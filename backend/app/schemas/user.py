from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.user import UserRole

class UserBase(BaseModel):
    email: EmailStr
    name: str
    organization: Optional[str] = None
    role: UserRole = UserRole.participant

class UserCreate(UserBase):
    firebase_uid: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    organization: Optional[str] = None
    role: Optional[UserRole] = None

class User(UserBase):
    id: UUID
    firebase_uid: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
