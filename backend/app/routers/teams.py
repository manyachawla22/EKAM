from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.middleware.auth import require_role

from app.models.user import User, UserRole

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
    assign_judge_service
)

router = APIRouter(
    prefix="/judges",
    tags=["Judges"]
)


@router.post(
    "/create",
    response_model=Judge,
    status_code=status.HTTP_201_CREATED
)
async def create_judge(
    judge_in: JudgeCreate,
    current_user: User = Depends(
        require_role([UserRole.organizer, UserRole.admin])
    ),
    db: AsyncSession = Depends(get_db)
):
    return await create_judge_service(
        db,
        judge_in
    )


@router.post(
    "/assign",
    response_model=JudgeAssignment,
    status_code=status.HTTP_201_CREATED
)
async def assign_judge(
    assign_in: JudgeAssignmentCreate,
    current_user: User = Depends(
        require_role([UserRole.organizer, UserRole.admin])
    ),
    db: AsyncSession = Depends(get_db)
):
    return await assign_judge_service(
        db,
        assign_in
    )

from app.team_formation.optimizer import form_teams, compute_team_diversity_score
from app.models.participant import Participant

@router.get("/{event_id}", response_model=List[Judge])
async def list_judges(
    event_id: UUID,
    current_user: User = Depends(
        require_role([UserRole.organizer, UserRole.admin])
    ),
    db: AsyncSession = Depends(get_db)
):
    return await list_judges_service(
        db,
        event_id
    )
    # Fetch participants for the event
    result = await db.execute(select(Participant).where(Participant.event_id == event_id))
    participants = result.scalars().all()
    
    # Fake data if none
    if not participants:
        p_data = [
            {"id": "1", "skills": ["Backend", "ML"], "domain": "AI/ML", "experience_level": "Advanced", "institution": "A"},
            {"id": "2", "skills": ["Frontend"], "domain": "Web/App Dev", "experience_level": "Beginner", "institution": "A"},
            {"id": "3", "skills": ["Design"], "domain": "Web/App Dev", "experience_level": "Intermediate", "institution": "B"},
            {"id": "4", "skills": ["ML", "Research"], "domain": "AI/ML", "experience_level": "Advanced", "institution": "B"},
        ]
    else:
        p_data = [
            {
                "id": str(p.id),
                "skills": ["Backend", "Frontend"],  # Mocked skills since model doesn't have it
                "domain": "Web/App Dev",
                "experience_level": "Intermediate",
                "institution": "Unknown"
            } for p in participants
        ]
        
    try:
        teams, leftovers = form_teams(p_data, team_size=team_size)
        return {
            "success": True,
            "teams": teams,
            "leftovers": leftovers,
            "message": f"Successfully formed {len(teams)} teams"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

