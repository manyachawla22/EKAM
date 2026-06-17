from collections import defaultdict
from datetime import datetime, timezone
from statistics import mean, pstdev
from typing import Any
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import RobustScaler
from app.models.anomaly import Anomaly, AnomalyType, AnomalyReviewStatus
from app.models.event import Event, Round
from app.models.judge import Judge
from app.models.notification import NotificationType
from app.models.report import Report as ReportModel
from app.models.submission import Evaluation, Submission, SubmissionStatus
from app.core.config import settings
from app.services.email_service import send_direct_email
from app.services.notification_service import create_notification
# ── Tuning knobs ──────────────────────────────────────────────────────────────
# Need enough evaluation points before ML is meaningful
_MIN_POINTS_FOR_ML = 6
# Fallback thresholds when data is too small for IsolationForest
_PANEL_SPREAD_THRESHOLD = 35.0
_PANEL_DEVIATION_THRESHOLD = 30.0
# Post-ML filters to reduce noisy anomaly flags
_MIN_ABS_RESIDUAL_FROM_PANEL = 20.0
_MIN_PANEL_STD_FOR_FLAG = 5.0
# Safer default contamination
_DEFAULT_CONTAMINATION = 0.05
# ── Helpers ───────────────────────────────────────────────────────────────────
def _evaluation_score(evaluation: Evaluation) -> float | None:
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
def _uuid_str(value: Any) -> str:
    return str(value)
# ── Data loading ──────────────────────────────────────────────────────────────
async def _load_event_evaluation_points(
    db: AsyncSession,
    event_id: UUID | str,
) -> list[dict]:
    stmt = (
        select(Evaluation, Submission, Round)
        .join(Submission, Evaluation.submission_id == Submission.id)
        .join(Round, Submission.round_id == Round.id)
        .where(Round.event_id == event_id)
    )
    rows = (await db.execute(stmt)).all()
    points: list[dict] = []
    for evaluation, submission, round_obj in rows:
        score = _evaluation_score(evaluation)
        if score is None:
            continue
        points.append(
            {
                "evaluation": evaluation,
                "submission": submission,
                "round": round_obj,
                "score": score,
            }
        )
    return points
# ── Feature engineering ───────────────────────────────────────────────────────
def _build_ml_features(points: list[dict]) -> tuple[list[list[float]], list[dict]]:
    scores_by_submission: dict[Any, list[float]] = defaultdict(list)
    scores_by_judge: dict[Any, list[float]] = defaultdict(list)
    for point in points:
        evaluation = point["evaluation"]
        submission = point["submission"]
        score = point["score"]
        scores_by_submission[submission.id].append(score)
        scores_by_judge[evaluation.judge_id].append(score)
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
                "global_average": float(global_average),
                "residual_from_panel": float(residual_from_panel),
                "residual_from_judge_mean": float(residual_from_judge_mean),
                "residual_from_global_mean": float(residual_from_global_mean),
                "submission_score_count": len(submission_scores),
                "judge_score_count": len(judge_scores),
            }
        )
    return feature_rows, feature_payloads
# ── ML model ──────────────────────────────────────────────────────────────────
def _run_isolation_forest(
    feature_rows: list[list[float]],
    contamination: float,
):
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
    return labels, decision_scores
# ── ML anomaly extraction with post-filtering ─────────────────────────────────
def _build_anomaly_payloads(
    points: list[dict],
    feature_payloads: list[dict],
    labels,
    decision_scores,
) -> list[dict]:
    anomalies: list[dict] = []
    for point, payload, label, decision_score in zip(
        points,
        feature_payloads,
        labels,
        decision_scores,
    ):
        if label != -1:
            continue
        # Post-filter to reduce noise
        if abs(payload["residual_from_panel"]) < _MIN_ABS_RESIDUAL_FROM_PANEL:
            continue
        if payload["panel_std"] < _MIN_PANEL_STD_FOR_FLAG:
            continue
        evaluation = point["evaluation"]
        submission = point["submission"]
        round_obj = point["round"]
        score = point["score"]
        anomalies.append(
            {
                "evaluation_id": _uuid_str(evaluation.id),
                "submission_id": _uuid_str(submission.id),
                "team_id": _uuid_str(submission.team_id),
                "round_id": _uuid_str(round_obj.id),
                "judge_id": _uuid_str(evaluation.judge_id),
                "score": float(score),
                "panel_average": payload["panel_average"],
                "panel_std": payload["panel_std"],
                "judge_average": payload["judge_average"],
                "judge_std": payload["judge_std"],
                "global_average": payload["global_average"],
                "residual_from_panel": payload["residual_from_panel"],
                "residual_from_judge_mean": payload["residual_from_judge_mean"],
                "residual_from_global_mean": payload["residual_from_global_mean"],
                "submission_score_count": payload["submission_score_count"],
                "judge_score_count": payload["judge_score_count"],
                "ml_anomaly_score": float(decision_score),
                "model_label": int(label),
                "model": "IsolationForest",
            }
        )
    return anomalies
# ── Small-data fallback ───────────────────────────────────────────────────────
def _fallback_panel_disagreement(points: list[dict]) -> list[dict]:
    scores_by_submission: dict[Any, list[dict]] = defaultdict(list)
    for point in points:
        submission = point["submission"]
        scores_by_submission[submission.id].append(point)
    anomalies: list[dict] = []
    for submission_id, submission_points in scores_by_submission.items():
        scores = [p["score"] for p in submission_points]
        if len(scores) < 2:
            continue
        panel_average = mean(scores)
        panel_std = _safe_std(scores)
        panel_spread = max(scores) - min(scores)
        if panel_spread < _PANEL_SPREAD_THRESHOLD:
            continue
        for point in submission_points:
            score = point["score"]
            residual = score - panel_average
            if abs(residual) < _PANEL_DEVIATION_THRESHOLD:
                continue
            evaluation = point["evaluation"]
            submission = point["submission"]
            round_obj = point["round"]
            anomalies.append(
                {
                    "evaluation_id": _uuid_str(evaluation.id),
                    "submission_id": _uuid_str(submission.id),
                    "team_id": _uuid_str(submission.team_id),
                    "round_id": _uuid_str(round_obj.id),
                    "judge_id": _uuid_str(evaluation.judge_id),
                    "score": float(score),
                    "panel_average": float(panel_average),
                    "panel_std": float(panel_std),
                    "judge_average": float(score),
                    "judge_std": 0.0,
                    "global_average": float(panel_average),
                    "residual_from_panel": float(residual),
                    "residual_from_judge_mean": 0.0,
                    "residual_from_global_mean": float(residual),
                    "submission_score_count": len(scores),
                    "judge_score_count": 1,
                    "ml_anomaly_score": -1.0,
                    "model_label": -1,
                    "model": "fallback_panel_disagreement",
                }
            )
    return anomalies
# ── Live anomaly creation ─────────────────────────────────────────────────────
async def _create_live_anomaly_notification(
    db: AsyncSession,
    event_id: UUID | str,
    evaluation: Evaluation,
    anomaly_payload: dict,
):
    severity = min(
        1.0,
        max(
            0.1,
            abs(float(anomaly_payload["residual_from_panel"])) / 100.0,
        ),
    )
    description = (
        "ML scoring anomaly detected. "
        f"Score {anomaly_payload['score']:.1f} was flagged. "
        f"Panel average: {anomaly_payload['panel_average']:.2f}. "
        f"Judge average: {anomaly_payload['judge_average']:.2f}."
    )
    anomaly = Anomaly(
        event_id=event_id,
        evaluation_id=evaluation.id,
        anomaly_type=AnomalyType.score_variance,
        severity=severity,
        description=description,
        review_status=AnomalyReviewStatus.pending.value,
    )
    db.add(anomaly)
    await db.flush()
    event = (
        await db.execute(select(Event).where(Event.id == event_id))
    ).scalars().first()
    judge = (
        await db.execute(select(Judge).where(Judge.id == evaluation.judge_id))
    ).scalars().first()
    await db.commit()
    await db.refresh(anomaly)
    try:
        from app.services.approval_service import create_approval_request
        from app.models.approval import RequestType
        judge_label = (judge.name or judge.email) if judge else "a judge"
        await create_approval_request(
            db=db,
            event_id=str(event_id),
            request_type=RequestType.anomaly_review,
            payload={
                "anomaly_id": str(anomaly.id),
                "event_id": str(event_id),
                "judge_id": str(evaluation.judge_id),
                "judge_name": judge_label,
                "judge_email": getattr(judge, "email", None) if judge else None,
                "description": description,
                "score": float(anomaly_payload["score"]),
                "panel_average": float(anomaly_payload["panel_average"]),
                "judge_average": float(anomaly_payload["judge_average"]),
                "severity": severity,
            },
            requested_by=str(event.organizer_id) if event and event.organizer_id else None,
        )
    except Exception as exc:
        print(f"[anomaly_service] raising anomaly approval failed: {exc}")
    return anomaly
# ── Judge/organizer dispatch ──────────────────────────────────────────────────
async def dispatch_anomaly_review(
    db: AsyncSession,
    anomaly_id: str,
    approved: bool,
) -> None:
    anomaly = (
        await db.execute(select(Anomaly).where(Anomaly.id == anomaly_id))
    ).scalars().first()
    if not anomaly:
        return
    event = (
        await db.execute(select(Event).where(Event.id == anomaly.event_id))
    ).scalars().first()
    evaluation = (
        await db.execute(select(Evaluation).where(Evaluation.id == anomaly.evaluation_id))
    ).scalars().first()
    judge = None
    if evaluation is not None:
        judge = (
            await db.execute(select(Judge).where(Judge.id == evaluation.judge_id))
        ).scalars().first()
    event_id = anomaly.event_id
    event_name = event.name if event else "your event"
    if not approved:
        anomaly.review_status = AnomalyReviewStatus.rejected.value
        anomaly.is_resolved = True
        anomaly.resolved_at = datetime.now(timezone.utc)
        await db.commit()
        try:
            from app.services.event_bus import safe_publish
            if event and event.organizer_id:
                await safe_publish(
                    [str(event.organizer_id)],
                    {"type": "anomaly", "event_id": str(event_id), "anomaly_id": str(anomaly.id)},
                )
        except Exception as exc:
            print(f"[anomaly_service] dismiss signal failed: {exc}")
        return anomaly.review_status == AnomalyReviewStatus.approved.value
    await db.commit()
    if event and event.organizer_id:
        organizer_link = (
            f"{settings.FRONTEND_URL.rstrip('/')}/organizer/events/{event_id}/anomalies"
        )
        from app.models.user import User
        organizer = (
            await db.execute(select(User).where(User.id == event.organizer_id))
        ).scalars().first()
        organizer_email = getattr(organizer, "email", None) if organizer else None
        if organizer_email:
            judge_label = (judge.name or judge.email) if judge else "a judge"
            o_subject = f"[EKAM] Scoring anomaly confirmed — {event_name}"
            o_text = (
                f"You approved an automated scoring anomaly flagged for "
                f"\"{event_name}\".\n\n"
                f"  Judge: {judge_label}\n"
                f"  {anomaly.description}\n\n"
                f"The judge has been asked to review and correct it.\n"
                f"Review all anomalies here:\n  {organizer_link}\n\n"
                f"Team EKAM"
            )
            o_html = (
                f"<p>You approved an automated scoring anomaly flagged for "
                f"<strong>{event_name}</strong>.</p>"
                f"<ul><li><strong>Judge:</strong> {judge_label}</li>"
                f"<li>{anomaly.description}</li></ul>"
                f"<p>The judge has been asked to review and correct it.</p>"
                f"<p><a href=\"{organizer_link}\">Review all anomalies</a></p>"
                f"<p>Team EKAM</p>"
            )
            await send_direct_email(
                to=organizer_email, subject=o_subject, body_html=o_html, body_text=o_text
            )
    if judge:
        judge_page = "/judge/anomalies"
        await create_notification(
            db=db,
            event_id=str(event_id),
            user_id=str(judge.id),
            title="Please review a flagged evaluation",
            message=(
                "One of your evaluations was flagged as a possible scoring "
                "anomaly and confirmed for review. Open your anomalies page to "
                "review and fix it."
            ),
            notification_type=NotificationType.action_required,
            action_link=judge_page,
        )
        if getattr(judge, "email", None):
            judge_name = judge.name or judge.email.split("@")[0]
            try:
                from app.services.magic_link_service import generate_magic_link
                review_link = await generate_magic_link(
                    db, str(judge.id), "judge", str(event_id), redirect_path=judge_page
                )
            except Exception as exc:
                print(f"[anomaly] judge magic link failed: {exc}")
                review_link = f"{settings.FRONTEND_URL.rstrip('/')}{judge_page}"
            subject = f"[EKAM] Scoring anomaly flagged — {event_name}"
            body_text = (
                f"Hello {judge_name},\n\n"
                f"Our automated scoring review flagged one of your evaluations "
                f"for \"{event_name}\" as a possible anomaly, and the organizer "
                f"asked you to review it.\n\n"
                f"  {anomaly.description}\n\n"
                f"This does not mean the score is wrong — open your anomalies "
                f"page (one-click login) to review and fix any flagged scores:\n\n"
                f"  {review_link}\n\n"
                f"Thank you,\nTeam EKAM"
            )
            body_html = (
                f"<p>Hello {judge_name},</p>"
                f"<p>Our automated scoring review flagged one of your evaluations "
                f"for <strong>{event_name}</strong> as a possible anomaly, and the "
                f"organizer asked you to review it.</p>"
                f"<p>{anomaly.description}</p>"
                f"<p>This does not mean the score is wrong — open your anomalies "
                f"page to review and fix any flagged scores:</p>"
                f"<p><a href=\"{review_link}\">Review my flagged evaluations</a></p>"
                f"<p>Thank you,<br/>Team EKAM</p>"
            )
            await send_direct_email(
                to=judge.email, subject=subject, body_html=body_html, body_text=body_text
            )
    try:
        from app.services.event_bus import safe_publish
        targets = []
        if event and event.organizer_id:
            targets.append(str(event.organizer_id))
        if judge:
            targets.append(str(judge.id))
        if targets:
            await safe_publish(
                targets,
                {"type": "anomaly", "event_id": str(event_id), "anomaly_id": str(anomaly.id)},
            )
    except Exception as exc:
        print(f"[anomaly_service] anomaly signal failed: {exc}")
# ── Event-level report ────────────────────────────────────────────────────────
async def _create_event_report(
    db: AsyncSession,
    event_id: UUID | str,
    points: list[dict],
    anomalies: list[dict],
    contamination: float,
):
    flagged_submission_ids = {
        anomaly["submission_id"]
        for anomaly in anomalies
    }
    scores_by_submission: dict[Any, list[float]] = defaultdict(list)
    submission_objects: dict[str, Submission] = {}
    for point in points:
        submission = point["submission"]
        score = point["score"]
        scores_by_submission[submission.id].append(score)
        submission_objects[_uuid_str(submission.id)] = submission
    for submission_id_str, submission in submission_objects.items():
        submission_scores = scores_by_submission[submission.id]
        panel_average = mean(submission_scores)
        if hasattr(submission, "panel_average"):
            submission.panel_average = float(panel_average)
        if hasattr(submission, "panel_avg"):
            submission.panel_avg = float(panel_average)
        if hasattr(submission, "final_score"):
            submission.final_score = float(panel_average)
        if hasattr(submission, "score"):
            submission.score = float(panel_average)
        if submission_id_str in flagged_submission_ids:
            submission.status = SubmissionStatus.flagged
        elif submission.status == SubmissionStatus.pending:
            submission.status = SubmissionStatus.reviewed
    all_scores = [point["score"] for point in points]
    report_data = {
        "model": "IsolationForest",
        "summary": {
            "total_evaluations": len(points),
            "flagged_evaluations": len(anomalies),
            "flagged_submissions": len(flagged_submission_ids),
            "contamination": contamination,
            "global_average_score": float(mean(all_scores)) if all_scores else 0.0,
        },
        "anomalies": anomalies,
    }
    report = ReportModel(
        event_id=event_id,
        title="Evaluation Anomaly Report",
        type="anomaly",
        data=report_data,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report
# ── Public function (keep compatibility) ──────────────────────────────────────
async def analyze_evaluation(
    db: AsyncSession,
    event_id: UUID | str,
    contamination: float = _DEFAULT_CONTAMINATION,
):
    contamination = _validate_contamination(contamination)
    points = await _load_event_evaluation_points(db, event_id)
    if not points:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No scored evaluations found for this event",
        )
    if len(points) < _MIN_POINTS_FOR_ML:
        anomalies = _fallback_panel_disagreement(points)
    else:
        feature_rows, feature_payloads = _build_ml_features(points)
        labels, decision_scores = _run_isolation_forest(feature_rows, contamination)
        anomalies = _build_anomaly_payloads(
            points,
            feature_payloads,
            labels,
            decision_scores,
        )
        # If ML returns nothing but there is still obvious disagreement,
        # fallback catches blatant edge cases.
        if not anomalies:
            fallback_anomalies = _fallback_panel_disagreement(points)
            anomalies.extend(fallback_anomalies)
    # Create anomaly records / approval requests
    for anomaly_payload in anomalies:
        evaluation = next(
            (
                point["evaluation"]
                for point in points
                if _uuid_str(point["evaluation"].id) == anomaly_payload["evaluation_id"]
            ),
            None,
        )
        if evaluation is None:
            continue
        existing = (
            await db.execute(
                select(Anomaly).where(Anomaly.evaluation_id == evaluation.id)
            )
        ).scalars().first()
        if existing:
            continue
        await _create_live_anomaly_notification(
            db=db,
            event_id=event_id,
            evaluation=evaluation,
            anomaly_payload=anomaly_payload,
        )
    report = await _create_event_report(
        db=db,
        event_id=event_id,
        points=points,
        anomalies=anomalies,
        contamination=contamination,
    )
    return report
