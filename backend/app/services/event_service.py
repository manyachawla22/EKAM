from fastapi import HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.user import User, UserRole
from app.schemas.event import EventCreate, EventUpdate


async def create_event_service(
    db: AsyncSession,
    event_data: EventCreate,
    current_user: User
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


async def get_event_service(
    db: AsyncSession,
    event_id,
    current_user: User = None
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


async def list_events_service(
    db: AsyncSession,
    current_user: User = None
):

    result = await db.execute(
        select(Event)
    )

    return result.scalars().all()


async def update_event_service(
    db: AsyncSession,
    event_id,
    event_data: EventUpdate,
    current_user: User
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


async def delete_event_service(
    db: AsyncSession,
    event_id,
    current_user: User
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