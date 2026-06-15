"""
EKAM automated scoring (Task 3, Stage 5).

Ingests externally-computed scores (an autograder, a CTF scoreboard export, an
AI-challenge metric) for an `auto`-scored round and writes them onto the
submissions — no human judges. The leaderboard + progression machinery is reused
unchanged: setting `submission.final_score` makes the round's `:evaluation` step
"ready" (see pipeline `_condition_met` for auto rounds), the live leaderboard
updates via the existing SSE signal, and the organizer still approves advancement.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, Round
from app.models.participant import Participant
from app.models.submission import Submission, SubmissionStatus


async def apply_auto_scores(db: AsyncSession, round_id: str, scores: dict) -> dict:
    """Set `final_score` on this round's submissions from `scores` (a map of
    submission_id OR team_id → number). Marks them reviewed, pushes the live
    leaderboard signal, and auto-proposes the round's next transition (the
    organizer still approves). Returns {updated, unmatched}."""
    rnd = (await db.execute(select(Round).where(Round.id == round_id))).scalars().first()
    if rnd is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Round not found")

    subs = (await db.execute(
        select(Submission).where(Submission.round_id == round_id)
    )).scalars().all()
    by_team = {str(s.team_id): s for s in subs}
    by_id = {str(s.id): s for s in subs}

    updated = 0
    unmatched: list[str] = []
    for key, val in (scores or {}).items():
        try:
            score = float(val)
        except (TypeError, ValueError):
            unmatched.append(str(key))
            continue
        sub = by_id.get(str(key)) or by_team.get(str(key))
        if sub is None:
            unmatched.append(str(key))
            continue
        sub.final_score = score
        sub.panel_average = score
        sub.status = SubmissionStatus.reviewed
        updated += 1

    if updated:
        await db.commit()

    # Live leaderboard signal (same shape evaluation_service uses).
    try:
        from app.services.event_bus import safe_publish

        event = (await db.execute(select(Event).where(Event.id == rnd.event_id))).scalars().first()
        participant_ids = (await db.execute(
            select(Participant.id).where(Participant.event_id == rnd.event_id)
        )).scalars().all()
        targets = [str(pid) for pid in participant_ids]
        if event and event.organizer_id:
            targets.append(str(event.organizer_id))
        if targets:
            await safe_publish(targets, {
                "type": "leaderboard",
                "event_id": str(rnd.event_id),
                "round_id": str(round_id),
            })
    except Exception as exc:
        print(f"[auto_score_service] leaderboard signal failed: {exc}")

    # Auto-propose the next transition (human still approves) now that the round
    # is fully scored.
    try:
        from app.services.pipeline_service import autopropose
        await autopropose(db, str(rnd.event_id))
    except Exception as exc:
        print(f"[auto_score_service] autopropose failed: {exc}")

    return {"updated": updated, "unmatched": unmatched}
