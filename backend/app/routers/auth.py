from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.core.security import verify_token
from app.middleware.auth import get_current_user
from app.models.user import User, UserRole
from app.schemas.user import User as UserSchema, UserCreate
from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None

router = APIRouter()

@router.post("/login", response_model=UserSchema)
async def login(
    request_data: Optional[LoginRequest] = None,
    token_data: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    """
    Login endpoint. 
    Verifies the Firebase token and returns the user from Postgres.
    If the user doesn't exist yet, it creates one.
    """
    uid = token_data.get("uid")
    email = token_data.get("email") or ""
    firebase_name = token_data.get("name") or token_data.get("display_name")
    
    # Check if user exists in db
    result = await db.execute(select(User).where(User.firebase_uid == uid))
    user = result.scalars().first()

    from datetime import datetime, timezone
    
    if not user:
        # Create new user
        role = request_data.role if request_data and request_data.role else "participant"
        name = request_data.name if request_data and request_data.name else (firebase_name or (email.split('@')[0] if email else "User"))
        
        user = User(
            firebase_uid=uid,
            email=email,
            name=name,
            role=UserRole(role),
            last_login=datetime.now(timezone.utc)
        )
        db.add(user)
    else:
        user.last_login = datetime.now(timezone.utc)
        
    await db.commit()
    await db.refresh(user)

    return user

@router.get("/me", response_model=UserSchema)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
