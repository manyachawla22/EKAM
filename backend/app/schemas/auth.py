from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.auth import (
    TokenType,
    OwnerType
)


# =========================================================
# REQUEST SCHEMAS
# =========================================================

class RequestAccess(BaseModel):
    email: EmailStr
    event_hash: str


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    event_hash: str
    otp: str


class MagicLoginRequest(BaseModel):
    token: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class FirebaseLoginRequest(BaseModel):
    # This is a dummy schema for documentation purposes; 
    # the actual token is passed in the Authorization header.
    pass


# =========================================================
# TOKEN RESPONSE
# =========================================================

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    actor_type: str
    event_id: str | None = None
    session_id: str | None = None


class LoginResponse(TokenResponse):
    """Extended response for the /auth/login endpoint — includes user profile fields."""
    name: str
    email: str
    role: str
    organization: str | None = None


# =========================================================
# ME RESPONSE
# =========================================================

from typing import Any, List

class MeResponse(BaseModel):
    id: str
    actor_type: str
    event_id: str | None = None
    profile: Any
    permissions: List[str]
    is_event_scoped: bool


# =========================================================
# AUTH TOKEN
# =========================================================

class AuthTokenBase(BaseModel):

    owner_id: UUID
    owner_type: OwnerType

    token_type: TokenType

    expires_at: datetime


class AuthTokenCreate(AuthTokenBase):

    token: str


class AuthTokenResponse(AuthTokenBase):

    id: UUID

    token: str

    is_used: bool

    created_at: datetime

    class Config:
        from_attributes = True


# =========================================================
# OTP
# =========================================================

class OTPCodeBase(BaseModel):

    owner_id: UUID
    owner_type: OwnerType

    expires_at: datetime


class OTPCodeCreate(OTPCodeBase):

    otp_code: str


class OTPCodeResponse(OTPCodeBase):

    id: UUID

    otp_code: str

    attempts: int

    verified: bool

    created_at: datetime

    class Config:
        from_attributes = True


# =========================================================
# SESSIONS
# =========================================================

class UserSessionBase(BaseModel):

    owner_id: UUID
    owner_type: OwnerType

    expires_at: datetime


class UserSessionCreate(UserSessionBase):

    jwt_id: str

    ip_address: str | None = None
    user_agent: str | None = None


class UserSessionResponse(UserSessionBase):

    id: UUID

    jwt_id: str

    ip_address: str | None
    user_agent: str | None

    is_active: bool

    created_at: datetime

    class Config:
        from_attributes = True