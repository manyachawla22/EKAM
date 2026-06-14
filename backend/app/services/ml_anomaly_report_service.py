"""
EKAM Anomaly Service

ML-based anomaly detection using IsolationForest.

Important:
- Public function name remains analyze_evaluation()
- This preserves compatibility with existing imports/calls
- The old simple math threshold logic is replaced by ML-based detection
"""

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


# When there are too few evaluations for IsolationForest to be meaningful we
# fall back to a simple panel-disagreement rule so blatant outliers (e.g. one
# judge gives 0, another gives 95) still get flagged.
_MIN_POINTS_FOR_ML = 4
_PANEL_SPREAD_THRESHOLD = 30.0   # max-min across a submission's scores
_PANEL_DEVIATION_THRESHOLD = 25.0  # |this score - panel average|


def _evaluation_score(evaluation: Evaluation) -> float | None:
    """
    Support both current and older branches.

    Current EKAM Evaluation model usually uses total_score.
    Some older branches used score.
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


def _uuid_str(value: Any) -> str:
    return str(value)


async def _load_event_evaluation_points(
    db: AsyncSession,
    event_id: UUID | str,
) -> list[dict]:
    """
    Load all scored evaluations for one event.

    This gives the ML model enough context to compare:
    - score against panel behavior
    - score against judge behavior
    - score against event-level behavior
    """
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


def _build_ml_features(points: list[dict]) -> tuple[list[list[float]], list[dict]]:
    """
    Build numeric features for IsolationForest.

    These are features only. The anomaly decision is made by IsolationForest,
    not by a manual threshold.
    """
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
            }
        )

    return feature_rows, feature_payloads


def _run_isolation_forest(
    feature_rows: list[list[float]],
    contamination: float,
):
    """
    Run the ML model.

    label = -1 means anomaly
    label = 1 means normal
    """
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
                "ml_anomaly_score": float(decision_score),
                "model_label": int(label),
                "model": "IsolationForest",
            }
        )

    return anomalies


async def _create_live_anomaly_notification(
    db: AsyncSession,
    event_id: UUID | str,
    evaluation: Evaluation,
    anomaly_payload: dict,
):
    """
    When analyze_evaluation() flags one evaluation, create the Anomaly record and
    raise an ORGANIZER APPROVAL (#2) — we deliberately do NOT email the judge or
    reveal it on their page yet. The organizer decides whether the anomaly is
    worth considering; only on approval does dispatch_anomaly_review() notify the
    judge + organizer and surface it. On rejection it's dismissed.
    """
    severity = min(
        1.0,
        max(
            0.1,
            abs(float(anomaly_payload["residual_from_panel"])) / 100.0,
        ),
    )

    description = (
        "ML scoring anomaly detected. "
        f"Score {anomaly_payload['score']:.1f} was flagged by IsolationForest. "
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

    # Raise the organizer approval. create_approval_request publishes the live
    # "approval" SSE signal, so the organizer's dashboard surfaces it instantly.
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


async def dispatch_anomaly_review(
    db: AsyncSession,
    anomaly_id: str,
    approved: bool,
) -> None:
    """Apply the organizer's decision on a flagged anomaly (#2).

    approved=True  → mark considered, email the organizer (report) + the judge
                     (with a one-click magic link to their fix-it page), drop an
                     in-app action for the judge, and push the live SSE signal so
                     the judge's page reveals it.
    approved=False → dismiss: mark rejected + resolved, send nothing, and push an
                     SSE signal to the organizer so the glow clears (#4).
    """
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

    # Rebuild the score context from the description's persisted numbers isn't
    # reliable, so re-derive what we can from the anomaly's own fields. The
    # description already carries the human-readable figures.

    if not approved:
        anomaly.review_status = AnomalyReviewStatus.rejected.value
        anomaly.is_resolved = True
        anomaly.resolved_at = datetime.now(timezone.utc)
        await db.commit()
        # Clear the organizer's glow live (#4): the dismissed anomaly is gone.
        try:
            from app.services.event_bus import safe_publish

            if event and event.organizer_id:
                await safe_publish(
                    [str(event.organizer_id)],
                    {"type": "anomaly", "event_id": str(event_id), "anomaly_id": str(anomaly.id)},
                )
        except Exception as exc:
            print(f"[anomaly_service] dismiss signal failed: {exc}")
        return

    anomaly.review_status = AnomalyReviewStatus.approved.value
    await db.commit()

    # Organizer report email — a proper write-up, not just an in-app ping.
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

    # Notify the judge (in-app + email with a magic link to their fix-it page).
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

    # Push the live "anomaly" signal so the judge's page reveals it and the
    # organizer's badge reflects the now-active anomaly (SSE). Best-effort.
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


async def _create_event_report(
    db: AsyncSession,
    event_id: UUID | str,
    points: list[dict],
    anomalies: list[dict],
    contamination: float,
):
    """
    Create an event-level anomaly report for reports.py.
    """
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
            "global_average": float(mean(all_scores)) if all_scores else 0.0,
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


def _panel_anomaly_payload(
    points: list[dict],
    evaluation: Evaluation,
) -> dict | None:
    """
    Lightweight, non-ML anomaly check for a single evaluation against the other
    scores on the SAME submission. Used when there aren't enough evaluations for
    IsolationForest. Returns an anomaly payload (same shape the notifier expects)
    or None.
    """
    target_score = _evaluation_score(evaluation)
    if target_score is None:
        return None

    submission_scores = [
        point["score"]
        for point in points
        if point["submission"].id == evaluation.submission_id
    ]

    # Need at least two judges on this submission to talk about disagreement.
    if len(submission_scores) < 2:
        return None

    panel_average = mean(submission_scores)
    spread = max(submission_scores) - min(submission_scores)
    residual_from_panel = target_score - panel_average

    judge_scores = [
        point["score"]
        for point in points
        if point["evaluation"].judge_id == evaluation.judge_id
    ]
    judge_average = mean(judge_scores) if judge_scores else target_score

    is_anomaly = (
        spread >= _PANEL_SPREAD_THRESHOLD
        or abs(residual_from_panel) >= _PANEL_DEVIATION_THRESHOLD
    )
    if not is_anomaly:
        return None

    return {
        "evaluation_id": _uuid_str(evaluation.id),
        "submission_id": _uuid_str(evaluation.submission_id),
        "judge_id": _uuid_str(evaluation.judge_id),
        "score": float(target_score),
        "panel_average": float(panel_average),
        "judge_average": float(judge_average),
        "residual_from_panel": float(residual_from_panel),
        "panel_spread": float(spread),
        "model": "panel_disagreement",
    }


async def analyze_evaluation(
    db: AsyncSession,
    event_id: UUID | str,
    evaluation: Evaluation | None = None,
    contamination: float = 0.1,
):
    """
    Main anomaly detection function.

    This keeps the old function name but replaces old math threshold detection
    with ML-based IsolationForest detection.

    Usage 1: existing evaluation flow
        await analyze_evaluation(db, event_id, evaluation)

        This checks whether that one evaluation is an ML anomaly.
        If yes, it creates an Anomaly record and notifies the organizer.
        It returns the Anomaly or None.

    Usage 2: reports.py
        await analyze_evaluation(db=db, event_id=event_id, contamination=0.1)

        This runs event-level ML anomaly detection and creates a Report.
        It returns the Report.
    """
    contamination = _validate_contamination(contamination)

    points = await _load_event_evaluation_points(
        db=db,
        event_id=event_id,
    )

    if not points:
        if evaluation is not None:
            return None

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evaluations found for the requested event",
        )

    if len(points) < _MIN_POINTS_FOR_ML:
        # Not enough data for IsolationForest.
        if evaluation is not None:
            # Live flow: still catch blatant panel disagreement on this
            # submission (e.g. 0 vs 95) using a simple statistical rule.
            panel_payload = _panel_anomaly_payload(points, evaluation)
            if panel_payload is not None:
                return await _create_live_anomaly_notification(
                    db=db,
                    event_id=event_id,
                    evaluation=evaluation,
                    anomaly_payload=panel_payload,
                )
            return None

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Need at least 4 scored evaluations for ML anomaly detection",
        )

    feature_rows, feature_payloads = _build_ml_features(points)

    labels, decision_scores = _run_isolation_forest(
        feature_rows=feature_rows,
        contamination=contamination,
    )

    anomalies = _build_anomaly_payloads(
        points=points,
        feature_payloads=feature_payloads,
        labels=labels,
        decision_scores=decision_scores,
    )

    # Existing live evaluation flow:
    # only react if the specific evaluation passed in was flagged by ML.
    if evaluation is not None:
        target_evaluation_id = _uuid_str(evaluation.id)

        for anomaly_payload in anomalies:
            if anomaly_payload["evaluation_id"] == target_evaluation_id:
                return await _create_live_anomaly_notification(
                    db=db,
                    event_id=event_id,
                    evaluation=evaluation,
                    anomaly_payload=anomaly_payload,
                )

        return None

    # Report flow:
    # no single evaluation was passed, so create event-level anomaly report.
    return await _create_event_report(
        db=db,
        event_id=event_id,
        points=points,
        anomalies=anomalies,
        contamination=contamination,
    )