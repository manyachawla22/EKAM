from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    status
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.middleware.auth import require_role

from app.models.user import (
    User,
    UserRole
)

from app.services.assignment_service import (
    assign_judge_service,
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
    status_code=status.HTTP_201_CREATED
)
async def assign_judge(
    assignment_in: JudgeAssignmentCreate,
    current_user: User = Depends(
        require_role([
            UserRole.organizer,
            UserRole.admin
        ])
    ),
    db: AsyncSession = Depends(get_db)
):
    return await assign_judge_service(
        db,
        assignment_in
    )


@router.post(
    "/team-member",
    response_model=TeamMember,
    status_code=status.HTTP_201_CREATED
)
async def assign_team_member(
    member_in: TeamMemberCreate,
    current_user: User = Depends(
        require_role([
            UserRole.organizer,
            UserRole.admin
        ])
    ),
    db: AsyncSession = Depends(get_db)
):
    return await assign_team_member_service(
        db,
        member_in
    )