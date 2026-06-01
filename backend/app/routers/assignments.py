"""
EKAM Assignments Router
"""

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    status
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.middleware.auth import require_actor_type
from app.core.auth_context import AuthContext

from app.services.assignment_service import (
    assign_single_judge_service,
    assign_team_member_service
)

from app.schemas.judge import (
    JudgeAssignmentCreate,
    JudgeAssignment
)

from app.schemas.team import (
    TeamMemberCreate,
    TeamMember
)

router = APIRouter(
    prefix="/assignments",
    tags=["Assignments"]
)


@router.post(
    "/judge",
    response_model=JudgeAssignment,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_actor_type(["organizer"]))]
)
async def assign_judge(
    assignment_in: JudgeAssignmentCreate,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    return await assign_single_judge_service(
        db,
        assignment_in
    )


@router.post(
    "/team-member",
    response_model=TeamMember,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_actor_type(["organizer"]))]
)
async def assign_team_member(
    member_in: TeamMemberCreate,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    return await assign_team_member_service(
        db,
        member_in
    )