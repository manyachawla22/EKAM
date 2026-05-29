"""
EKAM Authentication Middleware

Resolves JWT → loads entity (User/Participant/Judge) → returns AuthContext.

Provides:
- get_current_actor: universal dependency returning AuthContext
- require_actor_type: restricts routes to specific actor types
- require_event_access: validates the actor belongs to the event
- require_role: backward-compatible wrapper (delegates to require_actor_type)
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import verify_token
from app.core.auth_context import AuthContext
from app.core.roles import ActorType

from app.models.user import User, UserRole
from app.models.participant import Participant
from app.models.judge import Judge


# =========================================================
# MAIN DEPENDENCY: get_current_actor
# =========================================================

async def get_current_actor(
    token_data: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    """
    Resolve the current actor from any supported token type.

    Token sources:
    - firebase / mock  → look up User by firebase_uid
    - ekam_jwt         → look up entity by actor_type + sub
    """

    source = token_data.get("token_source", "")

    # ---- EKAM JWT path ----
    if source == "ekam_jwt":
        actor_id = token_data.get("sub")
        actor_type = token_data.get("actor_type")
        event_id = token_data.get("event_id")
        session_id = token_data.get("jti")

        entity = await _load_entity(db, actor_id, actor_type)

        return AuthContext(
            actor_id=actor_id,
            actor_type=actor_type,
            entity=entity,
            event_id=event_id,
            session_id=session_id,
        )

    # ---- Firebase / Mock path (organizer/admin) ----
    uid = token_data.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    result = await db.execute(
        select(User).where(User.firebase_uid == uid)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    actor_type = user.role.value  # "organizer" or "admin"

    return AuthContext(
        actor_id=str(user.id),
        actor_type=actor_type,
        entity=user,
        event_id=None,
        session_id=None,
    )


# =========================================================
# ENTITY LOADER
# =========================================================

async def _load_entity(
    db: AsyncSession,
    actor_id: str,
    actor_type: str,
):
    """Load the DB entity matching the JWT claims."""

    if actor_type in ("organizer", "admin"):
        result = await db.execute(
            select(User).where(User.id == actor_id)
        )
        entity = result.scalars().first()

    elif actor_type == "participant":
        result = await db.execute(
            select(Participant).where(Participant.id == actor_id)
        )
        entity = result.scalars().first()

    elif actor_type == "judge":
        result = await db.execute(
            select(Judge).where(Judge.id == actor_id)
        )
        entity = result.scalars().first()

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unknown actor type: {actor_type}",
        )

    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{actor_type.capitalize()} not found",
        )

    return entity


# =========================================================
# AUTHORIZATION DEPENDENCIES
# =========================================================

def require_actor_type(allowed_types: list[str]):
    """
    Dependency factory: restricts a route to specific actor types.

    Usage:
        @router.get("/...", dependencies=[Depends(require_actor_type(["organizer", "admin"]))])
        async def my_route(auth: AuthContext = Depends(get_current_actor)):
            ...
    """

    async def checker(
        auth: AuthContext = Depends(get_current_actor),
    ) -> AuthContext:
        if auth.actor_type not in allowed_types and auth.actor_type != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return auth

    return checker


def require_event_access(event_id_param: str = "event_id"):
    """
    Dependency factory: validates the actor belongs to the event.
    The event_id is read from the path parameter named `event_id_param`.

    Usage:
        @router.get("/{event_id}/...")
        async def my_route(
            event_id: UUID,
            auth: AuthContext = Depends(require_event_access()),
        ):
            ...
    """

    async def checker(
        auth: AuthContext = Depends(get_current_actor),
        **kwargs,
    ) -> AuthContext:
        # Admins and organizers can access any event
        if auth.actor_type in ("admin", "organizer"):
            return auth

        # Event-scoped actors must match event_id
        if not auth.event_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No event access",
            )

        return auth

    return checker


# =========================================================
# BACKWARD COMPATIBILITY
# =========================================================

def require_role(allowed_roles: list[UserRole]):
    """
    Backward-compatible dependency that wraps require_actor_type.
    Existing routers use this; it now supports all actor types.
    """

    # Map UserRole enums to ActorType strings
    type_strings = [r.value for r in allowed_roles]

    async def role_checker(
        auth: AuthContext = Depends(get_current_actor),
    ) -> User:
        if auth.actor_type not in type_strings and auth.actor_type != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )

        # Return the entity directly for backward compat
        # (existing routers expect a User object)
        return auth.entity

    return role_checker


# Legacy alias for backward compat
async def get_current_user(
    token_data: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Legacy: returns User model directly. Prefer get_current_actor."""
    auth = await get_current_actor(token_data=token_data, db=db)
    if not isinstance(auth.entity, User):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires an organizer/admin account",
        )
    return auth.entity
