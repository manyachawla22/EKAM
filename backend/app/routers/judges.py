from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.middleware.auth import require_role

from app.models.user import User, UserRole
from app.models.judge import Judge, JudgeAssignment
from app.models.participant import Team
from app.models.theme import Theme

from app.schemas.judge import (
    JudgeAssignmentResponse,
    JudgeAssignmentCreate
)

from app.judge_assignment.optimizer import assign_judges

router = APIRouter()


@router.post(
    "/assign",
    response_model=JudgeAssignmentResponse,
    status_code=status.HTTP_201_CREATED
)
async def assign_judge(
    assign_in: JudgeAssignmentCreate,
    current_user: User = Depends(
        require_role([UserRole.organizer])
    ),
    db: AsyncSession = Depends(get_db)
):

    existing = await db.execute(
        select(JudgeAssignment).where(
            JudgeAssignment.judge_id == assign_in.judge_id,
            JudgeAssignment.team_id == assign_in.team_id,
            JudgeAssignment.round_id == assign_in.round_id
        )
    )

    if existing.scalars().first():

        raise HTTPException(
            status_code=400,
            detail="Judge already assigned to this team"
        )

    new_assign = JudgeAssignment(
        **assign_in.model_dump()
    )

    db.add(new_assign)

    await db.commit()

    await db.refresh(new_assign)

    return new_assign


@router.get(
    "/round/{round_id}",
    response_model=List[JudgeAssignmentResponse]
)
async def list_assignments_for_round(
    round_id: UUID,
    current_user: User = Depends(
        require_role([UserRole.organizer])
    ),
    db: AsyncSession = Depends(get_db)
):

    result = await db.execute(
        select(JudgeAssignment).where(
            JudgeAssignment.round_id == round_id
        )
    )

    return result.scalars().all()


@router.post("/auto-assign/{round_id}")
async def auto_assign_judges(
    round_id: UUID,
    judges_per_team: int = 2,
    current_user: User = Depends(
        require_role([UserRole.organizer])
    ),
    db: AsyncSession = Depends(get_db)
):

    # fetch judges

    judge_result = await db.execute(
        select(Judge)
    )

    judges = judge_result.scalars().all()

    if not judges:

        raise HTTPException(
            status_code=400,
            detail="No judges found"
        )

    # fetch teams

    team_result = await db.execute(
        select(Team)
    )

    teams = team_result.scalars().all()

    if not teams:

        raise HTTPException(
            status_code=400,
            detail="No teams found"
        )

    # prepare judge data

    judge_data = []

    for j in judges:

        judge_data.append({

            "id": str(j.id),

            "name": j.name,

            "expertise": j.expertise or [],

            "institution": j.institution,

            "rating": j.rating

        })

    # prepare team data

    team_data = []

    for t in teams:

        theme_name = None
        required_skills = []

        if getattr(t, "theme", None):

            theme_name = t.theme.name

            required_skills = (
                t.theme.required_skills or []
            )

        team_data.append({

            "id": str(t.id),

            "theme": theme_name,

            "required_skills": required_skills,

            "institution": getattr(
                t,
                "institution",
                None
            )

        })

    try:

        assignments = assign_judges(
            judges=judge_data,
            teams=team_data,
            judges_per_team=judges_per_team
        )

        created_assignments = []

        for assignment in assignments:

            db_assignment = JudgeAssignment(

                judge_id=assignment["judge_id"],

                team_id=assignment["team_id"],

                round_id=round_id

            )

            db.add(db_assignment)

            created_assignments.append({

                "judge_id": assignment["judge_id"],

                "team_id": assignment["team_id"]

            })

        await db.commit()

        return {

            "success": True,

            "assignments": created_assignments,

            "message":
                f"Successfully assigned judges to {len(team_data)} teams"

        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
