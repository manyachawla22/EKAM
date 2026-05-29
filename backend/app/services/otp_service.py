"""
EKAM OTP Service

Generates, stores, and verifies one-time passwords.
Rate limited: max 5 attempts per OTP, 10-minute expiry.
"""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.auth import OTPCode, OwnerType


MAX_ATTEMPTS = 5
OTP_EXPIRY_MINUTES = 10


async def generate_and_store_otp(
    db: AsyncSession,
    owner_id: str,
    owner_type: str,
) -> str:
    """
    Generate a 6-digit OTP, store it in the DB, and return the OTP string.
    Invalidates any existing unexpired OTPs for the same owner.
    """

    # Invalidate previous unused OTPs for this owner
    result = await db.execute(
        select(OTPCode).where(
            OTPCode.owner_id == owner_id,
            OTPCode.owner_type == OwnerType(owner_type),
            OTPCode.verified == False,
        )
    )
    old_otps = result.scalars().all()
    for old in old_otps:
        old.verified = True  # mark as consumed so they can't be reused

    # Generate new OTP
    otp_code = str(secrets.randbelow(900000) + 100000)  # 6 digits

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

    otp_record = OTPCode(
        owner_id=owner_id,
        owner_type=OwnerType(owner_type),
        otp_code=otp_code,
        expires_at=expires_at,
        attempts=0,
        verified=False,
    )

    db.add(otp_record)
    await db.commit()

    return otp_code


async def verify_otp(
    db: AsyncSession,
    owner_id: str,
    owner_type: str,
    otp_code: str,
) -> bool:
    """
    Verify an OTP for the given owner.
    Returns True on success, raises HTTPException on failure.
    """

    result = await db.execute(
        select(OTPCode).where(
            OTPCode.owner_id == owner_id,
            OTPCode.owner_type == OwnerType(owner_type),
            OTPCode.verified == False,
        ).order_by(OTPCode.created_at.desc())
    )
    otp_record = result.scalars().first()

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending OTP found. Please request a new one.",
        )

    # Check expiry
    if otp_record.expires_at < datetime.now(timezone.utc):
        otp_record.verified = True  # consume it
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one.",
        )

    # Check attempts
    if otp_record.attempts >= MAX_ATTEMPTS:
        otp_record.verified = True
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Please request a new OTP.",
        )

    # Verify
    otp_record.attempts += 1

    if otp_record.otp_code != otp_code:
        await db.commit()
        remaining = MAX_ATTEMPTS - otp_record.attempts
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OTP. {remaining} attempts remaining.",
        )

    # Success
    otp_record.verified = True
    await db.commit()

    return True
