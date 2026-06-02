"""
EKAM Winner Service

Proposes winners (top-N by score from the latest round's leaderboard) and,
once the organizer confirms, announces them: sends each winning team a
congratulations + prize/next-steps email with a winner certificate attached,
distributes participation certificates to everyone, and records the result.
"""

import asyncio

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.certificate import generate_certificate_html
from app.models.event import Event, Round
from app.models.participant import Participant
from app.models.report import Report as ReportModel
from app.models.team import Team, TeamMember
from app.services.email_service import send_direct_email
from app.services.leaderboard_service import generate_leaderboard_service


def _ordinal(n: int) -> str:
    if 10 <= (n % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


async def _latest_round(db: AsyncSession, event_id) -> Round | None:
    return (
        await db.execute(
            select(Round)
            .where(Round.event_id == event_id)
            .order_by(Round.created_at.desc())
        )
    ).scalars().first()


async def _team_member_emails(db: AsyncSession, team_id) -> list[str]:
    rows = (
        await db.execute(
            select(Participant.email)
            .join(TeamMember, TeamMember.participant_id == Participant.id)
            .where(TeamMember.team_id == team_id)
        )
    ).all()
    return [r[0] for r in rows if r[0]]


async def propose_winners(
    db: AsyncSession,
    event_id,
    top_n: int = 3,
    round_id=None,
) -> dict:
    """Return the top-N teams (by final score) from a round's leaderboard."""
    rnd = None
    if round_id:
        rnd = (
            await db.execute(
                select(Round).where(Round.id == round_id, Round.event_id == event_id)
            )
        ).scalars().first()
    if rnd is None:
        rnd = await _latest_round(db, event_id)

    if rnd is None:
        return {"round_id": None, "winners": []}

    leaderboard = await generate_leaderboard_service(db, rnd.id)

    winners = []
    for rank, submission in enumerate(leaderboard[: max(0, top_n)], start=1):
        team = (
            await db.execute(select(Team).where(Team.id == submission.team_id))
        ).scalars().first()
        winners.append(
            {
                "rank": rank,
                "team_id": str(submission.team_id),
                "team_name": team.name if team else str(submission.team_id)[:8],
                "score": float(submission.final_score or 0.0),
            }
        )

    return {"round_id": str(rnd.id), "winners": winners}


async def finalize_winners(
    db: AsyncSession,
    event_id,
    winners: list[dict],
    requested_by: str,
) -> dict:
    """Persist the confirmed winners and send announcement + certificate emails."""
    event = (
        await db.execute(select(Event).where(Event.id == event_id))
    ).scalars().first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if not winners:
        raise HTTPException(status_code=400, detail="No winners provided")

    # Persist as a report so it shows on the Reports page and survives.
    report = ReportModel(
        event_id=event_id,
        title=f"Winners — {event.name}",
        type="winners",
        data={"winners": winners},
    )
    db.add(report)
    await db.commit()

    sent = 0
    for w in winners:
        rank = int(w.get("rank") or 0)
        team_id = w.get("team_id")
        prize = w.get("prize") or ""
        if not team_id:
            continue

        emails = await _team_member_emails(db, team_id)
        if not emails:
            continue

        place = _ordinal(rank) if rank else "a winning"
        team_name = w.get("team_name") or "your team"

        certificate_html = generate_certificate_html(
            participant_name=team_name,
            competition_name=event.name,
            achievement=f"{place} Place Winner",
        )

        prize_line = f"\n\nPrize: {prize}" if prize else ""
        subject = f"🏆 Congratulations! {team_name} won {place} place in {event.name}"
        body_text = (
            f"Congratulations {team_name}!\n\n"
            f"Your team secured {place} place in {event.name}.{prize_line}\n\n"
            f"Our team will contact you shortly regarding prize distribution and "
            f"next steps. Your winner certificate is attached.\n\n"
            f"Team EKAM"
        )
        body_html = (
            f"<p>Congratulations <strong>{team_name}</strong>!</p>"
            f"<p>Your team secured <strong>{place} place</strong> in "
            f"<strong>{event.name}</strong>."
            + (f" Prize: <strong>{prize}</strong>." if prize else "")
            + "</p>"
            f"<p>Our team will contact you shortly regarding <strong>prize "
            f"distribution and next steps</strong>. Your winner certificate is "
            f"attached.</p><p>Team EKAM</p>"
        )

        for email in emails:
            ok = await send_direct_email(
                to=email,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                attachments={
                    f"winner_certificate_{team_name}.html".replace(" ", "_"):
                    certificate_html.encode("utf-8"),
                },
            )
            if ok:
                sent += 1

    # Participation certificates to everyone (best-effort).
    try:
        from app.email_triggers import on_certificate_distribution

        await on_certificate_distribution(
            event=event,
            db=db,
            requested_by=requested_by,
            achievement="Participation",
        )
    except Exception as exc:
        print(f"[winner_service] participation certificate distribution failed: {exc}")

    return {
        "message": f"Winners announced. {sent} winner email(s) sent.",
        "report_id": str(report.id),
        "winners": winners,
    }
