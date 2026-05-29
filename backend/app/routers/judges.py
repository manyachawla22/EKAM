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

from app.models.judge import Judge as JudgeModel

from app.schemas.judge import (
    Judge,
    JudgeCreate,
    JudgeAssignment,
    JudgeAssignmentCreate
)

from app.services.judge_service import (
    create_judge_service,
    list_judges_service
)
from app.services.assignment_service import (
    assign_single_judge_service,
    propose_judge_assignment
)
from app.services.csv_service import parse_judge_csv, bulk_insert_judges

router = APIRouter(
    prefix="/judges",
    tags=["Judges"]
)


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
    
    return {
        "message": f"Successfully imported {count} judges",
        "count": count
    }


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
    """Register a single judge manually."""
    if not auth.can_access_event(str(judge_in.event_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No event access"
        )
        
    return await create_judge_service(
        db,
        judge_in
    )


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
    """
    Trigger CP-SAT judge assignment.
    Creates a pending ApprovalRequest with the proposed assignments.
    """
    try:
        approval = await propose_judge_assignment(
            db=db,
            event_id=event_id,
            requested_by=auth.actor_id,
            judges_per_team=judges_per_team,
            max_teams_per_judge=max_teams_per_judge
        )
        return {
            "message": "CP-SAT assignment proposed.",
            "approval_id": str(approval.id)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
    return await assign_single_judge_service(
        db,
        assign_in
    )


@router.get(
    "/{event_id}",
    response_model=List[Judge],
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def list_judges(
    event_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """List all judges for an event."""
    return await list_judges_service(db, event_id)


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
