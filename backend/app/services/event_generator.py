"""
EKAM Event Generator (Task 3, Stage 4).

Materializes a (possibly HAND-EDITED) Universal Blueprint into the SQL entities
the engine runs — Rounds, per-round Rubric criteria, Judges (with role labels) —
using EKAM's existing models. This is what makes a blueprint the organizer edited
on the review screen real, even when it has diverged from the original AI config.

Generalizes `routers/ai._materialize_rounds_judges_rubric`:
  - rounds + rubrics come from the BLUEPRINT (round-groups, so they pair 1:1 with
    `pipeline_service.build_steps`), preserving config round DATES when available;
  - judges come from the config (the actual people the organizer entered), stamped
    with the blueprint's evaluator `role_label`.

Idempotent: if rounds already exist for the event it no-ops (re-approval safe).
The AI never calls this directly — it runs only inside the approved `event_deploy`
executor, after a human approves the blueprint.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, Round, RoundStatus
from app.models.judge import Judge
from app.models.rubric import RubricCriterion


def _round_name(group: dict, index: int) -> str:
    """A clean round name from the group's submission/evaluation label."""
    for key, suffix in (("submission", " submission"), ("evaluation", " evaluation"), ("bracket", " bracket")):
        stage = group.get(key)
        if stage and stage.get("label"):
            label = str(stage["label"]).strip()
            low = label.lower()
            if low.endswith(suffix):
                label = label[: -len(suffix)].strip()
            if label:
                return label[:120]
    return f"Round {index + 1}"


def _single_role_label(blueprint: dict) -> str | None:
    judge_roles = [r for r in (blueprint.get("roles") or []) if r.get("kind") == "judge"]
    if len(judge_roles) == 1 and (judge_roles[0].get("label") or "").strip():
        return judge_roles[0]["label"].strip()
    return None


async def generate_from_blueprint(
    db: AsyncSession,
    event: Event,
    blueprint: dict,
    config: dict | None = None,
) -> dict:
    """Create rounds/rubrics/judges from the blueprint. Idempotent. Returns a small
    summary. Rounds are created in blueprint round-group order so the dynamic
    pipeline (`build_steps`) lines them up correctly."""
    from app.services.pipeline_service import _blueprint_round_groups
    from app.services.time_enforcement import parse_dt

    config = config or {}

    # Idempotency: never double-materialize.
    existing = (
        await db.execute(select(Round).where(Round.event_id == event.id).limit(1))
    ).scalars().first()
    if existing is not None:
        return {"created_rounds": 0, "skipped": True}

    # Keep the event's participant shape in step with the (edited) blueprint.
    participants = blueprint.get("participants") or {}
    model = (participants.get("model") or event.participants_model or "individual").lower()
    if model in ("individual", "team"):
        event.participants_model = model
    ts = participants.get("team_size") or {}
    if model == "team":
        try:
            if ts.get("min") is not None:
                event.min_team_size = int(ts["min"])
            if ts.get("max") is not None:
                event.max_team_size = int(ts["max"])
        except (TypeError, ValueError):
            pass

    # Themes/tracks (hackathon parity for a theme_selection stage) — from config.
    if any((s.get("type") == "theme_selection") for s in (blueprint.get("stages") or [])):
        from app.models.theme import Theme as ThemeModel

        seen_theme: set[str] = set()
        for t in (((config.get("core") or {}).get("tracks")) or []):
            if not isinstance(t, dict):
                continue
            tname = str(t.get("name") or "").strip()
            if not tname or tname.lower() in seen_theme:
                continue
            seen_theme.add(tname.lower())
            skills = t.get("required_skills") or []
            db.add(ThemeModel(
                event_id=event.id,
                name=tname[:200],
                description=(str(t.get("description") or "")[:1000]) or None,
                required_skills=[str(s)[:60] for s in (skills if isinstance(skills, list) else [])],
            ))
        if seen_theme:
            await db.commit()

    groups = _blueprint_round_groups(blueprint.get("stages") or [])
    config_rounds = config.get("rounds") or []

    # Postgres func.now() is the transaction time, so all rows in one commit share
    # created_at — stamp strictly increasing values so per-round ordering is stable.
    base_now = datetime.now(timezone.utc)
    created: list[tuple[Round, dict]] = []
    for i, g in enumerate(groups):
        # Round dates: reuse the config round at the same index when present
        # (config-derived blueprints), else leave open (organizer sets in Task-2 editors).
        start = end = None
        if i < len(config_rounds):
            d = (config_rounds[i].get("dates") or {})
            start = parse_dt(d.get("start") or d.get("starts_at") or d.get("opens_at") or d.get("start_date"))
            end = parse_dt(d.get("end") or d.get("ends_at") or d.get("deadline") or d.get("closes_at") or d.get("end_date"))
        evaluation = g.get("evaluation") or {}
        submission = g.get("submission") or {}
        scoring = evaluation.get("scoring") or {}
        mode = "auto" if (scoring.get("method") == "auto") else "human"
        anonymous = "anonymous_review" in (evaluation.get("behaviors") or [])
        # Quiz round (feature #8): the AI flags a set-paper / test / problem-set round
        # with a 'quiz' behavior on the submission or evaluation. The organizer then
        # uploads the question bank on the round's Question-Bank panel; the platform
        # generates a per-team paper and the judge grades per-question (or the AI
        # auto-checks). Carries the flag so the round is a quiz from deploy.
        behaviors = (evaluation.get("behaviors") or []) + (submission.get("behaviors") or [])
        is_quiz = "quiz" in behaviors
        # Live round: an EVALUATION with NO preceding submission stage → judging is
        # live; the pipeline materializes placeholder submissions so judges grade. A
        # bracket round (no evaluation) is NOT live-judged — it uses matches, not
        # submissions, so `bool(evaluation)` keeps it out.
        live_judging = bool(evaluation) and not bool(g.get("submission"))
        rnd = Round(
            event_id=event.id,
            name=_round_name(g, i),
            status=RoundStatus.upcoming,
            start_date=start,
            end_date=end,
            scoring_mode=mode,
            anonymous=anonymous,
            live_judging=live_judging,
            is_quiz=is_quiz,
            created_at=base_now + timedelta(seconds=i),
        )
        db.add(rnd)
        created.append((rnd, g))

    # If the blueprint had NO evaluation groups (e.g. a pure custom-stage format),
    # still create a single round so submission/leaderboard machinery has a home.
    if not created:
        rnd = Round(event_id=event.id, name="Round 1", status=RoundStatus.upcoming, created_at=base_now)
        db.add(rnd)
        created.append((rnd, {}))

    await db.commit()
    for rnd, _ in created:
        await db.refresh(rnd)

    # Rubric per round from the group's evaluation scoring criteria (the edited ones).
    for rnd, g in created:
        scoring = ((g.get("evaluation") or {}).get("scoring")) or {}
        criteria = scoring.get("criteria") or []
        rows = []
        for pos, c in enumerate(criteria):
            cname = str(c.get("name") or "").strip()
            if not cname:
                continue
            max_score = c.get("max_score") or 100
            rows.append(RubricCriterion(
                round_id=rnd.id,
                name=cname[:120],
                description=(str(c.get("description") or "")[:300]) or None,
                max_score=float(max_score),
                position=pos,
            ))
        if rows:
            db.add_all(rows)
    await db.commit()

    # Judges from config (the actual people), stamped with the blueprint role label.
    role_label = _single_role_label(blueprint) or "Judge"
    judges_cfg = ((config.get("judging_panel") or {}).get("judges")) or []
    seen: set[str] = set()
    created_judges = 0
    for j in judges_cfg:
        if not isinstance(j, dict):
            continue
        email = str(j.get("email") or "").strip()
        if "@" not in email or email.lower() in seen:
            continue
        seen.add(email.lower())
        expertise = j.get("expertise") or j.get("expertise_areas") or []
        if not isinstance(expertise, list):
            expertise = []
        db.add(Judge(
            event_id=event.id,
            name=str(j.get("name") or email.split("@")[0])[:120],
            email=email,
            institution=(str(j.get("company") or j.get("institution") or "")[:120]) or None,
            expertise=[str(e)[:60] for e in expertise],
            role_label=role_label,
        ))
        created_judges += 1
    if created_judges:
        await db.commit()

    return {"created_rounds": len(created), "created_judges": created_judges, "skipped": False}
