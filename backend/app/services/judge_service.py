from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.judge import Judge


async def create_judge_service(
    db: AsyncSession,
    judge_data,
    current_user=None
):

    existing = await db.execute(
        select(Judge).where(
            Judge.event_id == judge_data.event_id,
            Judge.email == judge_data.email
        )
    )

    if existing.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="Judge already registered"
        )

    judge = Judge(
        **judge_data.model_dump()
    )

    db.add(judge)

    await db.commit()
    await db.refresh(judge)

    return judge


async def list_judges_service(
    db: AsyncSession,
    event_id
):

    result = await db.execute(
        select(Judge).where(
            Judge.event_id == event_id
        )
    )

    return result.scalars().all()


async def get_judge_by_id_service(
    db: AsyncSession,
    judge_id: str
):
    result = await db.execute(
        select(Judge).where(
            Judge.id == judge_id
        )
    )

    return result.scalars().first()