import uuid
from fastapi import HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.team import Team, TeamMember
from app.models.participant import Participant


async def create_team_service(
    db: AsyncSession,
    team_data,
    current_user=None
):

    existing = await db.execute(
        select(Team).where(
            Team.event_id == team_data.event_id,
            Team.name == team_data.name
        )
    )

    if existing.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="Team name already taken"
        )

    team = Team(
        **team_data.model_dump()
    )

    db.add(team)

    await db.commit()
    await db.refresh(team)

    return team


async def list_teams_service(
    db: AsyncSession,
    event_id
):

    result = await db.execute(
        select(Team)
        .where(Team.event_id == event_id)
        .options(selectinload(Team.members))
    )

    return result.scalars().all()


async def get_team_by_id_service(
    db: AsyncSession,
    team_id: str
):
    result = await db.execute(
        select(Team).where(
            Team.id == team_id
        )
    )

    return result.scalars().first()