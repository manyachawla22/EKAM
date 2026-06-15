from fastapi import HTTPException
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, EventStatus
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
    # A freshly created event is live (registration open), not a perpetual
    # draft — otherwise the status badge never leaves "draft". The pipeline
    # flips it to "completed" when the event finishes.
    if event.status in (None, EventStatus.draft):
        event.status = EventStatus.active
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

    previous_stage = event.stage

    update_data = event_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(event, key, value)

    # Keep status in sync with the stage so "completed" events read as completed
    # even when the organizer advances the stage manually.
    from app.models.event import EventStage

    if event.stage == EventStage.completed:
        event.status = EventStatus.completed
    elif event.status == EventStatus.completed and event.stage != EventStage.completed:
        # Re-opened a completed event by moving the stage back.
        event.status = EventStatus.active

    await db.commit()
    await db.refresh(event, attribute_names=["rounds"])

    # When the organizer advances the stage manually, fire the stage email
    # pipeline (results announcements, certificate distribution, etc.). Without
    # this, only the approval-driven path triggered emails, so manual stage
    # changes silently skipped certificates/announcements. Best-effort.
    if event.stage != previous_stage:
        try:
            from app.email_triggers import trigger_stage_emails

            await trigger_stage_emails(
                event=event,
                new_stage=event.stage,
                db=db,
                requested_by=str(getattr(current_user, "id", "organizer")),
            )
        except Exception as exc:
            print(f"[event_service] stage email trigger failed: {exc}")

    return event


async def delete_event_service(
    db: AsyncSession,
    event_id,
    current_user: User,
):
    from sqlalchemy import text

    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if current_user and hasattr(current_user, "role") and current_user.role.value != "admin":
        if str(event.organizer_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Cannot delete another organizer's event")

    # The event has many child rows across tables whose FKs are NOT ON DELETE
    # CASCADE, so a bare ORM delete fails (FK violation / NOT-NULL on SET NULL).
    # Delete the whole graph explicitly, leaves-first.
    eid = {"e": str(event_id)}
    cascade = [
        "DELETE FROM matches WHERE event_id = :e",
        "DELETE FROM anomalies WHERE event_id = :e",
        "DELETE FROM evaluations WHERE submission_id IN "
        "(SELECT s.id FROM submissions s JOIN rounds r ON s.round_id = r.id WHERE r.event_id = :e)",
        "DELETE FROM judge_assignments WHERE round_id IN (SELECT id FROM rounds WHERE event_id = :e)",
        "DELETE FROM submissions WHERE round_id IN (SELECT id FROM rounds WHERE event_id = :e)",
        "DELETE FROM rubric_criteria WHERE round_id IN (SELECT id FROM rounds WHERE event_id = :e)",
        "DELETE FROM team_members WHERE team_id IN (SELECT id FROM teams WHERE event_id = :e)",
        "DELETE FROM team_preferences WHERE team_id IN (SELECT id FROM teams WHERE event_id = :e)",
        "DELETE FROM email_drafts WHERE event_id = :e",
        "DELETE FROM approval_requests WHERE event_id = :e",
        "DELETE FROM notifications WHERE event_id = :e",
        "DELETE FROM reports WHERE event_id = :e",
        "DELETE FROM event_pipeline WHERE event_id = :e",
        "DELETE FROM teams WHERE event_id = :e",
        "DELETE FROM participants WHERE event_id = :e",
        "DELETE FROM judges WHERE event_id = :e",
        "DELETE FROM rounds WHERE event_id = :e",
        "DELETE FROM themes WHERE event_id = :e",
        "DELETE FROM events WHERE id = :e",
    ]
    for stmt in cascade:
        await db.execute(text(stmt), eid)
    await db.commit()
    return {"message": "Event deleted"}
