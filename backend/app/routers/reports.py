from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from uuid import UUID
from statistics import mean

from sklearn.ensemble import IsolationForest

from app.core.database import get_db
from app.middleware.auth import require_role
from app.models.user import User, UserRole
from app.models.report import Report
from app.models.submission import Evaluation, Submission, SubmissionStatus
from app.models.event import Round
from app.schemas.report import Report as ReportSchema, ReportCreate

router = APIRouter()

@router.post("/generate", response_model=ReportSchema, status_code=status.HTTP_201_CREATED)
async def generate_report(
    report_in: ReportCreate,
    current_user: User = Depends(require_role([UserRole.organizer])),
    db: AsyncSession = Depends(get_db)
):
    # In a real app, this would trigger background tasks to aggregate data
    new_report = Report(**report_in.model_dump())
    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)
    return new_report

@router.post(
    "/detect-anomalies/{event_id}",
    response_model=ReportSchema,
    status_code=status.HTTP_201_CREATED
)
async def detect_anomaly_scores(
    event_id: UUID,
    contamination: float = 0.1,
    current_user: User = Depends(require_role([UserRole.organizer, UserRole.judge])),
    db: AsyncSession = Depends(get_db)
):
    if contamination <= 0 or contamination >= 0.5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="contamination must be between 0 and 0.5")

    stmt = select(Evaluation, Submission).join(Submission, Evaluation.submission_id == Submission.id).join(
        Round, Submission.round_id == Round.id
    ).where(Round.event_id == event_id)

    rows = (await db.execute(stmt)).all()
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No evaluations found for the requested event")

    submission_scores: dict[UUID, list[float]] = {}
    evaluation_points: list[dict] = []
    submission_objects: dict[UUID, Submission] = {}

    for evaluation, submission in rows:
        submission_objects[submission.id] = submission
        submission_scores.setdefault(submission.id, []).append(evaluation.score)
        evaluation_points.append({
            "submission_id": submission.id,
            "team_id": submission.team_id,
            "judge_id": evaluation.judge_id,
            "score": evaluation.score,
        })

    submission_avg = {
        submission_id: mean(scores)
        for submission_id, scores in submission_scores.items()
    }

    features = [
        [point["score"] - submission_avg[point["submission_id"]]]
        for point in evaluation_points
    ]

    model = IsolationForest(contamination=contamination, random_state=42)
    outlier_labels = model.fit_predict(features)

    anomalies: list[dict] = []
    flagged_submissions: set[UUID] = set()

    for point, label in zip(evaluation_points, outlier_labels):
        if label == -1:
            anomalies.append({
                "submission_id": str(point["submission_id"]),
                "team_id": str(point["team_id"]),
                "judge_id": str(point["judge_id"]),
                "score": point["score"],
                "submission_avg": submission_avg[point["submission_id"]],
            })
            flagged_submissions.add(point["submission_id"])

    for submission_id, submission in submission_objects.items():
        submission.panel_avg = submission_avg[submission_id]
        submission.score = submission_avg[submission_id]
        if submission_id in flagged_submissions:
            submission.status = SubmissionStatus.flagged
        elif submission.status == SubmissionStatus.pending:
            submission.status = SubmissionStatus.reviewed

    report_data = {
        "anomalies": anomalies,
        "summary": {
            "total_evaluations": len(evaluation_points),
            "flagged_submissions": len(flagged_submissions),
            "contamination": contamination,
        },
    }

    new_report = Report(
        event_id=event_id,
        title="Judge scoring anomaly detection",
        type="anomaly",
        data=report_data,
    )
    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)
    return new_report

@router.get("/{event_id}", response_model=List[ReportSchema])
async def list_reports(
    event_id: UUID,
    current_user: User = Depends(require_role([UserRole.organizer])),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Report).where(Report.event_id == event_id))
    return result.scalars().all()
