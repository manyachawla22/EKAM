from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_token

from app.middleware.auth import get_current_user

from app.models.user import User

from app.schemas.user import User as UserSchema

from app.services.auth_service import login_service

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


@router.post("/login", response_model=UserSchema)
async def login(
    token_data: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    return await login_service(
        db=db,
        token_data=token_data
    )


@router.get("/me", response_model=UserSchema)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    return current_user