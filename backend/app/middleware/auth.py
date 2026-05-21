from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.core.security import verify_token
from app.models.user import User, UserRole

async def get_current_user(
    token_data: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    # token_data from verify_token will contain 'uid', 'email', 'role' for mock, 
    # or Firebase decoded token data.
    uid = token_data.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    # Check if user exists in db
    result = await db.execute(select(User).where(User.firebase_uid == uid))
    user = result.scalars().first()
    
    if not user:
        # For mock flow or first login, we might not have a user yet.
        # But this dependency requires the user to exist in Postgres.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user

def require_role(allowed_roles: list[UserRole]):
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles and current_user.role != UserRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker
