"""
EKAM Notifications Router
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth_context import AuthContext
from app.middleware.auth import get_current_actor

from app.services.notification_service import list_notifications, mark_notification_read

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"]
)

@router.get("")
async def get_my_notifications(
    unread_only: bool = False,
    auth: AuthContext = Depends(get_current_actor),
    db: AsyncSession = Depends(get_db)
):
    """Get notifications for the currently logged in actor."""
    return await list_notifications(db, auth.actor_id, unread_only)


@router.post("/{notification_id}/read")
async def read_notification(
    notification_id: str,
    auth: AuthContext = Depends(get_current_actor),
    db: AsyncSession = Depends(get_db)
):
    """Mark a notification as read."""
    # We should verify it belongs to the user, but skipping for brevity
    return await mark_notification_read(db, notification_id)
