"""
EKAM Matches / Bracket Router (Task 3, Stage 5c).
"""
import csv
import io
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.auth_context import AuthContext
from app.middleware.auth import require_actor_type, require_event_access, get_current_actor
from app.models.event import Event
from app.models.match import Match
from app.models.team import Team, TeamMember
from app.services import bracket_service

router = APIRouter(prefix="/matches", tags=["Matches"])


class GenerateBracketBody(BaseModel):
    round_id: str
    team_ids: Optional[List[str]] = None        # default: all of the event's teams
    seed_by_score: bool = False                 # seed by each team's latest final_score


class PatchMatchBody(BaseModel):
    match_link: Optional[str] = None
    scheduled_at: Optional[str] = None          # ISO; sets status → scheduled
    winner_team_id: Optional[str] = None        # set → record result + advance
    score_a: Optional[float] = None
    score_b: Optional[float] = None


@router.get(
    "/events/{event_id}/bracket",
    dependencies=[
        Depends(require_actor_type(["organizer", "judge", "participant"])),
        Depends(require_event_access("event_id")),
    ],
)
async def get_event_bracket(event_id: str, db: AsyncSession = Depends(get_db)):
    """The full bracket tree (rounds → matches), for the bracket view."""
    return await bracket_service.get_bracket(db, event_id)


@router.post(
    "/events/{event_id}/generate",
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id")),
    ],
)
async def generate_event_bracket(
    event_id: str, body: GenerateBracketBody, db: AsyncSession = Depends(get_db)
):
    """Seed + build a single-elimination bracket for a round. Defaults to all of
    the event's teams; optionally seeds by each team's latest score."""
    team_ids = body.team_ids
    if not team_ids:
        rows = (await db.execute(select(Team.id).where(Team.event_id == event_id))).scalars().all()
        team_ids = [str(t) for t in rows]
        # Individual (team-less) tournament: each participant is their own entry
        # (a one-person "team", §7b.3). With no teams yet there are no contestants
        # to seed, so form singleton teams first, then re-read. Idempotent; a real
        # team event already has its teams and this no-ops.
        if not team_ids:
            from app.services.pipeline_service import ensure_singleton_teams

            await ensure_singleton_teams(db, event_id)
            rows = (await db.execute(select(Team.id).where(Team.event_id == event_id))).scalars().all()
            team_ids = [str(t) for t in rows]
        # Exclude teams already eliminated (e.g. losers of a qualifier round) so the
        # knockout only contains the squads that actually advanced. A pure-tournament
        # event has no eliminations yet, so this leaves all teams in. (Explicit
        # team_ids from the caller are trusted as-is.)
        try:
            from app.services.pipeline_service import get_or_create_pipeline, _ordered_rounds

            event = (await db.execute(select(Event).where(Event.id == event_id))).scalars().first()
            if event:
                rounds = await _ordered_rounds(db, event_id)
                pipeline = await get_or_create_pipeline(db, event, rounds)
                eliminated = {str(t) for t in (pipeline.data or {}).get("eliminated_team_ids", [])}
                if eliminated:
                    team_ids = [t for t in team_ids if t not in eliminated]
        except Exception as exc:
            print(f"[matches] eliminated-team filter failed (using all teams): {exc}")

    seed_scores = None
    if body.seed_by_score:
        from app.models.submission import Submission

        subs = (await db.execute(
            select(Submission.team_id, Submission.final_score).where(Submission.round_id == body.round_id)
        )).all()
        seed_scores = {str(tid): (sc or 0.0) for tid, sc in subs}

    return await bracket_service.generate_bracket(db, event_id, body.round_id, team_ids, seed_scores)


@router.patch(
    "/{match_id}",
    dependencies=[Depends(require_actor_type(["organizer", "judge"]))],
)
async def patch_match(
    match_id: str,
    body: PatchMatchBody,
    auth: AuthContext = Depends(require_actor_type(["organizer", "judge"])),
    db: AsyncSession = Depends(get_db),
):
    """Set match logistics (link/time) and/or record the result (winner+scores),
    which advances the bracket. Open to the organizer AND the event's evaluators
    (the referee scores each live match); access is gated to the match's event."""
    match = (await db.execute(select(Match).where(Match.id == match_id))).scalars().first()
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    if not auth.can_access_event(str(match.event_id)):
        raise HTTPException(status_code=403, detail="No access to this event")

    # Logistics first (so a single call can schedule + record).
    changed = False
    if body.match_link is not None:
        match.match_link = body.match_link
        changed = True
    if body.scheduled_at is not None:
        try:
            match.scheduled_at = datetime.fromisoformat(body.scheduled_at.replace("Z", "+00:00"))
            if match.status == "pending":
                match.status = "scheduled"
            changed = True
        except ValueError:
            raise HTTPException(status_code=400, detail="scheduled_at must be ISO-8601")
    if changed:
        await db.commit()

    if body.winner_team_id:
        await bracket_service.record_result(db, match_id, body.winner_team_id, body.score_a, body.score_b)

    return await bracket_service.get_bracket(db, str(match.event_id))


@router.post(
    "/events/{event_id}/upload-csv",
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id")),
    ],
)
async def upload_match_links_csv(
    event_id: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)
):
    """Bulk-set match links + times from a CSV (reuses the participant-CSV pattern).
    Columns (case-insensitive): round_number, match_index, match_link, scheduled_at.
    Matches the event's bracket by (round_number, match_index)."""
    if not (file.filename or "").endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    content = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))

    existing = (await db.execute(select(Match).where(Match.event_id == event_id))).scalars().all()
    by_pos = {(m.round_number, m.match_index): m for m in existing}

    updated = 0
    for row in reader:
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items() if k}
        try:
            pos = (int(row.get("round_number")), int(row.get("match_index")))
        except (TypeError, ValueError):
            continue
        m = by_pos.get(pos)
        if not m:
            continue
        if row.get("match_link"):
            m.match_link = row["match_link"]
        if row.get("scheduled_at"):
            try:
                m.scheduled_at = datetime.fromisoformat(row["scheduled_at"].replace("Z", "+00:00"))
                if m.status == "pending":
                    m.status = "scheduled"
            except ValueError:
                pass
        updated += 1
    if updated:
        await db.commit()
    return {"updated": updated}


@router.get(
    "/events/{event_id}/my-matches",
    dependencies=[Depends(require_actor_type(["participant"]))],
)
async def my_matches(
    event_id: str,
    auth: AuthContext = Depends(require_actor_type(["participant"])),
    db: AsyncSession = Depends(get_db),
):
    """The calling participant's matches (their team's), with opponent + link +
    time — feeds the participant 'my match' card."""
    email = getattr(auth.entity, "email", None)
    if not email:
        return []
    # Resolve the participant's team(s) in this event.
    from app.models.participant import Participant

    team_ids = (await db.execute(
        select(TeamMember.team_id)
        .join(Team, Team.id == TeamMember.team_id)
        .join(Participant, Participant.id == TeamMember.participant_id)
        .where(Team.event_id == event_id, Participant.email == email)
    )).scalars().all()
    if not team_ids:
        return []
    team_id_set = {str(t) for t in team_ids}

    bracket = await bracket_service.get_bracket(db, event_id)
    mine = []
    for rnd in bracket["rounds"]:
        for m in rnd["matches"]:
            a, b = m["side_a"]["team_id"], m["side_b"]["team_id"]
            if (a in team_id_set) or (b in team_id_set):
                you_are_a = a in team_id_set
                mine.append({
                    "match_id": m["id"],
                    "round_number": rnd["round_number"],
                    "opponent": m["side_b"]["name"] if you_are_a else m["side_a"]["name"],
                    "scheduled_at": m["scheduled_at"],
                    "match_link": m["match_link"],
                    "status": m["status"],
                    "winner_team_id": m["winner_team_id"],
                })
    return mine
