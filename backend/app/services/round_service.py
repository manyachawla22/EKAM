from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# This is a stub for the Round schema, which might be in app.schemas.round or event
from app.schemas.event import RoundCreate


async def create_round_service(
    db: AsyncSession,
    round_data: RoundCreate,
    current_user=None
):
    # This is a placeholder since the Round model wasn't explicitly provided,
    # but based on the other services, we would typically do:
    # round_obj = Round(**round_data.model_dump())
    # db.add(round_obj)
    # await db.commit()
    # await db.refresh(round_obj)
    # return round_obj
    pass

async def list_rounds_service(
    db: AsyncSession,
    event_id: str
):
    # Placeholder
    # result = await db.execute(select(Round).where(Round.event_id == event_id))
    # return result.scalars().all()
    pass
