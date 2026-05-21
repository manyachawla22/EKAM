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
