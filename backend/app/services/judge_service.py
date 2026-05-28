from fastapi import HTTPException
from sqlalchemy.future import select

from app.models.judge import Judge


class JudgeService:

    @staticmethod
    async def create_judge(
        db,
        judge_data
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
                detail="Judge already exists"
            )

        judge = Judge(
            **judge_data.model_dump()
        )

        db.add(judge)

        await db.commit()
        await db.refresh(judge)

        return judge


    @staticmethod
    async def list_judges(
        db,
        event_id
    ):

        result = await db.execute(
            select(Judge).where(
                Judge.event_id == event_id
            )
        )

        return result.scalars().all()