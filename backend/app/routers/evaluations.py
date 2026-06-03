"""
EKAM Evaluations Router
"""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db

from app.middleware.auth import require_actor_type
from app.core.auth_context import AuthContext

from app.models.judge import Judge
from app.models.submission import Submission
from app.models.event import Round
from app.models.user import User

from app.schemas.evaluation import (
    Evaluation,
    EvaluationCreate
)

from app.services.evaluation_service import (
    submit_evaluation_service,
    get_submission_evaluations_service
)
from app.services.assessment_guide_service import generate_assessment_guide

router = APIRouter(
    prefix="/evaluations",
    tags=["Evaluations"]
)


@router.post(
    "/submit",
    response_model=Evaluation,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_actor_type(["judge"]))],
)
async def submit_evaluation(
    evaluation_in: EvaluationCreate,
    auth: AuthContext = Depends(require_actor_type(["judge"])),
    db: AsyncSession = Depends(get_db),
):
    """Submit an evaluation for a submission.

    The Judge row is resolved server-side from the authenticated user's
    email + the submission's event_id, ignoring whatever judge_id the
    client might have sent. This avoids the FK-violation failure mode
    where the frontend mistakenly sends a User.id (different table).
    """

    # 1. Look up the submission to discover its event via round.
    sub_res = await db.execute(
        select(Submission).where(Submission.id == evaluation_in.submission_id)
    )
    submission = sub_res.scalars().first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    round_res = await db.execute(
        select(Round).where(Round.id == submission.round_id)
    )
    round_obj = round_res.scalars().first()
    if not round_obj:
        raise HTTPException(
            status_code=404, detail="Round for this submission is missing"
        )

    # 2. Resolve the email of the authenticated actor.
    user_email = getattr(auth.entity, "email", None)
    if not user_email:
        raise HTTPException(
            status_code=403, detail="Authenticated actor has no email"
        )

    # 3. Find a Judge row owned by this email for the submission's event.
    judge_res = await db.execute(
        select(Judge).where(
            Judge.event_id == round_obj.event_id,
            Judge.email == user_email,
        )
    )
    judge = judge_res.scalars().first()
    if not judge:
        raise HTTPException(
            status_code=403,
            detail=(
                "You are not invited as a judge for this event. "
                "Ask the organizer to add your email."
            ),
        )

    # 4. Substitute the authoritative Judge.id before persisting.
    evaluation_in_validated = evaluation_in.model_copy(
        update={"judge_id": judge.id}
    )

    try:
        return await submit_evaluation_service(db, evaluation_in_validated)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"submit_evaluation failed: {type(e).__name__}: {e}",
        )


@router.get(
    "/guide/{submission_id}",
    dependencies=[Depends(require_actor_type(["organizer", "judge"]))],
)
async def get_assessment_guide(
    submission_id: UUID,
    auth: AuthContext = Depends(require_actor_type(["organizer", "judge"])),
    db: AsyncSession = Depends(get_db),
):
    """A structured judging guide tailored to the submission's challenge and the
    round's rubric. Generated on demand (AI-assisted, with a rubric-based
    fallback)."""
    return await generate_assessment_guide(db, submission_id)


@router.get(
    "/{submission_id}",
    response_model=List[Evaluation],
    dependencies=[Depends(require_actor_type(["organizer", "judge"]))]
)
async def get_submission_evaluations(
    submission_id: UUID,
    auth: AuthContext = Depends(require_actor_type(["organizer", "judge"])),
    db: AsyncSession = Depends(get_db)
):
    return await get_submission_evaluations_service(
        db,
        submission_id
    )