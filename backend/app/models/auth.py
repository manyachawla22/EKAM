from uuid import uuid4
from datetime import datetime

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Integer,
    Enum
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import Mapped, mapped_column

import enum

from app.core.database import Base


# =========================================================
# ENUMS
# =========================================================

class OwnerType(str, enum.Enum):
    organizer = "organizer"
    admin = "admin"
    participant = "participant"
    judge = "judge"


class TokenType(str, enum.Enum):
    MAGIC_LINK = "MAGIC_LINK"
    OTP = "OTP"
    INVITATION = "INVITATION"
    PASSWORDLESS_LOGIN = "PASSWORDLESS_LOGIN"
    REFRESH_TOKEN = "REFRESH_TOKEN"


# =========================================================
# AUTH TOKENS
# =========================================================

class AuthToken(Base):

    __tablename__ = "auth_tokens"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    owner_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    owner_type: Mapped[OwnerType] = mapped_column(
        Enum(OwnerType),
        nullable=False
    )

    token: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
        index=True
    )

    token_type: Mapped[TokenType] = mapped_column(
        Enum(TokenType),
        nullable=False
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    is_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )


# =========================================================
# OTP CODES
# =========================================================

class OTPCode(Base):

    __tablename__ = "otp_codes"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    owner_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    owner_type: Mapped[OwnerType] = mapped_column(
        Enum(OwnerType),
        nullable=False
    )

    otp_code: Mapped[str] = mapped_column(
        # Stores a bcrypt hash of the OTP (~60 chars), not the 6-digit plaintext.
        String(255),
        nullable=False
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )


# =========================================================
# USER SESSIONS
# =========================================================

class UserSession(Base):

    __tablename__ = "user_sessions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    owner_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    owner_type: Mapped[OwnerType] = mapped_column(
        Enum(OwnerType),
        nullable=False
    )

    jwt_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
        index=True
    )

    ip_address: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    user_agent: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )