"""
EKAM Pipeline Service

Handles stage transitions and progression logic for teams.
Integrates with the Approval Workflow.
"""

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.approval import ApprovalRequest, ApprovalStatus, RequestType
from app.models.event import Event, EventStage, EventStatus, Round, RoundStatus
from app.models.participant import Participant, RegistrationStatus
from app.models.judge import Judge, JudgeAssignment
from app.models.pipeline import EventPipeline
from app.models.submission import Submission, Evaluation
from app.models.team import Team, TeamMember, TeamPreference
from app.models.notification import NotificationType
from app.services.approval_service import create_approval_request
from app.services.leaderboard_service import generate_leaderboard_service
from app.services.notification_service import create_notification


async def propose_stage_transition(
    db: AsyncSession,
    event_id: str,
    requested_by: str,
    target_stage: str,
    cutoff_score: float,
    round_id: str | None = None,
):
    """
    Queries the leaderboard for the current (or specified) round, applies the
    cutoff_score, and creates an ApprovalRequest listing which teams advance and
    which are eliminated.
    """
    current_round = None

    if round_id:
        res = await db.execute(
            select(Round).where(Round.id == round_id, Round.event_id == event_id)
        )
        current_round = res.scalars().first()
    else:
        # Most recent round for the event
        res = await db.execute(
            select(Round)
            .where(Round.event_id == event_id)
            .order_by(Round.start_date.desc())
        )
        current_round = res.scalars().first()

    advancing_teams = []
    eliminated_teams = []

    if current_round:
        leaderboard = await generate_leaderboard_service(db, current_round.id)

        for submission in leaderboard:
            score = submission.final_score or 0.0
            res_team = await db.execute(select(Team).where(Team.id == submission.team_id))
            team = res_team.scalars().first()
            team_name = team.name if team else str(submission.team_id)

            entry = {
                "team_id": str(submission.team_id),
                "team_name": team_name,
                "score": score,
            }
            if score >= cutoff_score:
                advancing_teams.append(entry)
            else:
                eliminated_teams.append(entry)
    else:
        # No rounds yet — propose advancing every team (event pre-round)
        res = await db.execute(select(Team))
        all_teams = res.scalars().all()
        advancing_teams = [
            {"team_id": str(t.id), "team_name": t.name, "score": 0.0}
            for t in all_teams
        ]

    payload = {
        "event_id": event_id,
        "target_stage": target_stage,
        "round_id": str(current_round.id) if current_round else None,
        "cutoff_score": cutoff_score,
        "advancing_teams": advancing_teams,
        "eliminated_teams": eliminated_teams,
        "requested_by": requested_by,  # preserved for email trigger after approval
    }

    approval = await create_approval_request(
        db=db,
        event_id=event_id,
        request_type=RequestType.stage_transition,
        payload=payload,
        requested_by=requested_by,
    )

    return approval


async def execute_stage_transition(
    db: AsyncSession,
    payload: dict,
):
    """
    Executed by the Approval Service once a stage transition is approved.
    1. Updates the event stage.
    2. Sends in-app notifications to all participants.
    3. Drafts AI-written bulk emails via email_triggers (→ approval → SMTP).
    """
    # New dynamic per-round pipeline payloads carry a next_step — delegate.
    if payload.get("pipeline") or payload.get("next_step"):
        return await execute_pipeline_transition(db, payload)

    event_id = payload.get("event_id")
    target_stage = payload.get("target_stage")
    requested_by = payload.get("requested_by", "system")

    if not event_id or not target_stage:
        return

    # 1. Update event stage
    new_stage_enum = None
    event = None
    try:
        res = await db.execute(select(Event).where(Event.id == event_id))
        event = res.scalars().first()

        if event:
            try:
                new_stage_enum = EventStage(target_stage)
                event.stage = new_stage_enum
            except ValueError:
                pass  # unknown stage string — skip enum update
            await db.commit()
    except Exception:
        await db.rollback()
        raise

    # 1b. Keep the dynamic pipeline cursor in step with this coarse transition.
    # The legacy path only touches event.stage; without this the DynamicPipeline
    # (which reads pipeline.current_step) would keep showing the previous step.
    if event and new_stage_enum:
        try:
            await _sync_pipeline_cursor_to_stage(db, event, target_stage)
        except Exception as exc:
            print(f"[pipeline_service] cursor sync failed: {exc}")

    # 2. In-app notifications to all participants
    res_p = await db.execute(
        select(Participant).where(Participant.event_id == event_id)
    )
    participants = res_p.scalars().all()
    stage_label = target_stage.replace("_", " ").title()
    for p in participants:
        await create_notification(
            db=db,
            event_id=event_id,
            user_id=str(p.id),
            title="Stage Update",
            message=f"The event has advanced to the {stage_label} stage.",
            notification_type=NotificationType.info,
        )

    # 3. AI-draft bulk emails via email_triggers (fire-and-forget errors)
    if event and new_stage_enum:
        try:
            from app.email_triggers import trigger_stage_emails
            extra_data = {
                "advancing_teams": payload.get("advancing_teams", []),
            }
            await trigger_stage_emails(
                event=event,
                new_stage=new_stage_enum,
                db=db,
                requested_by=requested_by,
                extra_data=extra_data,
            )
        except Exception as exc:
            # Email drafting must never block the pipeline
            print(f"[pipeline_service] email trigger failed: {exc}")


# =====================================================================
# DYNAMIC PER-ROUND PIPELINE
# =====================================================================
#
# The pipeline adapts to the event's rounds. Ordered steps:
#   registration → team_formation → theme_selection → judge_assignment
#   → for each round: round:<id>:submission → :evaluation → :advancement
#   → winner_announcement → completed
#
# Each step's transition is auto-proposed (an ApprovalRequest) when its
# condition is met; the organizer approves. `event.stage` is kept in sync with
# a coarse value for backward-compatible UI gating. Failed teams (below the
# advancement cutoff) are recorded in EventPipeline.data and blocked from later
# rounds.

_PRE_ROUND_STEPS = [
    ("registration", "Registration"),
    ("team_formation", "Team Formation"),
    ("theme_selection", "Theme & Team Name"),
    ("judge_assignment", "Judge Assignment"),
]


def build_steps(rounds: list, blueprint: dict | None = None) -> list[dict]:
    """Ordered pipeline steps.

    Task 3: when the event carries a `blueprint`, the steps are derived from
    `blueprint.stages` (any format, including custom/manual phases and individual
    `entry_formation`). When there's no blueprint (legacy/hackathon events), this
    falls back to the original hardcoded default — backward-compat, non-negotiable.
    """
    if blueprint:
        bp_steps = _build_steps_from_blueprint(blueprint, rounds)
        if bp_steps:
            return bp_steps

    steps: list[dict] = [{"id": sid, "label": label} for sid, label in _PRE_ROUND_STEPS]
    for index, rnd in enumerate(rounds, start=1):
        rid = str(rnd.id)
        steps.append({"id": f"round:{rid}:submission", "label": f"R{index} Submission", "round_id": rid})
        steps.append({"id": f"round:{rid}:evaluation", "label": f"R{index} Evaluation", "round_id": rid})
        steps.append({"id": f"round:{rid}:advancement", "label": f"R{index} Advancement", "round_id": rid})
    steps.append({"id": "winner_announcement", "label": "Winner Announcement"})
    steps.append({"id": "completed", "label": "Completed"})
    return steps


def _blueprint_round_groups(stages: list[dict]) -> list[dict]:
    """Group blueprint stages into EKAM 'rounds'. A round is anchored by an
    `evaluation` stage, plus the preceding `submission` (since the last round) and
    the following non-winners `progression`. The generator creates one Round per
    group, in this order, so build_steps can pair group[i] ↔ rounds[i]."""
    groups: list[dict] = []
    pending_sub: dict | None = None
    for s in stages:
        t = (s.get("type") or "").lower()
        if t == "submission":
            pending_sub = s
        elif t == "evaluation":
            groups.append({"submission": pending_sub, "evaluation": s, "bracket": None, "progression": None})
            pending_sub = None
        elif t == "bracket":
            # A bracket is its OWN round (a knockout phase, refereed live) — anchor a
            # group on it so it gets a real, well-named round and a first-class
            # pipeline step instead of a manual `custom:` step.
            groups.append({"submission": pending_sub, "evaluation": None, "bracket": s, "progression": None})
            pending_sub = None
        elif t == "progression":
            rule = s.get("rule") or {}
            if rule.get("kind") != "winners" and groups and groups[-1].get("progression") is None:
                groups[-1]["progression"] = s
    return groups


def _build_steps_from_blueprint(blueprint: dict, rounds: list) -> list[dict]:
    """Map an ordered blueprint into pipeline steps the existing executors run.
    Round-bearing stages (submission/evaluation/progression) reuse the round step
    ids; pre/terminal/custom stages map to their own ids. Unknown phases become
    `custom:<id>` manual steps so an unseen format still flows roster → results."""
    stages = blueprint.get("stages") or []
    if not stages:
        return []

    groups = _blueprint_round_groups(stages)
    stage_to_step: dict[str, tuple[str, str]] = {}  # stage_id -> (round_id, kind)
    for i, g in enumerate(groups):
        if i >= len(rounds):
            break
        rid = str(rounds[i].id)
        if g.get("submission"):
            stage_to_step[g["submission"].get("id", "")] = (rid, "submission")
        if g.get("evaluation"):
            stage_to_step[g["evaluation"].get("id", "")] = (rid, "evaluation")
        if g.get("bracket"):
            stage_to_step[g["bracket"].get("id", "")] = (rid, "bracket")
        if g.get("progression"):
            stage_to_step[g["progression"].get("id", "")] = (rid, "advancement")

    steps: list[dict] = []
    for s in stages:
        sid = s.get("id") or ""
        t = (s.get("type") or "").lower()
        label = s.get("label") or t.replace("_", " ").title()
        if sid in stage_to_step:
            rid, kind = stage_to_step[sid]
            steps.append({"id": f"round:{rid}:{kind}", "label": label, "round_id": rid})
        elif t == "registration":
            steps.append({"id": "registration", "label": label})
        elif t == "team_formation":
            steps.append({"id": "team_formation", "label": label})
        elif t == "entry_formation":
            steps.append({"id": "entry_formation", "label": label})
        elif t == "theme_selection":
            steps.append({"id": "theme_selection", "label": label})
        elif t == "judge_assignment":
            steps.append({"id": "judge_assignment", "label": label})
        elif t in ("progression", "bracket") and (s.get("rule") or {}).get("kind") == "winners":
            steps.append({"id": "winner_announcement", "label": label})
        elif t == "communication":
            continue  # a touchpoint (communications[]), not a standalone pipeline step
        else:
            # custom / manual / approval / anything the engine can't automate →
            # an informational step the organizer advances by hand.
            steps.append({"id": f"custom:{sid}", "label": label})

    if not any(st["id"] == "winner_announcement" for st in steps):
        steps.append({"id": "winner_announcement", "label": "Winner Announcement"})
    steps.append({"id": "completed", "label": "Completed"})
    return steps


def _coarse_stage(step_id: str) -> str:
    if step_id == "registration":
        return "registration"
    if step_id in ("team_formation", "entry_formation", "theme_selection", "judge_assignment"):
        return "team_formation"
    if step_id.endswith(":submission"):
        return "submission"
    if step_id.endswith(":evaluation") or step_id.endswith(":advancement") or step_id.endswith(":bracket"):
        return "evaluation"
    if step_id == "winner_announcement":
        return "results"
    if step_id == "completed":
        return "completed"
    # custom:* (and anything unmapped) → not a coarse EventStage; the caller's
    # EventStage(...) raises ValueError and leaves event.stage unchanged.
    return "custom"


def _round_id_of(step_id: str) -> str | None:
    if step_id.startswith("round:"):
        return step_id.split(":")[1]
    return None


def _next_step_id(steps: list[dict], current: str) -> str | None:
    ids = [s["id"] for s in steps]
    if current not in ids:
        return None
    i = ids.index(current)
    return ids[i + 1] if i + 1 < len(ids) else None


async def _ordered_rounds(db: AsyncSession, event_id) -> list:
    res = await db.execute(
        select(Round).where(Round.event_id == event_id).order_by(Round.created_at, Round.id)
    )
    return list(res.scalars().all())


async def get_or_create_pipeline(db: AsyncSession, event: Event, rounds: list) -> EventPipeline:
    res = await db.execute(
        select(EventPipeline).where(EventPipeline.event_id == event.id)
    )
    pipeline = res.scalars().first()
    if pipeline:
        return pipeline

    # Seed the cursor from the event's existing coarse stage.
    stage = getattr(event.stage, "value", str(event.stage))
    step_id = "registration"
    if stage == "team_formation":
        step_id = "team_formation"
    elif stage == "submission" and rounds:
        step_id = f"round:{rounds[0].id}:submission"
    elif stage == "evaluation" and rounds:
        step_id = f"round:{rounds[0].id}:evaluation"
    elif stage == "results":
        step_id = "winner_announcement"
    elif stage == "completed":
        step_id = "completed"

    pipeline = EventPipeline(
        event_id=event.id,
        current_step=step_id,
        data={"eliminated_team_ids": [], "done_steps": []},
    )
    db.add(pipeline)
    await db.commit()
    await db.refresh(pipeline)
    return pipeline


async def _sync_pipeline_cursor_to_stage(db: AsyncSession, event: Event, target_stage: str) -> None:
    """Advance the dynamic pipeline cursor to match a coarse stage transition.

    The manual ("legacy") stage-transition path only updates event.stage; this
    moves pipeline.current_step to the matching step so the DynamicPipeline
    display doesn't keep showing the previous step. Forward-only — it never
    regresses a pipeline that's already further along.
    """
    rounds = await _ordered_rounds(db, event.id)
    steps = build_steps(rounds, getattr(event, "blueprint", None))
    ids = [s["id"] for s in steps]
    pipeline = await get_or_create_pipeline(db, event, rounds)

    # Resolve the target step id: an exact step id wins; otherwise map the coarse
    # stage to the first matching step (mirrors get_or_create_pipeline seeding).
    target_id = None
    if target_stage in ids:
        target_id = target_stage
    elif target_stage == "registration":
        target_id = "registration"
    elif target_stage == "team_formation":
        target_id = "team_formation"
    elif target_stage == "submission" and rounds:
        target_id = f"round:{rounds[0].id}:submission"
    elif target_stage == "evaluation" and rounds:
        target_id = f"round:{rounds[0].id}:evaluation"
    elif target_stage == "results":
        target_id = "winner_announcement"
    elif target_stage == "completed":
        target_id = "completed"

    if target_id not in ids:
        return

    current = pipeline.current_step if pipeline.current_step in ids else ids[0]
    if ids.index(target_id) <= ids.index(current):
        return  # already at or past the target — don't regress

    done = list((pipeline.data or {}).get("done_steps", []))
    for sid in ids[: ids.index(target_id)]:
        if sid not in done:
            done.append(sid)

    pipeline.current_step = target_id
    pipeline.data = {**(pipeline.data or {}), "done_steps": done}
    await db.commit()


async def _round_fully_evaluated(db: AsyncSession, round_id) -> bool:
    assignments = (
        await db.execute(select(JudgeAssignment).where(JudgeAssignment.round_id == round_id))
    ).scalars().all()
    if not assignments:
        return False
    subs = (
        await db.execute(select(Submission).where(Submission.round_id == round_id))
    ).scalars().all()
    sub_by_team = {s.team_id: s.id for s in subs}
    if not sub_by_team:
        return False
    eval_rows = (
        await db.execute(
            select(Evaluation.judge_id, Evaluation.submission_id).where(
                Evaluation.submission_id.in_(list(sub_by_team.values()))
            )
        )
    ).all()
    done = {(jid, sid) for jid, sid in eval_rows}
    for a in assignments:
        sid = sub_by_team.get(a.team_id)
        if sid is None or (a.judge_id, sid) not in done:
            return False
    return True


async def _condition_met(
    db: AsyncSession,
    event: Event,
    step_id: str,
    eliminated: list[str],
) -> bool:
    if step_id == "registration":
        # Registration is "ready to advance" only when it is actually OVER:
        #   (a) confirmed-participant capacity is reached, OR
        #   (b) the registration window has closed (registration_closes_at passed).
        # Previously this was `n > 0`, which proposed a stage transition on the
        # first registration — and again on every subsequent one (#7).
        confirmed = (await db.execute(
            select(func.count(Participant.id)).where(
                Participant.event_id == event.id,
                Participant.status == RegistrationStatus.confirmed,
            )
        )).scalar() or 0
        if confirmed == 0:
            return False
        cap = event.max_participants or 0
        if cap and confirmed >= cap:
            return True
        closes_at = event.registration_closes_at
        if closes_at is not None:
            if closes_at.tzinfo is None:
                closes_at = closes_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) >= closes_at:
                return True
        return False

    if step_id == "team_formation":
        n = (await db.execute(
            select(func.count(Team.id)).where(Team.event_id == event.id)
        )).scalar() or 0
        return n > 0

    if step_id == "entry_formation":
        # Individual formats (§7b.3): ready as soon as there are confirmed
        # participants — the transition executor creates the singleton "team of
        # one" per participant, then the pipeline flows to the first submission.
        confirmed = (await db.execute(
            select(func.count(Participant.id)).where(
                Participant.event_id == event.id,
                Participant.status == RegistrationStatus.confirmed,
            )
        )).scalar() or 0
        return confirmed > 0

    if step_id.startswith("custom:"):
        # Known-unknown manual phase (topic allocation, mentorship, country
        # allocation…). There's no on-platform "done" signal, so it's organizer-
        # driven: proposable immediately (an approval card appears to advance past
        # it) AND directly advanceable by hand — both paths, the human is the gate.
        return True

    if step_id == "theme_selection":
        teams = (await db.execute(
            select(Team).where(Team.event_id == event.id)
        )).scalars().all()
        if not teams:
            return False
        for team in teams:
            members = (await db.execute(
                select(func.count(TeamMember.id)).where(TeamMember.team_id == team.id)
            )).scalar() or 0
            prefs = (await db.execute(
                select(func.count(TeamPreference.id)).where(TeamPreference.team_id == team.id)
            )).scalar() or 0
            # Every member must have voted, and the team must have resolved a theme.
            if members == 0 or prefs < members or team.theme_id is None:
                return False
        return True

    if step_id == "judge_assignment":
        round_ids = [r.id for r in await _ordered_rounds(db, event.id)]
        if not round_ids:
            return False
        n = (await db.execute(
            select(func.count(JudgeAssignment.id)).where(
                JudgeAssignment.round_id.in_(round_ids)
            )
        )).scalar() or 0
        return n > 0

    if step_id.endswith(":submission"):
        rid = _round_id_of(step_id)
        teams = (await db.execute(
            select(Team).where(Team.event_id == event.id)
        )).scalars().all()
        active = [t for t in teams if str(t.id) not in eliminated]
        if not active:
            return False
        subs = (await db.execute(
            select(Submission.team_id).where(Submission.round_id == rid)
        )).all()
        submitted = {row[0] for row in subs}
        return all(t.id in submitted for t in active)

    if step_id.endswith(":evaluation"):
        rid = _round_id_of(step_id)
        rnd = (await db.execute(select(Round).where(Round.id == rid))).scalars().first()
        if rnd is not None and getattr(rnd, "scoring_mode", "human") == "auto":
            # Auto-scored round (CTF/coding/AI): no judges — ready once every active
            # team's submission carries a score (ingested from the autograder).
            teams = (await db.execute(
                select(Team).where(Team.event_id == event.id)
            )).scalars().all()
            active = [t for t in teams if str(t.id) not in eliminated]
            if not active:
                return False
            scored = (await db.execute(
                select(Submission.team_id).where(
                    Submission.round_id == rid, Submission.final_score.isnot(None)
                )
            )).all()
            scored_teams = {row[0] for row in scored}
            return all(t.id in scored_teams for t in active)
        return await _round_fully_evaluated(db, rid)

    if step_id.endswith(":bracket"):
        # Knockout phase: the organizer generates the bracket and referees score the
        # matches on the Bracket tab. There's no single on-platform "all done" signal
        # (a bracket can be partially played), so it's organizer-driven — proposable
        # immediately and advanced by hand once the final is decided.
        return True

    if step_id.endswith(":advancement") or step_id == "winner_announcement":
        return True  # organizer-driven; proposable immediately

    return False


async def get_state(db: AsyncSession, event_id) -> dict:
    event = (await db.execute(select(Event).where(Event.id == event_id))).scalars().first()
    if not event:
        return {"steps": [], "current_step": None, "ready_to_advance": False,
                "next_step": None, "eliminated_team_ids": []}

    rounds = await _ordered_rounds(db, event_id)
    steps = build_steps(rounds, getattr(event, "blueprint", None))
    pipeline = await get_or_create_pipeline(db, event, rounds)
    eliminated = (pipeline.data or {}).get("eliminated_team_ids", [])

    ids = [s["id"] for s in steps]
    current = pipeline.current_step if pipeline.current_step in ids else (ids[0] if ids else None)
    current_index = ids.index(current) if current in ids else 0

    for i, s in enumerate(steps):
        s["status"] = "done" if i < current_index else ("active" if i == current_index else "upcoming")

    # A round's submission window is closed once the pipeline has advanced past
    # that round's submission step (it's "done", i.e. before the active cursor).
    closed_submission_round_ids = [
        s["round_id"]
        for s in steps
        if s["id"].endswith(":submission") and s.get("round_id") and s["status"] == "done"
    ]

    ready = await _condition_met(db, event, current, eliminated) if current else False
    return {
        "steps": steps,
        "current_step": current,
        "ready_to_advance": ready,
        "next_step": _next_step_id(steps, current) if current else None,
        "eliminated_team_ids": eliminated,
        "closed_submission_round_ids": closed_submission_round_ids,
    }


async def sync_round_statuses(db: AsyncSession, event_id) -> bool:
    """Derive each round's status (upcoming/active/completed) from the pipeline
    cursor and persist any changes.

    Rounds are created 'upcoming' and nothing else ever updates the column, so
    without this every round — done, current, and future — displays as
    'upcoming'. We map the pipeline's per-round steps
    (round:<id>:submission|evaluation|advancement) onto the round:
      - all three steps done           → completed
      - cursor is within the round     → active
      - cursor hasn't reached it yet   → upcoming
    Returns True if any row changed. Best-effort and idempotent.
    """
    state = await get_state(db, event_id)
    steps = state.get("steps", [])
    if not steps:
        return False

    statuses_by_round: dict[str, set] = {}
    for s in steps:
        rid = s.get("round_id")
        if rid:
            statuses_by_round.setdefault(rid, set()).add(s.get("status"))

    if not statuses_by_round:
        return False

    rounds = await _ordered_rounds(db, event_id)
    changed = False
    for rnd in rounds:
        statuses = statuses_by_round.get(str(rnd.id))
        if not statuses:
            continue
        if statuses == {"done"}:
            target = RoundStatus.completed
        elif "active" in statuses or "done" in statuses:
            target = RoundStatus.active
        else:
            target = RoundStatus.upcoming
        if rnd.status != target:
            rnd.status = target
            changed = True

    if changed:
        await db.commit()
    return changed


async def is_round_submission_closed(db: AsyncSession, event_id, round_id) -> bool:
    """True once the pipeline has advanced past this round's submission step."""
    try:
        state = await get_state(db, event_id)
    except Exception:
        return False
    return str(round_id) in (state.get("closed_submission_round_ids") or [])


async def autopropose(db: AsyncSession, event_id) -> None:
    """Auto-create a stage-transition approval when the current step's condition
    is met and there isn't already one pending. Best-effort."""
    event = (await db.execute(select(Event).where(Event.id == event_id))).scalars().first()
    if not event:
        return

    rounds = await _ordered_rounds(db, event_id)
    steps = build_steps(rounds, getattr(event, "blueprint", None))
    pipeline = await get_or_create_pipeline(db, event, rounds)
    ids = [s["id"] for s in steps]
    current = pipeline.current_step
    if current not in ids or current == "completed":
        return

    eliminated = (pipeline.data or {}).get("eliminated_team_ids", [])
    if not await _condition_met(db, event, current, eliminated):
        return

    next_step = _next_step_id(steps, current)
    if not next_step:
        return

    pending = (await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.event_id == event_id,
            ApprovalRequest.request_type == RequestType.stage_transition,
            ApprovalRequest.status == ApprovalStatus.pending,
        )
    )).scalars().first()
    if pending:
        return

    current_step_obj = next(s for s in steps if s["id"] == current)
    payload = {
        "event_id": str(event_id),
        "pipeline": True,
        "current_step": current,
        "next_step": next_step,
        "round_id": current_step_obj.get("round_id"),
        "cutoff_score": 0.0,
    }

    # Winner announcement is irreversible (it emails winners + distributes
    # certificates), so the approval carries the proposed winners for the
    # organizer to review/edit before approving. The executor announces exactly
    # this reviewed list.
    is_winner_step = current == "winner_announcement"
    if is_winner_step:
        try:
            from app.services.winner_service import propose_winners
            proposal = await propose_winners(db, event_id, top_n=3)
            payload["winners"] = [
                w for w in proposal.get("winners", [])
                if w.get("team_id") not in eliminated
            ]
        except Exception as exc:
            print(f"[pipeline_service] winner proposal for approval failed: {exc}")

    await create_approval_request(
        db=db,
        event_id=str(event_id),
        request_type=RequestType.stage_transition,
        payload=payload,
        requested_by=str(event.organizer_id),
    )
    await create_notification(
        db=db,
        event_id=str(event_id),
        user_id=str(event.organizer_id),
        title=("Approve winner announcement" if is_winner_step else "Pipeline: action ready"),
        message=(
            "Winners are proposed and ready. Review them in Approvals and approve "
            "to announce winners and send emails."
            if is_winner_step else
            f"'{current_step_obj['label']}' is complete. "
            f"Approve in Approvals to advance the event."
        ),
        notification_type=NotificationType.action_required,
    )


async def advance_pipeline(db: AsyncSession, event_id, cutoff_score: float = 0.0) -> dict:
    """Organizer-initiated direct advance of the dynamic pipeline by one real step.

    Unlike the legacy coarse `propose_stage_transition`, this follows the actual
    per-round steps (team_formation → theme_selection → judge_assignment → …) so
    the UI never skips intermediate stages. Executes the step's side effects via
    execute_pipeline_transition and returns the new cursor position.
    """
    state = await get_state(db, event_id)
    current = state.get("current_step")
    next_step = state.get("next_step")
    if not current or not next_step:
        return {
            "advanced": False,
            "current_step": current,
            "next_step": next_step,
            "message": "Pipeline is already at its final step.",
        }

    # Winner announcement emails winners and distributes certificates — an
    # irreversible action that must always be explicitly approved, never fired
    # by a direct advance. Route it to the approval queue instead of executing.
    if current == "winner_announcement":
        await autopropose(db, event_id)
        return {
            "advanced": False,
            "requires_approval": True,
            "current_step": current,
            "next_step": next_step,
            "message": (
                "Winner announcement requires approval. Review the proposed "
                "winners in Approvals and approve to announce them and send emails."
            ),
        }

    # Scoring advancement is cutoff-gated and eliminates teams — route it to the
    # approval queue too, so the qualifying cutoff is set/reviewed in exactly ONE
    # place (the advancement approval), never applied by an unreviewed direct
    # advance (#13). autopropose creates the approval; the cutoff is edited there.
    if current.endswith(":advancement"):
        await autopropose(db, event_id)
        return {
            "advanced": False,
            "requires_approval": True,
            "current_step": current,
            "next_step": next_step,
            "message": (
                "Advancement requires approval. Set the qualifying cutoff and "
                "approve it in the Approvals panel."
            ),
        }

    event = (await db.execute(select(Event).where(Event.id == event_id))).scalars().first()
    rounds = await _ordered_rounds(db, event_id)
    steps = build_steps(rounds, getattr(event, "blueprint", None))
    current_obj = next((s for s in steps if s["id"] == current), {})

    payload = {
        "event_id": str(event_id),
        "pipeline": True,
        "current_step": current,
        "next_step": next_step,
        "round_id": current_obj.get("round_id"),
        "cutoff_score": float(cutoff_score or 0.0),
    }
    await execute_pipeline_transition(db, payload)

    new_state = await get_state(db, event_id)
    new_current = new_state.get("current_step")
    label = next((s["label"] for s in steps if s["id"] == new_current), new_current)
    return {
        "advanced": True,
        "current_step": new_current,
        "next_step": new_state.get("next_step"),
        "message": f"Pipeline advanced to {label}.",
    }


async def _team_member_emails(db: AsyncSession, team_id) -> list[str]:
    rows = (await db.execute(
        select(Participant.email)
        .join(TeamMember, TeamMember.participant_id == Participant.id)
        .where(TeamMember.team_id == team_id)
    )).all()
    return [r[0] for r in rows if r[0]]


async def _email_round_results(db, event, round_id, advancing_ids, failing_ids) -> None:
    from app.services.email_service import send_direct_email

    for team_id in advancing_ids:
        for email in await _team_member_emails(db, team_id):
            await send_direct_email(
                to=email,
                subject=f"You're through to the next round — {event.name}",
                body_text=(
                    f"Congratulations! Your team has advanced to the next round of "
                    f"{event.name}. Log in to submit for the upcoming round.\n\nTeam EKAM"
                ),
            )
    for team_id in failing_ids:
        for email in await _team_member_emails(db, team_id):
            await send_direct_email(
                to=email,
                subject=f"Update on your {event.name} journey",
                body_text=(
                    f"Thank you for participating in {event.name}. Your team did not "
                    f"advance to the next round, so further submissions are closed. "
                    f"We hope to see you again!\n\nTeam EKAM"
                ),
            )


async def ensure_singleton_teams(db: AsyncSession, event_id) -> int:
    """Individual (team-less) formats (§7b.3): give every participant without a
    team a one-member 'team of one', so the team-keyed submission / evaluation /
    judge-assignment / leaderboard machinery works unchanged. Idempotent — skips
    participants who already belong to a team. Returns how many were created.
    Also used as a backfill from the registration path / generator."""
    participants = (await db.execute(
        select(Participant).where(Participant.event_id == event_id)
    )).scalars().all()
    if not participants:
        return 0
    membered = set((await db.execute(
        select(TeamMember.participant_id)
        .join(Team, Team.id == TeamMember.team_id)
        .where(Team.event_id == event_id)
    )).scalars().all())

    created = 0
    for p in participants:
        if p.id in membered:
            continue
        team = Team(event_id=event_id, name=(p.name or f"Entry {str(p.id)[:8]}"))
        db.add(team)
        await db.flush()
        db.add(TeamMember(team_id=team.id, participant_id=p.id, is_leader=True))
        created += 1
    if created:
        await db.commit()
    return created


async def ensure_live_submissions(db: AsyncSession, event_id, round_id, eliminated: list[str]) -> int:
    """Live-judged round (Round.live_judging=True, §submission_required): there is
    no participant submission step, so create a placeholder Submission per active
    team. This lets judges/referees score live through the SAME evaluation path
    (Evaluation.submission_id) and keeps the leaderboard/advancement machinery
    unchanged. Idempotent — skips teams that already have a submission. Returns how
    many were created."""
    teams = (await db.execute(
        select(Team).where(Team.event_id == event_id)
    )).scalars().all()
    active = [t for t in teams if str(t.id) not in (eliminated or [])]
    if not active:
        return 0
    existing = {row[0] for row in (await db.execute(
        select(Submission.team_id).where(Submission.round_id == round_id)
    )).all()}
    created = 0
    for t in active:
        if t.id in existing:
            continue
        db.add(Submission(team_id=t.id, round_id=round_id, attachments=[]))
        created += 1
    if created:
        await db.commit()
    return created


async def execute_pipeline_transition(db: AsyncSession, payload: dict) -> None:
    """Advance the dynamic pipeline cursor and perform the step's side effects."""
    event_id = payload.get("event_id")
    next_step = payload.get("next_step")
    current_step = payload.get("current_step")
    cutoff = float(payload.get("cutoff_score") or 0.0)
    if not event_id or not next_step:
        return

    event = (await db.execute(select(Event).where(Event.id == event_id))).scalars().first()
    if not event:
        return
    rounds = await _ordered_rounds(db, event_id)
    pipeline = await get_or_create_pipeline(db, event, rounds)
    eliminated = list((pipeline.data or {}).get("eliminated_team_ids", []))

    # Entry setup (individual formats, §7b.3): materialize one "team of one" per
    # participant so the team-keyed downstream machinery works unchanged.
    if current_step == "entry_formation":
        try:
            await ensure_singleton_teams(db, event_id)
        except Exception as exc:
            print(f"[pipeline_service] entry_formation singleton teams failed: {exc}")

    # Live-judged round: entering its evaluation step with no participant
    # submissions → seed a placeholder submission per active team so referees can
    # score live through the normal evaluation path. Only for rounds flagged
    # live_judging (the feature flag) — normal rounds are untouched.
    if next_step and next_step.endswith(":evaluation"):
        rid = _round_id_of(next_step)
        rnd = (await db.execute(select(Round).where(Round.id == rid))).scalars().first()
        if rnd is not None and getattr(rnd, "live_judging", False):
            try:
                await ensure_live_submissions(db, event_id, rid, eliminated)
            except Exception as exc:
                print(f"[pipeline_service] live-round placeholder submissions failed: {exc}")

    # Advancement: split this round's teams by the organizer's cutoff, eliminate
    # the failers, and email both groups.
    if current_step and current_step.endswith(":advancement"):
        rid = _round_id_of(current_step)
        leaderboard = await generate_leaderboard_service(db, rid)
        # An explicit override (set by the organizer editing the proposal) wins;
        # otherwise split by the cutoff score.
        override = payload.get("advancing_team_ids")
        advancing, failing = [], []
        if override is not None:
            override_set = {str(t) for t in override}
            for sub in leaderboard:
                (advancing if str(sub.team_id) in override_set else failing).append(sub.team_id)
        else:
            for sub in leaderboard:
                (advancing if (sub.final_score or 0.0) >= cutoff else failing).append(sub.team_id)
        for tid in failing:
            if str(tid) not in eliminated:
                eliminated.append(str(tid))
        # Persist the cutoff used as this round's single source of truth (#13), so
        # leaderboard/pipeline/approvals all display the same value read-only.
        rnd = next((r for r in rounds if str(r.id) == str(rid)), None)
        if rnd is not None:
            rnd.cutoff_score = cutoff
        # Suppress round-result emails for the FINAL round's advancement: there is
        # no "next round", and winners are announced (with their own email) via the
        # winner-announcement step. Sending "you're through to the next round" here
        # would be wrong and double up with the winner announcement.
        is_final_round = bool(rounds) and str(rounds[-1].id) == str(rid)
        if not is_final_round:
            try:
                await _email_round_results(db, event, rid, advancing, failing)
            except Exception as exc:
                print(f"[pipeline_service] round-result emails failed: {exc}")

    # Winner announcement: announce the winners the organizer reviewed when they
    # approved this transition. We only reach here via an approved approval (the
    # direct-advance path is blocked for this step), so reaching this code is the
    # verification gate. Fall back to a fresh proposal only if the payload didn't
    # carry one (e.g. legacy approvals created before this field existed).
    if current_step == "winner_announcement":
        try:
            from app.services.winner_service import propose_winners, finalize_winners
            winners = payload.get("winners")
            if not winners:
                proposal = await propose_winners(db, event_id, top_n=3)
                winners = proposal.get("winners", [])
            winners = [w for w in winners if w.get("team_id") not in eliminated]
            if winners:
                await finalize_winners(db, event_id, winners, requested_by=str(event.organizer_id))
        except Exception as exc:
            print(f"[pipeline_service] winner finalize failed: {exc}")

    done = list((pipeline.data or {}).get("done_steps", []))
    if current_step and current_step not in done:
        done.append(current_step)

    pipeline.current_step = next_step
    pipeline.data = {**(pipeline.data or {}), "eliminated_team_ids": eliminated, "done_steps": done}

    try:
        event.stage = EventStage(_coarse_stage(next_step))
    except ValueError:
        pass

    # Mark the event completed once the pipeline reaches its final step.
    if next_step == "completed":
        event.status = EventStatus.completed

    await db.commit()

    # Push a live "pipeline" signal to the organizer and all participants so
    # their pipeline views advance instantly (SSE). Best-effort.
    try:
        from app.services.event_bus import safe_publish

        participant_ids = (
            await db.execute(
                select(Participant.id).where(Participant.event_id == event_id)
            )
        ).scalars().all()
        targets = [str(event.organizer_id)] + [str(pid) for pid in participant_ids]
        await safe_publish(
            targets,
            {"type": "pipeline", "event_id": str(event_id), "current_step": next_step},
        )
    except Exception as exc:
        print(f"[pipeline_service] pipeline signal failed: {exc}")

    # Task 3: draft any blueprint communications for the stage just ENTERED, via
    # the existing approval-gated email_batch flow (organizer reviews/sends). No-op
    # for legacy events (no blueprint). Best-effort — never blocks the pipeline.
    try:
        from app.services.communication_service import fire_stage_communications

        await fire_stage_communications(db, event, next_step)
    except Exception as exc:
        print(f"[pipeline_service] stage communications failed: {exc}")

    # Leaving registration: propose the participant welcome/confirmation batch (with
    # magic links) so registrants can reach their dashboard. Critical for preformed-
    # team and individual events, which have no team_formation step to email people.
    # Approval-gated; blueprint events only; best-effort.
    if current_step == "registration":
        try:
            from app.services.communication_service import fire_post_registration

            await fire_post_registration(db, event)
        except Exception as exc:
            print(f"[pipeline_service] post-registration emails failed: {exc}")

    # Keep each round's status column in step with the new cursor position so
    # the judge/organizer UIs show done/active/upcoming correctly.
    try:
        await sync_round_statuses(db, event_id)
    except Exception as exc:
        print(f"[pipeline_service] round status sync failed: {exc}")

    # Chain: immediately propose the next transition if its condition is already met.
    try:
        await autopropose(db, event_id)
    except Exception as exc:
        print(f"[pipeline_service] chained autopropose failed: {exc}")
