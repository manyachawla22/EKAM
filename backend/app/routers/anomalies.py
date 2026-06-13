"""
EKAM Anomalies Router
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.auth_context import AuthContext
from app.middleware.auth import require_actor_type, require_event_access

from app.models.anomaly import Anomaly
from app.models.event import Round
from app.models.judge import Judge
from app.models.submission import Evaluation, Submission
from app.models.team import Team

router = APIRouter(
    prefix="/anomalies",
    tags=["Anomalies"]
)


# =========================================================
# JUDGE-SCOPED: a judge's own anomalies + a private fix-it endpoint
# =========================================================
# NOTE on ownership: the "private page" requirement ("accessible only to him")
# is enforced HERE, server-side. We never trust a judge_id from the client — we
# resolve the Judge rows owned by the authenticated actor's EMAIL (a judge may be
# an OTP/magic-link Judge row or a Firebase User; matching by email covers both,
# exactly like the evaluations router) and only ever return / mutate anomalies
# whose underlying evaluation belongs to one of those Judge rows.


class ResolveMyAnomalyBody(BaseModel):
    rubric_scores: Dict[str, float]
    feedback: Optional[str] = None


async def _my_judge_ids(db: AsyncSession, auth: AuthContext) -> List:
    """Judge.id values owned by the authenticated actor's email (across events)."""
    email = getattr(auth.entity, "email", None)
    if not email:
        return []
    rows = (
        await db.execute(select(Judge.id).where(Judge.email == email))
    ).scalars().all()
    return list(rows)


@router.get("/mine", dependencies=[Depends(require_actor_type(["judge"]))])
async def list_my_anomalies(
    event_id: Optional[str] = None,
    auth: AuthContext = Depends(require_actor_type(["judge"])),
    db: AsyncSession = Depends(get_db),
):
    """Every anomaly attributed to the calling judge, enriched with enough
    context to fix it inline (team, round, the judge's own per-criterion scores,
    the rubric, panel average). Optionally filtered to a single event."""
    judge_ids = await _my_judge_ids(db, auth)
    if not judge_ids:
        return []

    stmt = (
        select(Anomaly, Evaluation, Submission, Round, Team)
        .join(Evaluation, Anomaly.evaluation_id == Evaluation.id)
        .join(Submission, Evaluation.submission_id == Submission.id)
        .join(Round, Submission.round_id == Round.id)
        .join(Team, Submission.team_id == Team.id, isouter=True)
        .where(Evaluation.judge_id.in_(judge_ids))
        .order_by(Anomaly.created_at.desc())
    )
    if event_id:
        stmt = stmt.where(Anomaly.event_id == event_id)

    rows = (await db.execute(stmt)).all()

    # Lazy import avoids a heavy import at module load.
    from app.services.rubric_service import list_criteria

    items = []
    for anomaly, evaluation, submission, round_obj, team in rows:
        criteria = await list_criteria(db, submission.round_id, seed_if_empty=False)
        saved = evaluation.rubric_scores or {}
        items.append(
            {
                "id": str(anomaly.id),
                "event_id": str(anomaly.event_id),
                "anomaly_type": anomaly.anomaly_type.value,
                "severity": anomaly.severity,
                "description": anomaly.description,
                "is_resolved": anomaly.is_resolved,
                "created_at": anomaly.created_at.isoformat() if anomaly.created_at else None,
                "submission_id": str(submission.id),
                "round_id": str(round_obj.id),
                "round_name": round_obj.name,
                "team_name": team.name if team else None,
                "my_total_score": evaluation.total_score,
                "panel_average": submission.panel_average,
                "rubric": [
                    {
                        "id": str(c.id),
                        "name": c.name,
                        "max_score": c.max_score,
                        "description": c.description,
                        "my_score": float(saved.get(str(c.id), 0) or 0),
                    }
                    for c in criteria
                ],
            }
        )
    return items


@router.post("/mine/{anomaly_id}/resolve", dependencies=[Depends(require_actor_type(["judge"]))])
async def resolve_my_anomaly(
    anomaly_id: str,
    body: ResolveMyAnomalyBody,
    auth: AuthContext = Depends(require_actor_type(["judge"])),
    db: AsyncSession = Depends(get_db),
):
    """A judge fixes one of THEIR OWN flagged evaluations by editing the rubric
    scores. Re-scores via the normal evaluation path (recomputes the panel
    average, re-runs anomaly detection, pushes the live leaderboard signal),
    marks this anomaly resolved, and notifies the organizer."""
    judge_ids = await _my_judge_ids(db, auth)

    anomaly = (
        await db.execute(select(Anomaly).where(Anomaly.id == anomaly_id))
    ).scalars().first()
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    evaluation = (
        await db.execute(select(Evaluation).where(Evaluation.id == anomaly.evaluation_id))
    ).scalars().first()
    # Ownership gate: the anomaly's evaluation must belong to THIS judge.
    if not evaluation or evaluation.judge_id not in judge_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This anomaly does not belong to you.",
        )

    # Re-score through the standard evaluation service so all the existing side
    # effects (panel-average recompute, anomaly re-analysis, leaderboard SSE,
    # auto-propose) run exactly as they do for a normal submission.
    from app.schemas.submission import EvaluationCreate
    from app.services.evaluation_service import submit_evaluation_service

    fallback_total = float(sum(v for v in body.rubric_scores.values()))
    await submit_evaluation_service(
        db,
        EvaluationCreate(
            submission_id=evaluation.submission_id,
            judge_id=evaluation.judge_id,
            total_score=fallback_total,
            rubric_scores=body.rubric_scores,
            feedback=body.feedback,
        ),
    )

    # Mark this anomaly resolved. resolved_by is a FK to users.id, but a judge is
    # a Judge row (or User) — leave it null for judge-driven resolution to avoid
    # an FK violation; resolved_at records that it was actioned.
    anomaly.is_resolved = True
    anomaly.resolved_at = datetime.now(timezone.utc)
    await db.commit()

    # Tell the organizer a judge corrected a flagged score (in-app + SSE).
    try:
        from app.models.event import Event
        from app.models.notification import NotificationType
        from app.services.notification_service import create_notification

        event = (
            await db.execute(select(Event).where(Event.id == anomaly.event_id))
        ).scalars().first()
        if event and event.organizer_id:
            judge_name = getattr(auth.entity, "name", None) or "A judge"
            await create_notification(
                db=db,
                event_id=str(anomaly.event_id),
                user_id=str(event.organizer_id),
                title="Anomaly corrected by judge",
                message=f"{judge_name} reviewed and updated a flagged evaluation.",
                notification_type=NotificationType.info,
            )
    except Exception as exc:
        print(f"[anomalies] organizer notify on resolve failed: {exc}")

    return {"message": "Anomaly resolved", "anomaly_id": str(anomaly.id)}

@router.get(
    "/{event_id}",
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def list_anomalies(
    event_id: str,
    db: AsyncSession = Depends(get_db)
):
    """List all anomalies detected for an event."""
    result = await db.execute(
        select(Anomaly).where(Anomaly.event_id == event_id).order_by(Anomaly.created_at.desc())
    )
    return result.scalars().all()


@router.post(
    "/{event_id}/{anomaly_id}/resolve",
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def resolve_anomaly(
    event_id: str,
    anomaly_id: str,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    """Mark an anomaly as resolved."""
    from datetime import datetime, timezone
    
    result = await db.execute(
        select(Anomaly).where(Anomaly.id == anomaly_id, Anomaly.event_id == event_id)
    )
    anomaly = result.scalars().first()
    
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
        
    anomaly.is_resolved = True
    anomaly.resolved_by = auth.actor_id
    anomaly.resolved_at = datetime.now(timezone.utc)
    
    await db.commit()
    return {"message": "Anomaly resolved"}
