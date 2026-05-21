from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.middleware.auth import require_role
from app.models.user import User, UserRole
from app.models.judge import JudgeAssignment
from app.schemas.judge import JudgeAssignment as JudgeAssignmentSchema, JudgeAssignmentCreate

router = APIRouter()

@router.post("/assign", response_model=JudgeAssignmentSchema, status_code=status.HTTP_201_CREATED)
async def assign_judge(
    assign_in: JudgeAssignmentCreate,
    current_user: User = Depends(require_role([UserRole.organizer])),
    db: AsyncSession = Depends(get_db)
):
    new_assign = JudgeAssignment(**assign_in.model_dump())
    db.add(new_assign)
    await db.commit()
    await db.refresh(new_assign)
    return new_assign

from pydantic import BaseModel
import uuid
import secrets
from datetime import datetime, timedelta, timezone

class JudgeInviteRequest(BaseModel):
    email: str
    event_id: UUID
    name: str = "Judge"

@router.post("/invite-judge", status_code=status.HTTP_200_OK)
async def invite_judge(
    req: JudgeInviteRequest,
    current_user: User = Depends(require_role([UserRole.organizer])),
    db: AsyncSession = Depends(get_db)
):
    from app.core.config import settings
    
    # Check if user exists in DB
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalars().first()
    
    temp_password = secrets.token_urlsafe(8)
    firebase_uid = None
    
    if not settings.MOCK_AUTH:
        import firebase_admin.auth as firebase_auth
        try:
            fb_user = firebase_auth.get_user_by_email(req.email)
            firebase_uid = fb_user.uid
        except Exception:
            try:
                fb_user = firebase_auth.create_user(
                    email=req.email,
                    password=temp_password,
                    display_name=req.name
                )
                firebase_uid = fb_user.uid
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Firebase Error: {str(e)}")
    else:
        firebase_uid = f"mock_uid_{uuid.uuid4().hex[:8]}"

    if not user:
        user = User(
            firebase_uid=firebase_uid,
            email=req.email,
            name=req.name,
            role=UserRole.judge,
            invitation_token=secrets.token_urlsafe(32),
            invitation_expiry=datetime.now(timezone.utc) + timedelta(days=7)
        )
        db.add(user)
        await db.flush() # flush to get user.id for Judge model if needed
        
        # Create Judge profile
        from app.models.judge import Judge
        judge_profile = Judge(user_id=user.id)
        db.add(judge_profile)
        await db.flush()

    # Assign Judge to Event
    from app.models.judge import Judge
    result = await db.execute(select(Judge).where(Judge.user_id == user.id))
    judge_profile = result.scalars().first()
    
    if not judge_profile:
        judge_profile = Judge(user_id=user.id)
        db.add(judge_profile)
        await db.flush()

    assign_check = await db.execute(
        select(JudgeAssignment).where(
            JudgeAssignment.judge_id == judge_profile.id,
            JudgeAssignment.event_id == req.event_id
        )
    )
    if not assign_check.scalars().first():
        new_assign = JudgeAssignment(judge_id=judge_profile.id, event_id=req.event_id)
        db.add(new_assign)
        
    await db.commit()
    
    # Mock Email Service
    print("="*50)
    print("MOCK EMAIL SERVICE - JUDGE INVITATION")
    print(f"To: {req.email}")
    print(f"Subject: You have been invited to judge an event!")
    print(f"Body: Please login at /auth with Email: {req.email} and Password: {temp_password}")
    print("="*50)
    
    return {"message": "Judge invited successfully", "email": req.email}

@router.get("/{event_id}", response_model=List[JudgeAssignmentSchema])
async def list_judges_for_event(
    event_id: UUID,
    current_user: User = Depends(require_role([UserRole.organizer])),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(JudgeAssignment).where(JudgeAssignment.event_id == event_id))
    return result.scalars().all()
