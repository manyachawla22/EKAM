from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.user import User, UserRole


async def login_service(
    db: AsyncSession,
    token_data: dict
):
    uid = token_data.get("uid")

    email = token_data.get("email") or ""

    firebase_name = (
        token_data.get("name")
        or token_data.get("display_name")
    )

    result = await db.execute(
        select(User).where(
            User.firebase_uid == uid
        )
    )

    user = result.scalars().first()

    if not user:
        user = User(
            firebase_uid=uid,
            email=email,
            name=firebase_name or email.split("@")[0],
            role=UserRole.organizer,
            last_login=datetime.now(timezone.utc)
        )

        db.add(user)

    else:
        user.last_login = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(user)

    return user