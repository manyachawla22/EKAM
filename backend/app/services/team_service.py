from fastapi import HTTPException
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.team import Team, TeamMember
from app.models.participant import Participant  # noqa: F401  (used via relationship)


def _team_with_members():
    """Base query that eagerly loads members + each member's Participant so
    TeamResponse can serialize the nested `participant: {id, name, email, ...}`
    without triggering lazy loads outside the async session (MissingGreenlet).
    """
    return select(Team).options(
        selectinload(Team.members).selectinload(TeamMember.participant)
    )


async def create_team_service(
    db: AsyncSession,
    team_data,
    current_user=None,
):
    existing = await db.execute(
        select(Team).where(
            Team.event_id == team_data.event_id,
            Team.name == team_data.name,
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="Team name already taken",
        )

    team = Team(**team_data.model_dump())
    db.add(team)

    await db.commit()
    # Eager-load the (currently empty) members list so the response serializes.
    await db.refresh(team, attribute_names=["members"])
    return team


async def list_teams_service(
    db: AsyncSession,
    event_id,
):
    result = await db.execute(
        _team_with_members().where(Team.event_id == event_id)
    )
    return result.scalars().all()


async def get_team_by_id_service(
    db: AsyncSession,
    team_id: str,
):
    result = await db.execute(
        _team_with_members().where(Team.id == team_id)
    )
    return result.scalars().first()
