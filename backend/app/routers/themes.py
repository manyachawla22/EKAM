"""
EKAM Themes Router
"""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.auth_context import AuthContext
from app.middleware.auth import require_actor_type, require_event_access
from app.models.theme import Theme as ThemeModel
from app.models.team import Team, TeamPreference
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
    # The body carries event_id; it must match the path it is created under.
    if body.event_id != event_id:
        raise HTTPException(
            status_code=400,
            detail="event_id in body does not match the event in the URL.",
        )

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


@router.delete(
    "/{event_id}/{theme_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def delete_theme(
    event_id: UUID,
    theme_id: UUID,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    """Delete a theme. Any teams/preferences pointing at it are cleared first."""
    result = await db.execute(
        select(ThemeModel).where(
            ThemeModel.id == theme_id,
            ThemeModel.event_id == event_id,
        )
    )
    theme = result.scalars().first()
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found.")

    # Clear references so the FK delete cannot fail.
    await db.execute(
        update(Team).where(Team.theme_id == theme_id).values(theme_id=None)
    )
    await db.execute(
        update(TeamPreference)
        .where(TeamPreference.preferred_theme_id == theme_id)
        .values(preferred_theme_id=None)
    )

    await db.delete(theme)
    await db.commit()
    return None
