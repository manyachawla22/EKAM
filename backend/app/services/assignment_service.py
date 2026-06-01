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

    return created_teams


# =========================================================
# JUDGE ASSIGNMENT
# =========================================================

async def propose_judge_assignment(
    db: AsyncSession,
    event_id: str,
    requested_by: str,
    round_id: str | None = None,
    judges_per_team: int = 2,
    max_teams_per_judge: int = 5,
):
    """
    1. Fetch judges and teams from DB (scoped to event).
    2. Run pure CP-SAT optimizer.
    3. Create an ApprovalRequest.
    """
    # Auto-detect first round for the event when caller doesn't specify one
    if not round_id:
        rounds_result = await db.execute(
            select(Round).where(Round.event_id == event_id).limit(1)
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
