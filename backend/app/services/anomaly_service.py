"""
EKAM Anomaly Service

Analyzes evaluations to detect scoring anomalies or judge bias.
Creates a notification for the event organizer whenever an anomaly is flagged.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.submission import Evaluation
from app.models.anomaly import Anomaly, AnomalyType
from app.models.event import Event
from app.models.notification import NotificationType
from app.services.notification_service import create_notification


async def analyze_evaluation(db: AsyncSession, event_id: str, evaluation: Evaluation):
    """
    Checks if a newly submitted evaluation deviates significantly from the mean
    of other evaluations for the same submission.
    If it does, creates an Anomaly record and notifies the event organizer.
    """
    result = await db.execute(
        select(Evaluation).where(
            Evaluation.submission_id == evaluation.submission_id,
            Evaluation.id != evaluation.id,
        )
    )
    other_evals = result.scalars().all()

    if len(other_evals) < 1:
        return  # Not enough data to compare

    # Evaluation model uses total_score, not score
    other_scores = [e.total_score for e in other_evals]
    avg_score = sum(other_scores) / len(other_scores)
    variance = abs(evaluation.total_score - avg_score) / (avg_score if avg_score > 0 else 1)

    if variance > 0.3:
        anomaly = Anomaly(
            event_id=event_id,
            evaluation_id=evaluation.id,
            anomaly_type=AnomalyType.score_variance,
            severity=min(variance, 1.0),
            description=(
                f"Score of {evaluation.total_score:.1f} deviates from average "
                f"{avg_score:.2f} by {variance * 100:.1f}%."
            ),
        )
        db.add(anomaly)
        await db.flush()

        res_event = await db.execute(select(Event).where(Event.id == event_id))
        event = res_event.scalars().first()

        await db.commit()

        if event and event.organizer_id:
            await create_notification(
                db=db,
                event_id=str(event_id),
                user_id=str(event.organizer_id),
                title="Score Anomaly Detected",
                message=anomaly.description,
                notification_type=NotificationType.alert,  # enum has alert, not warning
            )
