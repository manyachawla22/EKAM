"""
EKAM Tournament Bracket service (Task 3, Stage 5c).

Single-elimination knockout over the generic "team/entry" unit. Builds the whole
tree up front (round 1 paired, later rounds empty "TBD"), seeds by prior score or
input order, handles byes when the count isn't a power of two, and advances the
tree as results are recorded (winner promoted into its `next_match` slot). Reuses
the pipeline's `eliminated_team_ids` for losers. Pure-ish: only touches the
`matches` table + the pipeline data blob.
"""

from __future__ import annotations

import math
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Match
from app.models.team import Team


def _next_pow2(n: int) -> int:
    p = 1
    while p < n:
        p *= 2
    return p


def _seed_order(size: int) -> list[int]:
    """Standard single-elimination seed slot order for a power-of-two bracket.
    Returns seeds (1-based) so #1 and #2 can only meet in the final and byes are
    spread out. e.g. size 4 → [1, 4, 2, 3]."""
    seeds = [1, 2]
    rounds = int(math.log2(size))
    for r in range(1, rounds):
        target = 2 ** (r + 1) + 1
        nxt: list[int] = []
        for s in seeds:
            nxt.append(s)
            nxt.append(target - s)
        seeds = nxt
    return seeds


async def _promote(db: AsyncSession, match: Match, winner_team_id) -> None:
    """Record a winner and push it into its next-match slot."""
    match.winner_team_id = winner_team_id
    match.status = "completed"
    if match.next_match_id and winner_team_id:
        nxt = (await db.execute(select(Match).where(Match.id == match.next_match_id))).scalars().first()
        if nxt is not None:
            if match.next_slot == "b":
                nxt.side_b_team_id = winner_team_id
            else:
                nxt.side_a_team_id = winner_team_id


async def generate_bracket(
    db: AsyncSession,
    event_id,
    round_id,
    team_ids: list,
    seed_scores: Optional[dict] = None,
) -> dict:
    """Create the single-elim bracket for `team_ids`. Idempotent per round:
    no-ops if matches already exist for this round. Returns {created, rounds}."""
    existing = (await db.execute(
        select(Match).where(Match.round_id == round_id).limit(1)
    )).scalars().first()
    if existing is not None:
        return {"created": 0, "skipped": True}

    teams = [str(t) for t in team_ids if t]
    if len(teams) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="A bracket needs at least 2 contestants.")

    # Seed: highest score = #1 when scores given, else input order.
    if seed_scores:
        teams.sort(key=lambda t: seed_scores.get(t, 0.0), reverse=True)

    size = _next_pow2(len(teams))
    num_rounds = int(math.log2(size))
    order = _seed_order(size)
    # slot -> team (None = bye); seed s (1-based) maps to teams[s-1] or bye.
    slots = [teams[s - 1] if (s - 1) < len(teams) else None for s in order]

    by_round: dict[int, list[Match]] = {}
    # Round 1: pair adjacent slots.
    r1: list[Match] = []
    for i in range(size // 2):
        m = Match(
            event_id=event_id, round_id=round_id, round_number=1, match_index=i,
            side_a_team_id=slots[2 * i], side_b_team_id=slots[2 * i + 1], status="pending",
        )
        db.add(m)
        r1.append(m)
    by_round[1] = r1
    # Later rounds: empty matches.
    for r in range(2, num_rounds + 1):
        rmatches: list[Match] = []
        for i in range(size // (2 ** r)):
            m = Match(event_id=event_id, round_id=round_id, round_number=r, match_index=i, status="pending")
            db.add(m)
            rmatches.append(m)
        by_round[r] = rmatches
    await db.flush()  # assign ids

    # Link winner destinations.
    for r in range(1, num_rounds):
        for i, m in enumerate(by_round[r]):
            nxt = by_round[r + 1][i // 2]
            m.next_match_id = nxt.id
            m.next_slot = "a" if i % 2 == 0 else "b"
    await db.commit()

    # Resolve round-1 byes (exactly one side present) → auto-advance.
    for m in by_round[1]:
        a_none = m.side_a_team_id is None
        b_none = m.side_b_team_id is None
        if a_none ^ b_none:
            await _promote(db, m, m.side_a_team_id or m.side_b_team_id)
    await db.commit()

    total = sum(len(v) for v in by_round.values())
    return {"created": total, "rounds": num_rounds, "skipped": False}


async def record_result(
    db: AsyncSession,
    match_id,
    winner_team_id,
    score_a: Optional[float] = None,
    score_b: Optional[float] = None,
) -> Match:
    """Set a match's winner/scores and advance the winner into the next round.
    Records the loser into the event pipeline's eliminated set (best-effort)."""
    match = (await db.execute(select(Match).where(Match.id == match_id))).scalars().first()
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    sides = {str(match.side_a_team_id), str(match.side_b_team_id)}
    if str(winner_team_id) not in sides:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Winner must be one of the two contestants in this match.")

    if score_a is not None:
        match.score_a = float(score_a)
    if score_b is not None:
        match.score_b = float(score_b)
    await _promote(db, match, winner_team_id)
    await db.commit()

    # Eliminate the loser in the pipeline (so leaderboard/advancement see it).
    loser = match.side_b_team_id if str(winner_team_id) == str(match.side_a_team_id) else match.side_a_team_id
    if loser is not None:
        try:
            from app.models.event import Event
            from app.services.pipeline_service import get_or_create_pipeline, _ordered_rounds

            event = (await db.execute(select(Event).where(Event.id == match.event_id))).scalars().first()
            if event:
                rounds = await _ordered_rounds(db, match.event_id)
                pipeline = await get_or_create_pipeline(db, event, rounds)
                elim = list((pipeline.data or {}).get("eliminated_team_ids", []))
                if str(loser) not in elim:
                    elim.append(str(loser))
                    pipeline.data = {**(pipeline.data or {}), "eliminated_team_ids": elim}
                    await db.commit()
        except Exception as exc:
            print(f"[bracket_service] eliminate loser failed: {exc}")

    # Live bracket signal (reuse the event bus).
    try:
        from app.services.event_bus import safe_publish
        from app.models.participant import Participant

        pids = (await db.execute(
            select(Participant.id).where(Participant.event_id == match.event_id)
        )).scalars().all()
        from app.models.event import Event as Ev
        event = (await db.execute(select(Ev).where(Ev.id == match.event_id))).scalars().first()
        targets = [str(p) for p in pids] + ([str(event.organizer_id)] if event and event.organizer_id else [])
        if targets:
            await safe_publish(targets, {"type": "bracket", "event_id": str(match.event_id), "match_id": str(match.id)})
    except Exception as exc:
        print(f"[bracket_service] bracket signal failed: {exc}")

    return match


async def bracket_standings(db: AsyncSession, round_id) -> list[dict]:
    """Rank the contestants of a bracket round by how far they advanced — this is
    the tournament's leaderboard / winner source (single-elim has no submission
    scores). Primary key: matches won (champion wins the most, runner-up next,
    then semifinal losers, …); ties broken by accumulated match score. Returns
    dicts shaped for BOTH the leaderboard view (id/team_id/final_score/status) and
    the winner proposal (rank/team_name/score)."""
    matches = (await db.execute(
        select(Match).where(Match.round_id == round_id)
    )).scalars().all()
    if not matches:
        return []

    max_round = max(m.round_number for m in matches)
    stats: dict = {}

    def _ensure(tid):
        if tid is not None and tid not in stats:
            stats[tid] = {"wins": 0, "points": 0.0, "reached": 0, "has_score": False}

    for m in matches:
        _ensure(m.side_a_team_id)
        _ensure(m.side_b_team_id)
        if m.side_a_team_id is not None:
            stats[m.side_a_team_id]["reached"] = max(stats[m.side_a_team_id]["reached"], m.round_number)
            if m.score_a is not None:
                stats[m.side_a_team_id]["points"] += float(m.score_a)
                stats[m.side_a_team_id]["has_score"] = True
        if m.side_b_team_id is not None:
            stats[m.side_b_team_id]["reached"] = max(stats[m.side_b_team_id]["reached"], m.round_number)
            if m.score_b is not None:
                stats[m.side_b_team_id]["points"] += float(m.score_b)
                stats[m.side_b_team_id]["has_score"] = True
        if m.winner_team_id is not None:
            _ensure(m.winner_team_id)
            stats[m.winner_team_id]["wins"] += 1

    finals = [m for m in matches if m.round_number == max_round]
    champion = finals[0].winner_team_id if finals else None

    names: dict = {}
    if stats:
        rows = (await db.execute(
            select(Team.id, Team.name).where(Team.id.in_(list(stats.keys())))
        )).all()
        names = {tid: nm for tid, nm in rows}

    ordered = sorted(
        stats.items(),
        key=lambda kv: (kv[1]["wins"], kv[1]["points"], kv[1]["reached"]),
        reverse=True,
    )

    standings: list[dict] = []
    for rank, (tid, st) in enumerate(ordered, start=1):
        score = st["points"] if st["has_score"] else float(st["wins"])
        if champion is not None and tid == champion:
            status = "Champion"
        elif st["reached"] >= max_round:
            status = "Runner-up"
        else:
            status = "Eliminated"
        standings.append({
            "id": str(tid),
            "team_id": str(tid),
            "team_name": names.get(tid, str(tid)[:8]),
            "rank": rank,
            "score": score,
            "final_score": score,
            "wins": st["wins"],
            "status": status,
        })
    return standings


async def get_bracket(db: AsyncSession, event_id) -> dict:
    """The full bracket grouped by round, team names resolved (None → 'TBD')."""
    matches = (await db.execute(
        select(Match).where(Match.event_id == event_id)
        .order_by(Match.round_number, Match.match_index)
    )).scalars().all()
    if not matches:
        return {"rounds": []}

    team_ids = set()
    for m in matches:
        for tid in (m.side_a_team_id, m.side_b_team_id, m.winner_team_id):
            if tid:
                team_ids.add(tid)
    names: dict = {}
    if team_ids:
        rows = (await db.execute(select(Team.id, Team.name).where(Team.id.in_(list(team_ids))))).all()
        names = {tid: nm for tid, nm in rows}

    def label(tid, *, completed=False):
        if tid:
            return names.get(tid, "TBD")
        # An empty side of an already-completed match is a BYE (the other side
        # auto-advanced); an empty side of a not-yet-played match is still TBD.
        return "Bye" if completed else "TBD"

    by_round: dict[int, list] = {}
    for m in matches:
        is_done = m.status == "completed"
        by_round.setdefault(m.round_number, []).append({
            "id": str(m.id),
            "match_index": m.match_index,
            "side_a": {"team_id": str(m.side_a_team_id) if m.side_a_team_id else None, "name": label(m.side_a_team_id, completed=is_done)},
            "side_b": {"team_id": str(m.side_b_team_id) if m.side_b_team_id else None, "name": label(m.side_b_team_id, completed=is_done)},
            "winner_team_id": str(m.winner_team_id) if m.winner_team_id else None,
            "score_a": m.score_a,
            "score_b": m.score_b,
            "scheduled_at": m.scheduled_at.isoformat() if m.scheduled_at else None,
            "match_link": m.match_link,
            "status": m.status,
        })
    rounds = [{"round_number": r, "matches": by_round[r]} for r in sorted(by_round)]
    return {"rounds": rounds}
