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

from app.models.team import Team as TeamModel, TeamMember, TeamPreference as TeamPreferenceModel
from app.models.participant import Participant as ParticipantModel

from app.schemas.team import (
    Team,
    TeamCreate,
    TeamUpdate,
    TeamPreferenceCreate,
    TeamPreferenceResponse,
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
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Team formation failed: {type(e).__name__}: {e}")


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


@router.delete(
    "/{event_id}/{team_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def delete_team(
    event_id: UUID,
    team_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a team and its members."""
    result = await db.execute(select(TeamModel).where(TeamModel.id == team_id))
    team = result.scalars().first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    await db.delete(team)
    await db.commit()


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
        
    if auth.actor_type == "participant":
        res_member = await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.participant_id == auth.actor_id,
            )
        )
        if not res_member.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team",
            )
        
    if team_in.theme_id:
        team.theme_id = team_in.theme_id
    if team_in.name:
        team.name = team_in.name

    await db.commit()
    await db.refresh(team)
    return team


# ─── Team Preferences ─────────────────────────────────────────────────────────

@router.get(
    "/{event_id}/{team_id}/preferences",
    response_model=List[TeamPreferenceResponse],
    dependencies=[
        Depends(require_actor_type(["organizer", "participant"])),
        Depends(require_event_access("event_id"))
    ]
)
async def get_team_preferences(
    event_id: UUID,
    team_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all member name+theme preferences for a team."""
    result = await db.execute(
        select(TeamPreferenceModel).where(TeamPreferenceModel.team_id == team_id)
    )
    return result.scalars().all()


@router.post(
    "/{event_id}/{team_id}/preferences",
    response_model=TeamPreferenceResponse,
    dependencies=[
        Depends(require_actor_type(["participant"])),
        Depends(require_event_access("event_id"))
    ]
)
async def submit_team_preference(
    event_id: UUID,
    team_id: UUID,
    body: TeamPreferenceCreate,
    auth: AuthContext = Depends(require_actor_type(["participant"])),
    db: AsyncSession = Depends(get_db)
):
    """Submit or update this participant's name+theme preference for the team."""
    # Verify the calling participant is a member of this team
    member_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.participant_id == auth.actor_id,
        )
    )
    if not member_result.scalars().first():
        raise HTTPException(status_code=403, detail="You are not a member of this team")

    # Upsert: update existing or create new
    pref_result = await db.execute(
        select(TeamPreferenceModel).where(
            TeamPreferenceModel.team_id == team_id,
            TeamPreferenceModel.participant_id == auth.actor_id,
        )
    )
    pref = pref_result.scalars().first()

    if pref:
        pref.preferred_name = body.preferred_name
        pref.preferred_theme_id = body.preferred_theme_id
    else:
        pref = TeamPreferenceModel(
            team_id=team_id,
            participant_id=auth.actor_id,
            preferred_name=body.preferred_name,
            preferred_theme_id=body.preferred_theme_id,
        )
        db.add(pref)

    await db.commit()
    await db.refresh(pref)

    # Run majority check after each submission
    await _resolve_team_preference(db, team_id, event_id)

    return pref


async def _resolve_team_preference(db: AsyncSession, team_id: UUID, event_id: UUID):
    """After each preference submission, check for majority and auto-apply or flag conflict."""
    from collections import Counter
    from app.models.team import Team as TeamModel

    # Load members
    members_result = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id)
    )
    members = members_result.scalars().all()

    # Load prefs
    prefs_result = await db.execute(
        select(TeamPreferenceModel).where(TeamPreferenceModel.team_id == team_id)
    )
    prefs = prefs_result.scalars().all()

    if len(prefs) < len(members):
        return  # Not all submitted yet

    votes = Counter((p.preferred_name, str(p.preferred_theme_id) if p.preferred_theme_id else None) for p in prefs)
    top_choice, top_count = votes.most_common(1)[0]

    team_result = await db.execute(select(TeamModel).where(TeamModel.id == team_id))
    team = team_result.scalars().first()
    if not team:
        return

    if top_count > len(members) / 2:
        team.name = top_choice[0]
        if top_choice[1]:
            import uuid as _uuid
            team.theme_id = _uuid.UUID(top_choice[1])
        await db.commit()
