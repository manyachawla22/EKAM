"""
EKAM Pipeline Service

Handles stage transitions and progression logic for teams.
Integrates with the Approval Workflow.
"""

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.approval import ApprovalRequest, ApprovalStatus, RequestType
from app.models.event import Event, EventStage, EventStatus, Round, RoundStatus
from app.models.participant import Participant
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


def build_steps(rounds: list) -> list[dict]:
    steps: list[dict] = [{"id": sid, "label": label} for sid, label in _PRE_ROUND_STEPS]
    for index, rnd in enumerate(rounds, start=1):
        rid = str(rnd.id)
        steps.append({"id": f"round:{rid}:submission", "label": f"R{index} Submission", "round_id": rid})
        steps.append({"id": f"round:{rid}:evaluation", "label": f"R{index} Evaluation", "round_id": rid})
        steps.append({"id": f"round:{rid}:advancement", "label": f"R{index} Advancement", "round_id": rid})
    steps.append({"id": "winner_announcement", "label": "Winner Announcement"})
    steps.append({"id": "completed", "label": "Completed"})
    return steps


def _coarse_stage(step_id: str) -> str:
    if step_id == "registration":
        return "registration"
    if step_id in ("team_formation", "theme_selection", "judge_assignment"):
        return "team_formation"
    if step_id.endswith(":submission"):
        return "submission"
    if step_id.endswith(":evaluation") or step_id.endswith(":advancement"):
        return "evaluation"
    if step_id == "winner_announcement":
        return "results"
    if step_id == "completed":
        return "completed"
    return "registration"


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
    steps = build_steps(rounds)
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
        n = (await db.execute(
            select(func.count(Participant.id)).where(Participant.event_id == event.id)
        )).scalar() or 0
        return n > 0

    if step_id == "team_formation":
        n = (await db.execute(
            select(func.count(Team.id)).where(Team.event_id == event.id)
        )).scalar() or 0
        return n > 0

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
        return await _round_fully_evaluated(db, _round_id_of(step_id))

    if step_id.endswith(":advancement") or step_id == "winner_announcement":
        return True  # organizer-driven; proposable immediately

    return False


async def get_state(db: AsyncSession, event_id) -> dict:
    event = (await db.execute(select(Event).where(Event.id == event_id))).scalars().first()
    if not event:
        return {"steps": [], "current_step": None, "ready_to_advance": False,
                "next_step": None, "eliminated_team_ids": []}

    rounds = await _ordered_rounds(db, event_id)
    steps = build_steps(rounds)
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
    steps = build_steps(rounds)
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

    rounds = await _ordered_rounds(db, event_id)
    steps = build_steps(rounds)
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
