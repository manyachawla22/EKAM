from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.participant import Team, TeamMember
from app.schemas.participant import Team as TeamSchema, TeamCreate, TeamMember as TeamMemberSchema, TeamMemberCreate

router = APIRouter()

@router.post("/create", response_model=TeamSchema, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_in: TeamCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    new_team = Team(**team_in.model_dump())
    db.add(new_team)
    await db.commit()
    await db.refresh(new_team)
    return new_team

@router.post("/assign", response_model=TeamMemberSchema, status_code=status.HTTP_201_CREATED)
async def assign_team_member(
    member_in: TeamMemberCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    new_member = TeamMember(**member_in.model_dump())
    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)
    return new_member

@router.get("/{event_id}", response_model=List[TeamSchema])
async def list_teams(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Team).where(Team.event_id == event_id))
    return result.scalars().all()

from app.team_formation.optimizer import form_teams, compute_team_diversity_score
from app.models.participant import Participant

@router.post("/auto-form/{event_id}")
async def auto_form_teams(
    event_id: UUID,
    team_size: int = 4,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Fetch participants for the event
    result = await db.execute(select(Participant).where(Participant.event_id == event_id))
    participants = result.scalars().all()
    
    # Fake data if none
    if not participants:
        p_data = [
            {"id": "1", "skills": ["Backend", "ML"], "domain": "AI/ML", "experience_level": "Advanced", "institution": "A"},
            {"id": "2", "skills": ["Frontend"], "domain": "Web/App Dev", "experience_level": "Beginner", "institution": "A"},
            {"id": "3", "skills": ["Design"], "domain": "Web/App Dev", "experience_level": "Intermediate", "institution": "B"},
            {"id": "4", "skills": ["ML", "Research"], "domain": "AI/ML", "experience_level": "Advanced", "institution": "B"},
        ]
    else:
        p_data = [
            {
                "id": str(p.id),
                "skills": ["Backend", "Frontend"],  # Mocked skills since model doesn't have it
                "domain": "Web/App Dev",
                "experience_level": "Intermediate",
                "institution": "Unknown"
            } for p in participants
        ]
        
    try:
        teams, leftovers = form_teams(p_data, team_size=team_size)
        return {
            "success": True,
            "teams": teams,
            "leftovers": leftovers,
            "message": f"Successfully formed {len(teams)} teams"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
