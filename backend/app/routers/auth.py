"""
EKAM Auth Router

Handles all authentication endpoints.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_firebase_only, verify_token
from app.middleware.auth import get_current_actor
from app.core.auth_context import AuthContext

from app.schemas.auth import (
    TokenResponse,
    RequestAccess,
    VerifyOTPRequest,
    MagicLoginRequest,
    RefreshTokenRequest,
    MeResponse,
)

from app.services.auth_service import (
    login_service,
    request_access_service,
    verify_otp_service,
    magic_login_service,
    refresh_service,
    logout_service,
    me_service,
)


router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


@router.post("/firebase-login", response_model=TokenResponse)
async def firebase_login(
    request: Request,
    token_data: dict = Depends(verify_firebase_only),
    db: AsyncSession = Depends(get_db)
):
    """
    Organizer / Admin login via Firebase ID token.
    The ID token must be sent in the Authorization header as Bearer token.
    This also creates a JWT session.
    """
    
    # 1. Sync Firebase user to local DB
    user = await login_service(db, token_data)
    
    # 2. Issue an EKAM session for them
    from app.services.jwt_service import create_session
    
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await create_session(
        db=db,
        owner_id=str(user.id),
        owner_type=user.role.value,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.post("/request-access")
async def request_access(
    data: RequestAccess,
    db: AsyncSession = Depends(get_db)
):
    """
    Participants & Judges request access (OTP + Magic Link).
    Email is sent to the user.
    """
    return await request_access_service(
        db=db,
        email=data.email,
        event_hash=data.event_hash
    )


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(
    data: VerifyOTPRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify OTP and issue a JWT session.
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await verify_otp_service(
        db=db,
        email=data.email,
        event_hash=data.event_hash,
        otp=data.otp,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.post("/magic-login", response_model=TokenResponse)
async def magic_login(
    data: MagicLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify Magic Link token and issue a JWT session.
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await magic_login_service(
        db=db,
        token=data.token,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh an active JWT session."""
    return await refresh_service(db, data.refresh_token)


@router.post("/logout")
async def logout(
    auth: AuthContext = Depends(get_current_actor),
    db: AsyncSession = Depends(get_db)
):
    """Revoke the current session."""
    return await logout_service(db, auth.session_id)


@router.get("/me", response_model=MeResponse)
async def get_me(
    auth: AuthContext = Depends(get_current_actor)
):
    """Return the profile for the currently authenticated actor."""
    return await me_service(auth)