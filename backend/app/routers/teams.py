"""
EKAM Teams Router
"""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.auth_context import AuthContext
from app.middleware.auth import require_actor_type, require_event_access

from app.models.team import Team as TeamModel

from app.schemas.team import (
    Team,
    TeamCreate,
    TeamUpdate
)

from app.services.team_service import (
    create_team_service,
    list_teams_service
)
from app.services.assignment_service import propose_team_formation

router = APIRouter(
    prefix="/teams",
    tags=["Teams"]
)


@router.post(
    "/{event_id}/auto-form",
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def auto_form_teams(
    event_id: str,
    team_size: int = 3,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger CP-SAT team formation.
    Creates a pending ApprovalRequest with the proposed teams.
    """
    try:
        approval = await propose_team_formation(
            db=db,
            event_id=event_id,
            requested_by=auth.actor_id,
            team_size=team_size,
            constraints=[] # Add custom constraint payloads here later
        )
        return {
            "message": "CP-SAT team formation proposed.",
            "approval_id": str(approval.id)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/create",
    response_model=Team,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_actor_type(["organizer"]))]
)
async def create_team(
    team_in: TeamCreate,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    """Manually create a team."""
    if not auth.can_access_event(str(team_in.event_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No event access"
        )
    return await create_team_service(db, team_in)


@router.get(
    "/{event_id}",
    response_model=List[Team],
    dependencies=[
        Depends(require_actor_type(["organizer", "judge", "participant"])),
        Depends(require_event_access("event_id"))
    ]
)
async def list_teams(
    event_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """List all teams for an event."""
    return await list_teams_service(db, event_id)


@router.get(
    "/{event_id}/{team_id}",
    response_model=Team,
    dependencies=[
        Depends(require_actor_type(["organizer", "judge", "participant"])),
        Depends(require_event_access("event_id"))
    ]
)
async def get_team(
    event_id: UUID,
    team_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific team by ID."""
    # We do a simplified query. Depending on schema, we might want members too.
    result = await db.execute(select(TeamModel).where(TeamModel.id == team_id))
    team = result.scalars().first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.put(
    "/{event_id}/{team_id}/theme",
    response_model=Team,
    dependencies=[
        Depends(require_actor_type(["organizer", "participant"])),
        Depends(require_event_access("event_id"))
    ]
)
async def update_team_theme(
    event_id: UUID,
    team_id: UUID,
    team_in: TeamUpdate,
    auth: AuthContext = Depends(require_actor_type(["organizer", "participant"])),
    db: AsyncSession = Depends(get_db)
):
    """Update team theme. Can be done by organizer or team member."""
    result = await db.execute(select(TeamModel).where(TeamModel.id == team_id))
    team = result.scalars().first()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
        
    # Validation for participant: must be in the team (simplified for now)
    # Ideally we check TeamMember relationship here
    if auth.actor_type == "participant":
        pass # Add participant team validation here later
        
    if team_in.theme_id:
        team.theme_id = team_in.theme_id
    if team_in.name:
        team.name = team_in.name
        
    await db.commit()
    await db.refresh(team)
    return team
