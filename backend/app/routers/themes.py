"""
EKAM Themes Router
"""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.auth_context import AuthContext
from app.middleware.auth import require_actor_type, require_event_access
from app.models.theme import Theme as ThemeModel
from app.schemas.theme import ThemeCreate, ThemeResponse

router = APIRouter(
    prefix="/themes",
    tags=["Themes"]
)


@router.get(
    "/{event_id}",
    response_model=List[ThemeResponse],
    dependencies=[
        Depends(require_actor_type(["organizer", "participant", "judge"])),
        Depends(require_event_access("event_id"))
    ]
)
async def list_themes(
    event_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """List all themes for an event."""
    result = await db.execute(
        select(ThemeModel).where(ThemeModel.event_id == event_id)
    )
    return result.scalars().all()


@router.post(
    "/{event_id}",
    response_model=ThemeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def create_theme(
    event_id: UUID,
    body: ThemeCreate,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    """Create a new theme for an event."""
    theme = ThemeModel(
        event_id=event_id,
        name=body.name,
        description=body.description,
        required_skills=body.required_skills or []
    )
    db.add(theme)
    try:
        await db.commit()
        await db.refresh(theme)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Theme with this name already exists for this event.")
    return theme
