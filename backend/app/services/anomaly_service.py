"""
ML-based anomaly report service.

Detects suspicious judge scores using IsolationForest.
"""

from collections import defaultdict
from statistics import mean, pstdev
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import RobustScaler

from app.models.event import Round
from app.models.report import Report as ReportModel
from app.models.submission import Evaluation, Submission, SubmissionStatus


def _evaluation_score(evaluation: Evaluation) -> float | None:
    """
    Current EKAM Evaluation model uses total_score.
    Fallback to score only for old local branches.
    """
    raw_score = getattr(evaluation, "total_score", None)

    if raw_score is None:
        raw_score = getattr(evaluation, "score", None)

    if raw_score is None:
        return None

    return float(raw_score)


def _safe_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0

    return float(pstdev(values))


def _validate_contamination(contamination: float) -> float:
    if contamination <= 0 or contamination > 0.5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="contamination must be greater than 0 and less than or equal to 0.5",
        )

    return contamination


async def detect_score_anomalies_service(
    db: AsyncSession,
    event_id: UUID,
    contamination: float = 0.1,
):
    contamination = _validate_contamination(contamination)

    stmt = (
        select(Evaluation, Submission, Round)
        .join(Submission, Evaluation.submission_id == Submission.id)
        .join(Round, Submission.round_id == Round.id)
        .where(Round.event_id == event_id)
    )

    rows = (await db.execute(stmt)).all()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evaluations found for the requested event",
        )

    points: list[dict] = []
    scores_by_submission: dict[UUID, list[float]] = defaultdict(list)
    scores_by_judge: dict[UUID, list[float]] = defaultdict(list)
    submission_objects: dict[UUID, Submission] = {}

    for evaluation, submission, round_obj in rows:
        score = _evaluation_score(evaluation)

        if score is None:
            continue

        submission_objects[submission.id] = submission
        scores_by_submission[submission.id].append(score)
        scores_by_judge[evaluation.judge_id].append(score)

        points.append(
            {
                "evaluation": evaluation,
                "submission": submission,
                "round": round_obj,
                "score": score,
            }
        )

    if len(points) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Need at least 4 scored evaluations for ML anomaly detection",
        )

    all_scores = [point["score"] for point in points]
    global_average = mean(all_scores)

    feature_rows: list[list[float]] = []
    feature_payloads: list[dict] = []

    for point in points:
        evaluation = point["evaluation"]
        submission = point["submission"]
        score = point["score"]

        submission_scores = scores_by_submission[submission.id]
        judge_scores = scores_by_judge[evaluation.judge_id]

        panel_average = mean(submission_scores)
        panel_std = _safe_std(submission_scores)

        judge_average = mean(judge_scores)
        judge_std = _safe_std(judge_scores)

        residual_from_panel = score - panel_average
        residual_from_judge_mean = score - judge_average
        residual_from_global_mean = score - global_average

        feature_rows.append(
            [
                score,
                panel_average,
                panel_std,
                residual_from_panel,
                abs(residual_from_panel),
                judge_average,
                judge_std,
                residual_from_judge_mean,
                residual_from_global_mean,
            ]
        )

        feature_payloads.append(
            {
                "panel_average": float(panel_average),
                "panel_std": float(panel_std),
                "judge_average": float(judge_average),
                "judge_std": float(judge_std),
                "residual_from_panel": float(residual_from_panel),
                "residual_from_judge_mean": float(residual_from_judge_mean),
                "residual_from_global_mean": float(residual_from_global_mean),
            }
        )

    model = make_pipeline(
        RobustScaler(),
        IsolationForest(
            n_estimators=200,
            contamination=contamination,
            random_state=42,
        ),
    )

    model.fit(feature_rows)

    labels = model.predict(feature_rows)
    decision_scores = model.decision_function(feature_rows)

    anomalies: list[dict] = []
    flagged_submission_ids: set[UUID] = set()

    for point, payload, label, decision_score in zip(
        points,
        feature_payloads,
        labels,
        decision_scores,
    ):
        evaluation = point["evaluation"]
        submission = point["submission"]
        round_obj = point["round"]
        score = point["score"]

        if label != -1:
            continue

        flagged_submission_ids.add(submission.id)

        anomalies.append(
            {
                "evaluation_id": str(evaluation.id),
                "submission_id": str(submission.id),
                "team_id": str(submission.team_id),
                "round_id": str(round_obj.id),
                "judge_id": str(evaluation.judge_id),
                "score": float(score),
                "panel_average": payload["panel_average"],
                "panel_std": payload["panel_std"],
                "judge_average": payload["judge_average"],
                "judge_std": payload["judge_std"],
                "residual_from_panel": payload["residual_from_panel"],
                "residual_from_judge_mean": payload["residual_from_judge_mean"],
                "residual_from_global_mean": payload["residual_from_global_mean"],
                "ml_anomaly_score": float(decision_score),
                "model_label": int(label),
                "model": "IsolationForest",
            }
        )

    for submission_id, submission in submission_objects.items():
        panel_average = mean(scores_by_submission[submission_id])

        if hasattr(submission, "panel_average"):
            submission.panel_average = float(panel_average)

        if hasattr(submission, "final_score"):
            submission.final_score = float(panel_average)

        if submission_id in flagged_submission_ids:
            submission.status = SubmissionStatus.flagged
        elif submission.status == SubmissionStatus.pending:
            submission.status = SubmissionStatus.reviewed

    report_data = {
        "model": "IsolationForest",
        "feature_columns": [
            "score",
            "panel_average",
            "panel_std",
            "residual_from_panel",
            "absolute_residual_from_panel",
            "judge_average",
            "judge_std",
            "residual_from_judge_mean",
            "residual_from_global_mean",
        ],
        "anomalies": anomalies,
        "summary": {
            "total_evaluations": len(points),
            "flagged_evaluations": len(anomalies),
            "flagged_submissions": len(flagged_submission_ids),
            "contamination": contamination,
            "global_average": float(global_average),
        },
    }

    report = ReportModel(
        event_id=event_id,
        title="Judge scoring anomaly detection",
        type="anomaly",
        data=report_data,
    )

    db.add(report)
    await db.commit()
    await db.refresh(report)

    return report