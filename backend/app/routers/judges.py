"""
EKAM Judges Router
"""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.auth_context import AuthContext
from app.middleware.auth import require_actor_type, require_event_access
from app.core.config import settings

from app.models.judge import Judge as JudgeModel
from app.models.event import Event as EventModel

from app.schemas.judge import (
    Judge,
    JudgeCreate,
    JudgeAssignment,
    JudgeAssignmentCreate,
    JudgeAssignmentDetail,
    JudgeInviteDetail,
    JudgeInviteRespond,
)

from app.services.judge_service import (
    create_judge_service,
    list_judges_service,
    get_judge_assignments_detail,
)
from app.services.assignment_service import (
    assign_single_judge_service,
    propose_judge_assignment
)
from app.services.csv_service import parse_judge_csv, bulk_insert_judges
from app.services.email_service import send_judge_invite_email

router = APIRouter(
    prefix="/judges",
    tags=["Judges"]
)


# ─── Invite endpoints (no auth — judge hasn't logged in yet) ─────────────────
# These must be declared BEFORE the /{event_id} routes so FastAPI doesn't try
# to parse "invite" as a UUID.

@router.get(
    "/invite/{token}",
    response_model=JudgeInviteDetail,
)
async def get_invite_details(
    token: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return invite metadata so the frontend can show the accept/decline page."""
    result = await db.execute(
        select(JudgeModel).where(JudgeModel.invite_token == token)
    )
    judge = result.scalars().first()
    if not judge:
        raise HTTPException(status_code=404, detail="Invite link is invalid or has expired.")

    event_result = await db.execute(
        select(EventModel).where(EventModel.id == judge.event_id)
    )
    event = event_result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    return JudgeInviteDetail(
        judge_name=judge.name,
        judge_email=judge.email,
        event_name=event.name,
        event_hash=event.hash,
        invite_status=judge.invite_status,
    )


@router.post(
    "/invite/respond",
    response_model=JudgeInviteDetail,
)
async def respond_to_invite(
    body: JudgeInviteRespond,
    db: AsyncSession = Depends(get_db),
):
    """Accept or decline a judge invitation."""
    result = await db.execute(
        select(JudgeModel).where(JudgeModel.invite_token == body.token)
    )
    judge = result.scalars().first()
    if not judge:
        raise HTTPException(status_code=404, detail="Invite link is invalid or has expired.")

    if judge.invite_status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"This invitation has already been {judge.invite_status}."
        )

    event_result = await db.execute(
        select(EventModel).where(EventModel.id == judge.event_id)
    )
    event = event_result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    judge.invite_status = "accepted" if body.accepted else "declined"
    if body.accepted:
        judge.is_verified = True
    await db.commit()
    await db.refresh(judge)

    return JudgeInviteDetail(
        judge_name=judge.name,
        judge_email=judge.email,
        event_name=event.name,
        event_hash=event.hash,
        invite_status=judge.invite_status,
    )


# ─── CSV bulk import ──────────────────────────────────────────────────────────

@router.post(
    "/{event_id}/upload-csv",
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def upload_judge_csv(
    event_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Bulk upload judges via CSV."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV"
        )

    content = await file.read()
    judges_data = parse_judge_csv(content)
    count = await bulk_insert_judges(db, event_id, judges_data)
    return {"message": f"Successfully imported {count} judges", "count": count}


# ─── Create single judge (organizer) ─────────────────────────────────────────

@router.post(
    "/create",
    response_model=Judge,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_actor_type(["organizer"]))]
)
async def create_judge(
    judge_in: JudgeCreate,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    """Register a single judge and send them an invite email."""
    if not auth.can_access_event(str(judge_in.event_id)):
        raise HTTPException(status_code=403, detail="No event access")

    judge = await create_judge_service(db, judge_in)

    # Fetch event for email context
    event_result = await db.execute(
        select(EventModel).where(EventModel.id == judge_in.event_id)
    )
    event = event_result.scalars().first()

    if event and judge.invite_token:
        invite_link = f"{settings.FRONTEND_URL}/judge/invite?token={judge.invite_token}"
        await send_judge_invite_email(
            email=judge.email,
            judge_name=judge.name,
            event_name=event.name,
            event_hash=event.hash,
            invite_link=invite_link,
        )

    return judge


# ─── Judge-specific: assignments by event ────────────────────────────────────

@router.get(
    "/{event_id}/{judge_id}/assignments",
    response_model=List[JudgeAssignmentDetail],
    dependencies=[
        Depends(require_actor_type(["organizer", "judge"])),
        Depends(require_event_access("event_id"))
    ]
)
async def get_judge_assignments(
    event_id: UUID,
    judge_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return a judge's team assignments enriched with submission/evaluation state."""
    return await get_judge_assignments_detail(db, event_id, judge_id)


# ─── Auto-assign ─────────────────────────────────────────────────────────────

@router.post(
    "/{event_id}/auto-assign",
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def auto_assign_judges(
    event_id: str,
    judges_per_team: int = 2,
    max_teams_per_judge: int = 5,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    """Trigger CP-SAT judge assignment and create a pending ApprovalRequest."""
    try:
        approval = await propose_judge_assignment(
            db=db,
            event_id=event_id,
            requested_by=auth.actor_id,
            judges_per_team=judges_per_team,
            max_teams_per_judge=max_teams_per_judge
        )
        return {"message": "CP-SAT assignment proposed.", "approval_id": str(approval.id)}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Judge assignment failed: {type(e).__name__}: {e}")


# ─── Manual assign ────────────────────────────────────────────────────────────

@router.post(
    "/assign",
    response_model=JudgeAssignment,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_actor_type(["organizer"]))]
)
async def assign_judge(
    assign_in: JudgeAssignmentCreate,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    """Manually assign a single judge to a team."""
    return await assign_single_judge_service(db, assign_in)


# ─── List judges ─────────────────────────────────────────────────────────────

@router.get(
    "/{event_id}",
    response_model=List[Judge],
    dependencies=[
        # Judges call this against every event to discover which ones they're
        # invited to (the dashboard matches by email). Participants are blocked.
        Depends(require_actor_type(["organizer", "judge"])),
        Depends(require_event_access("event_id"))
    ]
)
async def list_judges(
    event_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """List all judges for an event."""
    return await list_judges_service(db, event_id)


# ─── Delete judge ─────────────────────────────────────────────────────────────

@router.delete(
    "/{event_id}/{judge_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def delete_judge(
    event_id: UUID,
    judge_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Remove a judge from the event."""
    result = await db.execute(
        select(JudgeModel).where(
            JudgeModel.id == judge_id,
            JudgeModel.event_id == event_id
        )
    )
    judge = result.scalars().first()
    if not judge:
        raise HTTPException(status_code=404, detail="Judge not found")
    await db.delete(judge)
    await db.commit()


# ─── Get single judge ─────────────────────────────────────────────────────────

@router.get(
    "/{event_id}/{judge_id}",
    response_model=Judge,
    dependencies=[
        Depends(require_actor_type(["organizer", "judge"])),
        Depends(require_event_access("event_id"))
    ]
)
async def get_judge(
    event_id: UUID,
    judge_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific judge by ID."""
    result = await db.execute(
        select(JudgeModel).where(
            JudgeModel.id == judge_id,
            JudgeModel.event_id == event_id
        )
    )
    judge = result.scalars().first()
    if not judge:
        raise HTTPException(status_code=404, detail="Judge not found")
    return judge
