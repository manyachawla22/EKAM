import secrets

from datetime import (
    datetime,
    timedelta,
    timezone
)


async def generate_otp():
    return str(secrets.randbelow(900000) + 100000)


async def generate_otp_expiry():
    return datetime.now(
        timezone.utc
    ) + timedelta(minutes=10)


async def send_otp_email(
    email: str,
    otp: str
):
    print("=" * 50)
    print("OTP EMAIL")
    print(f"TO: {email}")
    print(f"OTP: {otp}")
    print("=" * 50)


async def send_invitation_email(
    email: str,
    role: str,
    event_name: str
):
    print("=" * 50)
    print("INVITATION EMAIL")
    print(f"TO: {email}")
    print(f"ROLE: {role}")
    print(f"EVENT: {event_name}")
    print("=" * 50)


async def send_stage_update_email(
    email: str,
    event_name: str,
    stage: str
):
    print("=" * 50)
    print("STAGE UPDATE EMAIL")
    print(f"TO: {email}")
    print(f"EVENT: {event_name}")
    print(f"NEW STAGE: {stage}")
    print("=" * 50)


async def send_selection_email(
    email: str,
    round_name: str
):
    print("=" * 50)
    print("SELECTION EMAIL")
    print(f"TO: {email}")
    print(f"QUALIFIED ROUND: {round_name}")
    print("=" * 50)