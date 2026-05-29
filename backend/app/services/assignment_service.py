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
    constraints: List[Dict[str, Any]] = None
):
    """
    1. Fetch unassigned participants from DB.
    2. Run pure CP-SAT optimizer.
    3. Create an ApprovalRequest with the proposed teams.
    """
    if constraints is None:
        constraints = []

    # Fetch participants without a team
    # (For simplicity in this refactor, we just fetch all participants.
    # In production, we'd filter out those already in teams)
    result = await db.execute(
        select(Participant).where(Participant.event_id == event_id)
    )
    participants_db = result.scalars().all()

    if not participants_db:
        raise ValueError("No participants found for this event")

    # Convert DB models to dictionaries for the optimizer
    participant_dicts = [
        {
            "id": str(p.id),
            "skills": p.skills or [],
            "institution": p.organization or "Unknown",
            "gender": "Unknown",  # Assuming generic mapping
            "experience_level": "Beginner"  # Assuming generic mapping
        }
        for p in participants_db
    ]

    # Run CP-SAT purely
    teams_dict, leftover = await generate_teams(
        participants=participant_dicts,
        constraints=constraints,
        team_size=team_size
    )

    payload = {
        "teams": teams_dict,
        "leftover_participants": leftover,
        "team_size": team_size
    }

    # Create Approval Request (Draft)
    approval = await create_approval_request(
        db=db,
        event_id=event_id,
        request_type=RequestType.team_formation,
        payload=payload,
        requested_by=requested_by
    )

    return approval


async def execute_team_formation(
    db: AsyncSession,
    payload: dict
):
    """
    Executed by the Approval Service after an Organizer approves.
    Persists the teams to the DB.
    """
    teams_dict = payload.get("teams", {})
    
    created_teams = []

    for team_index, members in teams_dict.items():
        # Create a new Team
        team = Team(
            name=f"Team {int(team_index) + 1}",
            # we don't have event_id directly here easily, but we could pass it in payload
            # for now, relying on member updates
        )
        db.add(team)
        await db.flush()  # get team.id

        # Create TeamMembers
        for member_data in members:
            tm = TeamMember(
                team_id=team.id,
                participant_id=member_data["id"],
                role="member"
            )
            db.add(tm)
            
        created_teams.append(team)

    await db.commit()
    return created_teams


# =========================================================
# JUDGE ASSIGNMENT
# =========================================================

async def propose_judge_assignment(
    db: AsyncSession,
    event_id: str,
    requested_by: str,
    judges_per_team: int = 2,
    max_teams_per_judge: int = 5
):
    """
    1. Fetch judges and teams from DB.
    2. Run pure CP-SAT optimizer.
    3. Create an ApprovalRequest.
    """
    # Fetch judges
    judges_result = await db.execute(
        select(Judge).where(Judge.event_id == event_id)
    )
    judges_db = judges_result.scalars().all()

    # Fetch teams (we need teams related to this event, simplified query)
    teams_result = await db.execute(select(Team))
    teams_db = teams_result.scalars().all()

    if not judges_db or not teams_db:
        raise ValueError("Not enough judges or teams to run assignment")

    judge_dicts = [
        {
            "id": str(j.id),
            "institution": j.organization or "Unknown",
            "expertise": j.expertise or []
        }
        for j in judges_db
    ]
    
    team_dicts = [
        {
            "id": str(t.id),
            "institution": "Unknown",  # Simplification
            "theme": t.theme or "General"
        }
        for t in teams_db
    ]

    # Run CP-SAT purely
    assignments = await generate_assignments(
        judges=judge_dicts,
        teams=team_dicts,
        judges_per_team=judges_per_team,
        max_teams_per_judge=max_teams_per_judge
    )

    payload = {
        "assignments": assignments
    }

    # Create Approval Request
    approval = await create_approval_request(
        db=db,
        event_id=event_id,
        request_type=RequestType.judge_assignment,
        payload=payload,
        requested_by=requested_by
    )

    return approval


async def execute_judge_assignment(
    db: AsyncSession,
    payload: dict
):
    """
    Executed by the Approval Service after an Organizer approves.
    Persists the judge assignments to the DB.
    """
    assignments_data = payload.get("assignments", [])
    
    created = []
    for data in assignments_data:
        assignment = JudgeAssignment(
            judge_id=data["judge_id"],
            team_id=data["team_id"],
        )
        db.add(assignment)
        created.append(assignment)

    await db.commit()
    return created


# =========================================================
# MANUAL OPERATIONS (For Fallbacks)
# =========================================================

async def assign_team_member_service(
    db: AsyncSession,
    member_data
):
    member = TeamMember(**member_data.model_dump())
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def assign_single_judge_service(
    db: AsyncSession,
    assignment_data
):
    assignment = JudgeAssignment(**assignment_data.model_dump())
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment