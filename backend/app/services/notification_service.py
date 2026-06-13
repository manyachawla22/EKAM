"""
EKAM Notification Service

Handles in-app notifications.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.notification import Notification, NotificationType


async def create_notification(
    db: AsyncSession,
    event_id: str,
    user_id: str,
    title: str,
    message: str,
    notification_type: NotificationType = NotificationType.info,
    action_link: str | None = None
) -> Notification:
    
    notification = Notification(
        event_id=event_id,
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
        action_link=action_link
    )
    
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    # Push a live "notification" signal to the recipient's open dashboards (SSE).
    # Best-effort: never let the bus break the notification write.
    from app.services.event_bus import safe_publish
    await safe_publish(
        [str(user_id)],
        {
            "type": "notification",
            "event_id": str(event_id) if event_id else None,
            "id": str(notification.id),
        },
    )

    return notification


async def list_notifications(
    db: AsyncSession,
    user_id: str,
    unread_only: bool = False
):
    query = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        query = query.where(Notification.is_read == False)
        
    query = query.order_by(Notification.created_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


async def mark_notification_read(
    db: AsyncSession,
    notification_id: str
):
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    notification = result.scalars().first()
    
    if notification:
        notification.is_read = True
        await db.commit()
        
    return notification
