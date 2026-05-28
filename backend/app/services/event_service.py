from fastapi import HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.user import User, UserRole
from app.schemas.event import EventCreate, EventUpdate


class EventService:

    @staticmethod
    async def create_event(
        db: AsyncSession,
        current_user: User,
        event_data: EventCreate
    ):

        if (
            str(event_data.organizer_id) != str(current_user.id)
            and current_user.role != UserRole.admin
        ):
            raise HTTPException(
                status_code=403,
                detail="Cannot create event for another organizer"
            )

        event = Event(**event_data.model_dump())

        db.add(event)

        try:
            await db.commit()
            await db.refresh(event)

        except Exception:
            await db.rollback()

            raise HTTPException(
                status_code=400,
                detail="Invalid event data"
            )

        return event


    @staticmethod
    async def get_event(
        db: AsyncSession,
        event_id
    ):

        result = await db.execute(
            select(Event).where(Event.id == event_id)
        )

        event = result.scalars().first()

        if not event:
            raise HTTPException(
                status_code=404,
                detail="Event not found"
            )

        return event


    @staticmethod
    async def list_events(
        db: AsyncSession
    ):

        result = await db.execute(
            select(Event)
        )

        return result.scalars().all()


    @staticmethod
    async def update_event(
        db: AsyncSession,
        event_id,
        event_data: EventUpdate
    ):

        result = await db.execute(
            select(Event).where(Event.id == event_id)
        )

        event = result.scalars().first()

        if not event:
            raise HTTPException(
                status_code=404,
                detail="Event not found"
            )

        update_data = event_data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(event, key, value)

        await db.commit()
        await db.refresh(event)

        return event


    @staticmethod
    async def delete_event(
        db: AsyncSession,
        event_id
    ):

        result = await db.execute(
            select(Event).where(Event.id == event_id)
        )

        event = result.scalars().first()

        if not event:
            raise HTTPException(
                status_code=404,
                detail="Event not found"
            )

        await db.delete(event)

        await db.commit()

        return {"message": "Event deleted"}