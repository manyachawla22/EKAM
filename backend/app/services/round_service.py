"""
EKAM Round Service
"""

from fastapi import HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Round, RoundStatus
from app.schemas.event import RoundCreate


async def create_round_service(
    db: AsyncSession,
    round_data: RoundCreate,
    current_user=None,
) -> Round:
    round_obj = Round(
        event_id=round_data.event_id,
        name=round_data.name,
        description=round_data.description,
        status=round_data.status or RoundStatus.upcoming,
        start_date=round_data.start_date,
        end_date=round_data.end_date,
    )
    db.add(round_obj)
    try:
        await db.commit()
        await db.refresh(round_obj)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not create round: {type(e).__name__}: {e}",
        )
    return round_obj


async def list_rounds_service(
    db: AsyncSession,
    event_id,
) -> list[Round]:
    result = await db.execute(
        select(Round)
        .where(Round.event_id == event_id)
        .order_by(Round.created_at)
    )
    return list(result.scalars().all())


async def delete_round_service(
    db: AsyncSession,
    event_id,
    round_id,
) -> None:
    result = await db.execute(
        select(Round).where(Round.id == round_id, Round.event_id == event_id)
    )
    round_obj = result.scalars().first()
    if not round_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Round not found")
    await db.delete(round_obj)
    await db.commit()
