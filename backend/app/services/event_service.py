from fastapi import HTTPException
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.user import User, UserRole
from app.schemas.event import EventCreate, EventUpdate


async def create_event_service(
    db: AsyncSession,
    event_data: EventCreate,
    current_user: User,
):
    # Allow organizers to create their own events, admins to create for anyone.
    if (
        str(event_data.organizer_id) != str(current_user.id)
        and current_user.role != UserRole.admin
    ):
        raise HTTPException(
            status_code=403,
            detail="Cannot create event for another organizer",
        )

    event = Event(**event_data.model_dump())
    db.add(event)

    try:
        await db.commit()
        # EventResponse has `rounds: List[RoundResponse]`. Without eager-load,
        # Pydantic serialization triggers a lazy load outside the async
        # session and crashes with MissingGreenlet.
        await db.refresh(event, attribute_names=["rounds"])
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event data: {type(e).__name__}: {e}",
        )

    return event


async def get_event_service(
    db: AsyncSession,
    event_id,
    current_user: User = None,
):
    result = await db.execute(
        select(Event)
        .options(selectinload(Event.rounds))
        .where(Event.id == event_id)
    )
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


async def list_events_service(
    db: AsyncSession,
    current_user: User = None,
):
    query = select(Event).options(selectinload(Event.rounds))
    # Organizers only see their own events; admins see all
    if current_user and hasattr(current_user, "role") and current_user.role.value != "admin":
        query = query.where(Event.organizer_id == current_user.id)
    result = await db.execute(query)
    return result.scalars().all()


async def update_event_service(
    db: AsyncSession,
    event_id,
    event_data: EventUpdate,
    current_user: User,
):
    result = await db.execute(
        select(Event)
        .options(selectinload(Event.rounds))
        .where(Event.id == event_id)
    )
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if current_user and hasattr(current_user, "role") and current_user.role.value != "admin":
        if str(event.organizer_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Cannot modify another organizer's event")

    update_data = event_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(event, key, value)

    await db.commit()
    await db.refresh(event, attribute_names=["rounds"])
    return event


async def delete_event_service(
    db: AsyncSession,
    event_id,
    current_user: User,
):
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if current_user and hasattr(current_user, "role") and current_user.role.value != "admin":
        if str(event.organizer_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Cannot delete another organizer's event")

    await db.delete(event)
    await db.commit()
    return {"message": "Event deleted"}
