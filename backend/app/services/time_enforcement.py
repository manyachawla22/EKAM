"""
EKAM time enforcement.

Time is treated as a *gate*, not an auto-advancer: deadlines block new writes
(registration / submission) and disqualify non-submitters, but they never flip
the pipeline stage on their own — the organizer still approves progression. An
early finish is fine; the pipeline can advance before a deadline.

All comparisons use server UTC. Config times arrive as IST (`+05:30`) strings and
are normalized to UTC on the way in.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, EventStatus, Round
from app.models.submission import Submission
from app.models.team import Team, TeamMember
from app.models.participant import Participant
from app.models.pipeline import EventPipeline
from app.models.notification import NotificationType

IST = timezone(timedelta(hours=5, minutes=30))


def parse_dt(value) -> Optional[datetime]:
    """Parse an ISO datetime (or date) into an aware UTC datetime, tolerantly.

    Handles `+05:30` offsets, trailing `Z`, date-only strings, and existing
    datetimes. Naive values are assumed to be IST (the config's timezone).
    Returns None when unparseable/empty.
    """
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        s = str(value).strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            try:
                dt = datetime.fromisoformat(s + "T00:00:00")
            except ValueError:
                return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.astimezone(timezone.utc)


def _aware_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Treat a DB datetime as UTC if it came back naive."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def registration_window_state(event: Event) -> Tuple[bool, Optional[str]]:
    """(is_open, reason_if_closed) for an event's registration window.

    No window configured → always open.
    """
    now = datetime.now(timezone.utc)
    opens = _aware_utc(event.registration_opens_at)
    closes = _aware_utc(event.registration_closes_at)
    if opens and now < opens:
        return False, "Registration has not opened yet."
    if closes and now > closes:
        return False, "Registration has closed."
    return True, None


def submission_window_state(round_obj: Round) -> Tuple[bool, Optional[str]]:
    """(is_open, reason_if_closed) for a round's submission window by time only.

    No dates configured → not time-gated (pipeline gating still applies elsewhere).
    """
    now = datetime.now(timezone.utc)
    start = _aware_utc(round_obj.start_date)
    end = _aware_utc(round_obj.end_date)
    if start and now < start:
        return False, "This round has not opened yet."
    if end and now > end:
        return False, "The submission deadline for this round has passed."
    return True, None


async def disqualify_non_submitters(db: AsyncSession, round_id) -> int:
    """Disqualify every still-active team that has no submission for `round_id`,
    once that round's deadline has passed. Idempotent.

    Reuses EventPipeline.eliminated_team_ids so the existing exclusion machinery
    keeps disqualified teams out of later rounds and leaderboards. Returns the
    number of teams newly disqualified.
    """
    round_obj = (
        await db.execute(select(Round).where(Round.id == round_id))
    ).scalars().first()
    if not round_obj or not round_obj.end_date:
        return 0

    end = _aware_utc(round_obj.end_date)
    if datetime.now(timezone.utc) <= end:
        return 0  # deadline not yet passed

    event_id = round_obj.event_id

    teams = (
        await db.execute(select(Team).where(Team.event_id == event_id))
    ).scalars().all()
    if not teams:
        return 0

    submitted_team_ids = set(
        (
            await db.execute(
                select(Submission.team_id).where(Submission.round_id == round_id)
            )
        ).scalars().all()
    )

    pipeline = (
        await db.execute(
            select(EventPipeline).where(EventPipeline.event_id == event_id)
        )
    ).scalars().first()
    eliminated = list((pipeline.data or {}).get("eliminated_team_ids", [])) if pipeline else []

    newly: list[Team] = []
    for team in teams:
        if team.disqualified or str(team.id) in eliminated or team.id in submitted_team_ids:
            continue
        team.disqualified = True
        team.disqualified_reason = f"Missed submission deadline for {round_obj.name}"
        eliminated.append(str(team.id))
        newly.append(team)

    if not newly:
        return 0

    if pipeline:
        pipeline.data = {**(pipeline.data or {}), "eliminated_team_ids": eliminated}
    await db.commit()

    # Notify each disqualified team's members (in-app + SSE via create_notification).
    from app.services.notification_service import create_notification

    for team in newly:
        member_ids = (
            await db.execute(
                select(TeamMember.participant_id).where(TeamMember.team_id == team.id)
            )
        ).scalars().all()
        for pid in member_ids:
            try:
                await create_notification(
                    db=db,
                    event_id=str(event_id),
                    user_id=str(pid),
                    title="Submission deadline missed",
                    message=(
                        f"Your team did not submit before the deadline for "
                        f"{round_obj.name} and has been disqualified from further rounds."
                    ),
                    notification_type=NotificationType.alert,
                )
            except Exception as exc:
                print(f"[time_enforcement] disqualify notify failed: {exc}")

    # Live signal so leaderboard/pipeline views update.
    try:
        from app.services.event_bus import safe_publish

        ev = (await db.execute(select(Event).where(Event.id == event_id))).scalars().first()
        targets = [str(ev.organizer_id)] if ev and ev.organizer_id else []
        await safe_publish(
            targets,
            {"type": "leaderboard", "event_id": str(event_id), "round_id": str(round_id)},
        )
    except Exception as exc:
        print(f"[time_enforcement] disqualify signal failed: {exc}")

    print(f"[time_enforcement] disqualified {len(newly)} team(s) for round {round_id}")
    return len(newly)


async def run_deadline_sweep_once(db: AsyncSession) -> None:
    """Scan active events and disqualify non-submitters for any round whose
    submission window is the current pipeline step and whose deadline has passed.

    Scoping to the *current* submission round avoids wrongly disqualifying teams
    for future rounds they legitimately haven't reached yet.
    """
    from app.services.pipeline_service import get_state, _round_id_of

    events = (
        await db.execute(select(Event).where(Event.status == EventStatus.active))
    ).scalars().all()

    for event in events:
        try:
            state = await get_state(db, event.id)
            current = state.get("current_step")
            if current and current.endswith(":submission"):
                rid = _round_id_of(current)
                if rid:
                    await disqualify_non_submitters(db, rid)
        except Exception as exc:
            print(f"[time_enforcement] sweep failed for event {event.id}: {exc}")
            continue
