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
from app.models.approval import RequestType

from app.services.cpsat_team_service import generate_teams
from app.services.cpsat_judge_service import generate_assignments
from app.services.approval_service import create_approval_request


# =========================================================
# TEAM FORMATION
# =========================================================

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

    payload = {
        "event_id": event_id,          # needed by execute_team_formation
        "requested_by": requested_by,  # preserved for email triggers
        "teams": teams_dict,
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

    return created_teams


# =========================================================
# JUDGE ASSIGNMENT
# =========================================================

async def propose_judge_assignment(
    db: AsyncSession,
    event_id: str,
    requested_by: str,
    round_id: str,
    judges_per_team: int = 2,
    max_teams_per_judge: int = 5,
):
    """
    1. Fetch judges and teams from DB (scoped to event).
    2. Run pure CP-SAT optimizer.
    3. Create an ApprovalRequest.
    """
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

    # Judge model uses `institution`, not `organization`
    judge_dicts = [
        {
            "id": str(j.id),
            "name": j.name,
            "email": j.email,
            "institution": j.institution or "Unknown",
            "expertise": j.expertise or [],
        }
        for j in judges_db
    ]

    team_dicts = [
        {
            "id": str(t.id),
            "institution": "Unknown",
            "theme": str(t.theme_id) if t.theme_id else "General",
        }
        for t in teams_db
    ]

    assignments = await generate_assignments(
        judges=judge_dicts,
        teams=team_dicts,
        judges_per_team=judges_per_team,
        max_teams_per_judge=max_teams_per_judge,
    )

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

    return created


# =========================================================
# MANUAL OPERATIONS (Fallbacks)
# =========================================================

async def assign_team_member_service(db: AsyncSession, member_data):
    member = TeamMember(**member_data.model_dump())
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def assign_single_judge_service(db: AsyncSession, assignment_data):
    assignment = JudgeAssignment(**assignment_data.model_dump())
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment
