"""
EKAM Auth Router

Handles all authentication endpoints.
"""

import traceback

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_firebase_only, verify_token
from app.middleware.auth import get_current_actor
from app.core.auth_context import AuthContext

from app.schemas.auth import (
    TokenResponse,
    LoginResponse,
    RequestAccess,
    VerifyOTPRequest,
    MagicLoginRequest,
    RefreshTokenRequest,
    MeResponse,
)

from app.services.auth_service import (
    login_service,
    login_with_profile_service,
    request_access_service,
    verify_otp_service,
    magic_login_service,
    refresh_service,
    logout_service,
    me_service,
)

from pydantic import BaseModel


class _LoginBody(BaseModel):
    name: str | None = None
    role: str | None = None


router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    body: _LoginBody | None = None,
    token_data: dict = Depends(verify_firebase_only),
    db: AsyncSession = Depends(get_db),
):
    """
    POST /auth/login — frontend-compatible login for any role.

    - Send the Firebase ID token as Authorization: Bearer <token>.
    - Optionally include { name, role } in the JSON body (used during signup
      to pick the user's role; allowed values: organizer, participant, judge).
    - Returns an EKAM JWT plus the user profile (name, email, role, ...).
    """
    try:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        display_name = body.name if body else None
        role = body.role if body else None

        return await login_with_profile_service(
            db=db,
            token_data=token_data,
            ip_address=ip_address,
            user_agent=user_agent,
            display_name=display_name,
            role=role,
        )
    except HTTPException:
        raise
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {type(exc).__name__}: {exc}",
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
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"firebase-login failed: {type(e).__name__}: {e}",
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