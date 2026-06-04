"""
EKAM Assignment Service

Handles CP-SAT orchestrations for Team Formation and Judge Assignment.
Integrates with the Approval Workflow.
"""

from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.participant import Participant
from app.models.judge import Judge, JudgeAssignment
from app.models.team import Team, TeamMember
from app.models.event import Round, Event
from app.models.theme import Theme
from app.models.approval import RequestType

from app.services.cpsat_team_service import generate_teams
from app.services.cpsat_judge_service import generate_assignments
from app.services.approval_service import create_approval_request
from app.services.llm_service import complete_json


# =========================================================
# TEAM FORMATION
# =========================================================

def _fallback_rationale(members: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Deterministic per-team rationale used when the LLM is unavailable."""
    skills, institutions = [], []
    for m in members:
        skills.extend(m.get("skills") or [])
        if m.get("institution") and m["institution"] != "Unknown":
            institutions.append(m["institution"])
    unique_skills = list(dict.fromkeys(skills))
    inst_note = (
        "a single institution" if len(set(institutions)) <= 1 and institutions
        else f"{len(set(institutions))} institutions"
    )
    return {
        "rationale": (
            f"This team pairs members covering {len(unique_skills)} distinct skill(s) "
            f"across {inst_note}, giving balanced coverage for cross-functional work."
        ),
        "strengths": unique_skills[:3] or ["Cross-domain collaboration", "Adaptability"],
        "watch_out_for": "Aligning on scope and ownership early to avoid overlap.",
    }


async def _build_team_rationales(
    teams_dict: Dict[Any, List[Dict[str, Any]]],
) -> Dict[str, Dict[str, Any]]:
    """Produce a review note per proposed team.

    One LLM call covers all teams; on any failure each team gets a deterministic
    fallback so the organizer always has something to review.
    """
    fallback = {str(k): _fallback_rationale(v) for k, v in teams_dict.items()}
    if not teams_dict:
        return fallback

    compact = {
        str(k): [
            {
                "name": m.get("name", "Participant"),
                "skills": m.get("skills") or [],
                "institution": m.get("institution", "Unknown"),
            }
            for m in v
        ]
        for k, v in teams_dict.items()
    }
    system = (
        "You are an event organizer reviewing proposed hackathon team "
        "compositions. For EACH team key, explain why the grouping works. "
        'Return ONLY JSON of the shape {"<key>": {"rationale": "2-3 sentences", '
        '"strengths": ["..."], "watch_out_for": "one risk"}} using the exact '
        "team keys provided."
    )
    import json as _json

    result = await complete_json(system, _json.dumps(compact), max_tokens=1500)
    if not isinstance(result, dict):
        return fallback

    merged: Dict[str, Dict[str, Any]] = {}
    for key in compact:
        item = result.get(key)
        if isinstance(item, dict) and item.get("rationale"):
            merged[key] = {
                "rationale": str(item.get("rationale", "")),
                "strengths": item.get("strengths") or fallback[key]["strengths"],
                "watch_out_for": str(
                    item.get("watch_out_for") or fallback[key]["watch_out_for"]
                ),
            }
        else:
            merged[key] = fallback[key]
    return merged

async def propose_team_formation(
    db: AsyncSession,
    event_id: str,
    requested_by: str,
    team_size: int = 3,
    constraints: List[Dict[str, Any]] = None,
):
    """
    1. Fetch unassigned participants from DB.
    2. Run pure CP-SAT optimizer (no DB writes).
    3. Create an ApprovalRequest with the proposed teams.
    """
    if constraints is None:
        constraints = []

    result = await db.execute(
        select(Participant).where(Participant.event_id == event_id)
    )
    participants_db = result.scalars().all()

    if not participants_db:
        raise ValueError("No participants found for this event")

    # Participant model uses `institution`, not `organization`
    participant_dicts = [
        {
            "id": str(p.id),
            "name": p.name,
            "email": p.email,
            "skills": p.skills or [],
            "institution": p.institution or "Unknown",
            "gender": p.gender or "Unknown",
            "experience_level": "Beginner",
        }
        for p in participants_db
    ]

    teams_dict, leftover = await generate_teams(
        participants=participant_dicts,
        constraints=constraints,
        team_size=team_size,
    )

    # Per-team review notes (the "rationale" the organizer reviews before
    # approving). Stored alongside the teams so the frontend can show it.
    rationales = await _build_team_rationales(teams_dict)

    payload = {
        "event_id": event_id,          # needed by execute_team_formation
        "requested_by": requested_by,  # preserved for email triggers
        "teams": teams_dict,
        "rationales": rationales,
        "leftover_participants": leftover,
        "team_size": team_size,
    }

    approval = await create_approval_request(
        db=db,
        event_id=event_id,
        request_type=RequestType.team_formation,
        payload=payload,
        requested_by=requested_by,
    )

    return approval


async def execute_team_formation(
    db: AsyncSession,
    payload: dict,
):
    """
    Executed by the Approval Service after an Organizer approves.
    Persists teams to the DB atomically — rolls back on any failure.
    """
    event_id = payload.get("event_id")
    teams_dict = payload.get("teams", {})
    created_teams = []

    if not event_id:
        raise ValueError("execute_team_formation: event_id missing from approval payload")

    try:
        for team_index, members in teams_dict.items():
            team = Team(
                event_id=event_id,
                name=f"Team {int(team_index) + 1}",
            )
            db.add(team)
            await db.flush()  # get team.id before adding members

            for member_data in members:
                # TeamMember has is_leader (bool), not a role string
                tm = TeamMember(
                    team_id=team.id,
                    participant_id=member_data["id"],
                    is_leader=False,
                )
                db.add(tm)

            created_teams.append(team)

        await db.commit()
    except Exception:
        await db.rollback()
        raise

    # Auto-draft login emails for all participants in the formed teams.
    # We read IDs from teams_dict (already in memory) because team.members is
    # an unloaded async relationship after db.commit() and would always be empty.
    try:
        event_result = await db.execute(select(Event).where(Event.id == event_id))
        event_obj = event_result.scalars().first()
        if event_obj:
            participant_ids = [
                member_data["id"]
                for members in teams_dict.values()
                for member_data in members
            ]
            if participant_ids:
                p_result = await db.execute(
                    select(Participant).where(Participant.id.in_(participant_ids))
                )
                p_emails = [p.email for p in p_result.scalars().all() if p.email]
                if p_emails:
                    from app.services.email_service import draft_participant_login_emails
                    requested_by = payload.get("requested_by", str(event_obj.organizer_id))
                    await draft_participant_login_emails(
                        db=db,
                        event_id=event_id,
                        event_name=event_obj.name,
                        event_hash=event_obj.hash,
                        participant_emails=p_emails,
                        requested_by=requested_by,
                    )
    except Exception as e:
        print(f"[assignment_service] Auto email draft failed (non-fatal): {e}")

    # Pipeline: teams now exist → auto-propose the next transition.
    try:
        from app.services.pipeline_service import autopropose
        await autopropose(db, str(event_id))
    except Exception as e:
        print(f"[assignment_service] autopropose failed (non-fatal): {e}")

    return created_teams


# =========================================================
# JUDGE ASSIGNMENT
# =========================================================

async def propose_judge_assignment(
    db: AsyncSession,
    event_id: str,
    requested_by: str,
    round_id: str | None = None,
    judges_per_team: int = 3,
    max_teams_per_judge: int = 5,
):
    """
    1. Fetch judges and teams from DB (scoped to event).
    2. Run pure CP-SAT optimizer.
    3. Create an ApprovalRequest.

    Every team is reviewed by a panel of at least 3 judges (policy minimum), so
    `judges_per_team` is floored at 3 regardless of what the caller passes.
    """
    judges_per_team = max(3, judges_per_team)
    # Auto-detect the first round for the event when the caller doesn't specify
    # one. Order by created_at so this is deterministic (the panel is shared
    # across all rounds at grading time, but the stored round_id should still be
    # stable rather than whatever the DB happens to return first).
    if not round_id:
        rounds_result = await db.execute(
            select(Round)
            .where(Round.event_id == event_id)
            .order_by(Round.created_at)
            .limit(1)
        )
        round_obj = rounds_result.scalars().first()
        if not round_obj:
            raise ValueError(
                "No rounds exist for this event. Create at least one round before assigning judges."
            )
        round_id = str(round_obj.id)

    judges_result = await db.execute(
        select(Judge).where(Judge.event_id == event_id)
    )
    judges_db = judges_result.scalars().all()

    # Filter teams to this event
    teams_result = await db.execute(
        select(Team).where(Team.event_id == event_id)
    )
    teams_db = teams_result.scalars().all()

    if not judges_db or not teams_db:
        raise ValueError("Not enough judges or teams to run assignment")

    # Gate: all teams must have selected a theme before judges can be assigned.
    teams_without_theme = [t.name for t in teams_db if not t.theme_id]
    if teams_without_theme:
        names = ", ".join(teams_without_theme)
        raise ValueError(
            f"The following team(s) have not selected a theme yet: {names}. "
            f"All teams must select a theme before judge assignment can proceed."
        )

    # Judge model uses `institution`, not `organization`.
    # Use None (not a "Unknown" sentinel) when missing — the optimizer only
    # treats a shared institution as a conflict when BOTH sides are known, so a
    # placeholder must never collide.
    judge_dicts = [
        {
            "id": str(j.id),
            "name": j.name,
            "email": j.email,
            "institution": j.institution or None,
            "expertise": j.expertise or [],
        }
        for j in judges_db
    ]

    # Load each team's theme so the optimizer can score judge expertise against
    # the theme name + its required skills (the scorer reads theme_name /
    # required_skills). Without this the skill match never fires.
    theme_ids = [t.theme_id for t in teams_db if t.theme_id]
    theme_map: Dict[Any, Theme] = {}
    if theme_ids:
        theme_res = await db.execute(select(Theme).where(Theme.id.in_(theme_ids)))
        theme_map = {th.id: th for th in theme_res.scalars().all()}

    # Teams don't track an institution, so leave it None (no conflict applied).
    team_dicts = [
        {
            "id": str(t.id),
            "institution": None,
            "theme": str(t.theme_id) if t.theme_id else "General",
            "theme_name": theme_map[t.theme_id].name if t.theme_id in theme_map else "",
            "required_skills": (theme_map[t.theme_id].required_skills or []) if t.theme_id in theme_map else [],
        }
        for t in teams_db
    ]

    assignments = await generate_assignments(
        judges=judge_dicts,
        teams=team_dicts,
        judges_per_team=judges_per_team,
        max_teams_per_judge=max_teams_per_judge,
    )

    # Enrich each assignment with human-readable fields so the stored payload
    # (and every UI that renders it) shows judge name + institution and the team
    # name instead of raw ids. execute_judge_assignment still reads the ids.
    judge_by_id = {j["id"]: j for j in judge_dicts}
    team_name_by_id = {str(t.id): t.name for t in teams_db}
    for a in assignments:
        j = judge_by_id.get(a.get("judge_id"), {})
        a["judge_name"] = j.get("name")
        a["judge_institution"] = j.get("institution")
        a["team_name"] = team_name_by_id.get(a.get("team_id"))

    payload = {
        "event_id": event_id,
        "round_id": round_id,          # required by JudgeAssignment model
        "requested_by": requested_by,
        "assignments": assignments,
    }

    approval = await create_approval_request(
        db=db,
        event_id=event_id,
        request_type=RequestType.judge_assignment,
        payload=payload,
        requested_by=requested_by,
    )

    return approval


async def execute_judge_assignment(
    db: AsyncSession,
    payload: dict,
):
    """
    Executed by the Approval Service after an Organizer approves.
    Persists judge assignments to the DB atomically.
    JudgeAssignment requires judge_id, team_id, round_id (all NOT NULL).
    """
    round_id = payload.get("round_id")
    assignments_data = payload.get("assignments", [])
    created = []

    if not round_id:
        raise ValueError("execute_judge_assignment: round_id missing from approval payload")

    try:
        for data in assignments_data:
            assignment = JudgeAssignment(
                judge_id=data["judge_id"],
                team_id=data["team_id"],
                round_id=round_id,
            )
            db.add(assignment)
            created.append(assignment)

        await db.commit()
    except Exception:
        await db.rollback()
        raise

    # Auto-draft login emails for all assigned judges
    try:
        event_result = await db.execute(select(Event).where(Event.id == payload.get("event_id")))
        event_obj = event_result.scalars().first()
        if event_obj and assignments_data:
            judge_ids = [data["judge_id"] for data in assignments_data]
            j_result = await db.execute(
                select(Judge).where(Judge.id.in_(judge_ids))
            )
            j_emails = list({j.email for j in j_result.scalars().all() if j.email})
            if j_emails:
                from app.services.email_service import draft_judge_login_emails
                requested_by = payload.get("requested_by", str(event_obj.organizer_id))
                await draft_judge_login_emails(
                    db=db,
                    event_id=str(event_obj.id),
                    event_name=event_obj.name,
                    event_hash=event_obj.hash,
                    judge_emails=j_emails,
                    requested_by=requested_by,
                )
    except Exception as e:
        print(f"[assignment_service] Auto judge email draft failed (non-fatal): {e}")

    # Pipeline: judges assigned → auto-propose the next transition.
    try:
        from app.services.pipeline_service import autopropose
        if payload.get("event_id"):
            await autopropose(db, str(payload.get("event_id")))
    except Exception as e:
        print(f"[assignment_service] autopropose failed (non-fatal): {e}")

    return created


# =========================================================
# MANUAL OPERATIONS (Fallbacks)
# =========================================================

async def assign_team_member_service(db: AsyncSession, member_data):
    member = TeamMember(**member_data.model_dump())
    db.add(member)
    await db.commit()
    # TeamMemberResponse declares a nested `participant` field — load it
    # eagerly so Pydantic can serialize the response without lazy-loading
    # outside the async session (MissingGreenlet).
    await db.refresh(member, attribute_names=["participant"])
    return member


async def assign_single_judge_service(db: AsyncSession, assignment_data):
    assignment = JudgeAssignment(**assignment_data.model_dump())
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment
