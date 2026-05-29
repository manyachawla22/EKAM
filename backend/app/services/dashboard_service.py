"""
EKAM Dashboard Service

Aggregates data for the different actor dashboards.

Key schema notes:
  - Submission has NO event_id column; derive via Submission.round_id → Round.event_id
  - Evaluation uses total_score, not score
  - Participant/Judge use institution, not organization
  - Team has event_id directly
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.models.event import Event, Round
from app.models.participant import Participant
from app.models.judge import Judge, JudgeAssignment
from app.models.team import Team, TeamMember
from app.models.submission import Submission, Evaluation
from app.models.approval import ApprovalRequest, ApprovalStatus
from app.models.anomaly import Anomaly
from app.models.notification import Notification


async def organizer_dashboard_service(
    db: AsyncSession,
    event_id: str,
):
    """Returns aggregated metrics for the Organizer dashboard."""

    # Participant count
    res = await db.execute(
        select(func.count(Participant.id)).where(Participant.event_id == event_id)
    )
    total_participants = res.scalar() or 0

    # Judge count
    res = await db.execute(
        select(func.count(Judge.id)).where(Judge.event_id == event_id)
    )
    total_judges = res.scalar() or 0

    # Team count — Team has event_id directly
    res = await db.execute(
        select(func.count(Team.id)).where(Team.event_id == event_id)
    )
    total_teams = res.scalar() or 0

    # Submission count — Submission has no event_id; derive via Round
    round_ids_res = await db.execute(
        select(Round.id).where(Round.event_id == event_id)
    )
    round_ids = [r[0] for r in round_ids_res.all()]

    total_submissions = 0
    if round_ids:
        res = await db.execute(
            select(func.count(Submission.id)).where(Submission.round_id.in_(round_ids))
        )
        total_submissions = res.scalar() or 0

    # Pending approvals (top 10)
    res = await db.execute(
        select(ApprovalRequest)
        .where(
            ApprovalRequest.event_id == event_id,
            ApprovalRequest.status == ApprovalStatus.pending,
        )
        .order_by(ApprovalRequest.requested_at.desc())
        .limit(10)
    )
    pending_approvals_raw = res.scalars().all()
    pending_approvals = [
        {
            "id": str(a.id),
            "request_type": a.request_type.value,
            "requested_by": str(a.requested_by),
            "requested_at": a.requested_at,
            "status": a.status.value,
        }
        for a in pending_approvals_raw
    ]

    # Recent open anomalies
    res = await db.execute(
        select(Anomaly)
        .where(Anomaly.event_id == event_id, Anomaly.is_resolved == False)
        .order_by(Anomaly.created_at.desc())
        .limit(5)
    )
    anomalies = [
        {
            "id": str(a.id),
            "anomaly_type": a.anomaly_type.value,
            "severity": a.severity,
            "description": a.description,
            "created_at": a.created_at,
        }
        for a in res.scalars().all()
    ]

    # Rounds with status
    res = await db.execute(select(Round).where(Round.event_id == event_id))
    rounds = [
        {
            "id": str(r.id),
            "name": r.name,
            "status": r.status.value if r.status else None,
            "start_date": r.start_date,
            "end_date": r.end_date,
        }
        for r in res.scalars().all()
    ]

    return {
        "stats": {
            "total_participants": total_participants,
            "total_judges": total_judges,
            "total_teams": total_teams,
            "total_submissions": total_submissions,
            "pending_approvals": len(pending_approvals),
        },
        "pending_approvals": pending_approvals,
        "anomalies": anomalies,
        "rounds": rounds,
    }


async def participant_dashboard_service(
    db: AsyncSession,
    event_id: str,
    participant_id: str,
):
    """Returns specific details for a Participant."""

    res = await db.execute(
        select(TeamMember).where(TeamMember.participant_id == participant_id)
    )
    team_member = res.scalars().first()

    team_data = None
    submissions_data = []
    progression_status = "pending"

    if team_member:
        res_team = await db.execute(select(Team).where(Team.id == team_member.team_id))
        team = res_team.scalars().first()

        if team:
            res_members = await db.execute(
                select(TeamMember).where(TeamMember.team_id == team.id)
            )
            team_data = {
                "id": str(team.id),
                "name": team.name,
                "theme_id": str(team.theme_id) if team.theme_id else None,
                "member_count": len(res_members.scalars().all()),
            }

            # Submissions for this team — scoped to event via Round
            round_ids_res = await db.execute(
                select(Round.id).where(Round.event_id == event_id)
            )
            round_ids = [r[0] for r in round_ids_res.all()]

            if round_ids:
                res_sub = await db.execute(
                    select(Submission)
                    .where(
                        Submission.team_id == team.id,
                        Submission.round_id.in_(round_ids),
                    )
                    .order_by(Submission.submitted_at.desc())
                )
                submissions_data = [
                    {
                        "id": str(s.id),
                        "round_id": str(s.round_id),
                        "final_score": s.final_score,
                        "submitted_at": s.submitted_at,
                    }
                    for s in res_sub.scalars().all()
                ]

    # Unread notifications for this participant
    res_notifs = await db.execute(
        select(Notification)
        .where(
            Notification.user_id == participant_id,
            Notification.is_read == False,
        )
        .order_by(Notification.created_at.desc())
        .limit(20)
    )
    notifications = [
        {
            "id": str(n.id),
            "title": n.title,
            "message": n.message,
            "type": n.type.value if n.type else "info",
            "created_at": n.created_at,
        }
        for n in res_notifs.scalars().all()
    ]

    return {
        "team": team_data,
        "submissions": submissions_data,
        "progression_status": progression_status,
        "notifications": notifications,
    }


async def judge_dashboard_service(
    db: AsyncSession,
    event_id: str,
    judge_id: str,
):
    """Returns specific details for a Judge."""

    res = await db.execute(
        select(JudgeAssignment).where(JudgeAssignment.judge_id == judge_id)
    )
    assignments = res.scalars().all()

    assigned_teams = []
    pending_evaluations = []
    completed_evaluations = []

    # Collect round_ids for this event to scope submissions
    round_ids_res = await db.execute(
        select(Round.id).where(Round.event_id == event_id)
    )
    round_ids = [r[0] for r in round_ids_res.all()]

    for assign in assignments:
        res_team = await db.execute(select(Team).where(Team.id == assign.team_id))
        team = res_team.scalars().first()
        if not team:
            continue

        # Latest submission from this team in this event (via round_ids)
        submission = None
        if round_ids:
            res_sub = await db.execute(
                select(Submission)
                .where(
                    Submission.team_id == assign.team_id,
                    Submission.round_id.in_(round_ids),
                )
                .order_by(Submission.submitted_at.desc())
                .limit(1)
            )
            submission = res_sub.scalars().first()

        team_entry = {
            "team_id": str(team.id),
            "team_name": team.name,
            "theme_id": str(team.theme_id) if team.theme_id else None,
            "submission_id": str(submission.id) if submission else None,
        }
        assigned_teams.append(team_entry)

        if submission:
            res_eval = await db.execute(
                select(Evaluation).where(
                    Evaluation.submission_id == submission.id,
                    Evaluation.judge_id == judge_id,
                )
            )
            eval_record = res_eval.scalars().first()

            if eval_record:
                completed_evaluations.append({
                    "submission_id": str(submission.id),
                    "team_name": team.name,
                    "score": eval_record.total_score,  # Evaluation uses total_score
                    "evaluated_at": eval_record.evaluated_at,
                })
            else:
                pending_evaluations.append({
                    "submission_id": str(submission.id),
                    "team_name": team.name,
                    "team_id": str(team.id),
                })

    # Unread notifications for this judge
    res_notifs = await db.execute(
        select(Notification)
        .where(
            Notification.user_id == judge_id,
            Notification.is_read == False,
        )
        .order_by(Notification.created_at.desc())
        .limit(20)
    )
    notifications = [
        {
            "id": str(n.id),
            "title": n.title,
            "message": n.message,
            "type": n.type.value if n.type else "info",
            "created_at": n.created_at,
        }
        for n in res_notifs.scalars().all()
    ]

    return {
        "assigned_teams": assigned_teams,
        "pending_evaluations": pending_evaluations,
        "completed_evaluations": completed_evaluations,
        "notifications": notifications,
        "summary": {
            "total_assigned": len(assigned_teams),
            "pending": len(pending_evaluations),
            "completed": len(completed_evaluations),
        },
    }
