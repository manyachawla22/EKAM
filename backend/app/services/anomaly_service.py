"""
EKAM Anomaly Service

Analyzes evaluations to detect scoring anomalies or judge bias.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.models.submission import Evaluation
from app.models.anomaly import Anomaly, AnomalyType


async def analyze_evaluation(db: AsyncSession, event_id: str, evaluation: Evaluation):
    """
    Checks if a newly submitted evaluation deviates significantly from the mean
    of other evaluations for the same submission.
    """
    
    # Get all other evaluations for this submission
    result = await db.execute(
        select(Evaluation).where(
            Evaluation.submission_id == evaluation.submission_id,
            Evaluation.id != evaluation.id
        )
    )
    other_evals = result.scalars().all()
    
    if len(other_evals) < 1:
        return # Not enough data to compare
        
    other_scores = [e.score for e in other_evals]
    avg_score = sum(other_scores) / len(other_scores)
    
    # If the new score is more than 30% off the average, flag it
    variance = abs(evaluation.score - avg_score) / (avg_score if avg_score > 0 else 1)
    
    if variance > 0.3:
        anomaly = Anomaly(
            event_id=event_id,
            evaluation_id=evaluation.id,
            anomaly_type=AnomalyType.score_variance,
            severity=min(variance, 1.0),
            description=f"Score of {evaluation.score} deviates from average {avg_score:.2f} by {variance*100:.1f}%."
        )
        db.add(anomaly)
        await db.commit()
