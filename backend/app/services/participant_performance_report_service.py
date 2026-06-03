"""
Participant performance report service.

Builds participant/team/submission/evaluation statistics and generates
a personalized HTML report using Groq when GROQ_API_KEY is configured.
"""

from statistics import mean
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from groq import Groq
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import AuthContext
from app.core.config import get_settings
from app.models.event import Round
from app.models.participant import Participant
from app.models.report import Report as ReportModel
from app.models.submission import Evaluation, Submission, SubmissionStatus
from app.models.team import Team, TeamMember


def _enum_value(value: Any) -> str:
    if hasattr(value, "value"):
        return value.value

    return str(value)


def _evaluation_score(evaluation: Evaluation) -> float | None:
    raw_score = getattr(evaluation, "total_score", None)

    if raw_score is None:
        raw_score = getattr(evaluation, "score", None)

    if raw_score is None:
        return None

    return float(raw_score)


def _evaluation_feedback(evaluation: Evaluation) -> str | None:
    for field_name in ("feedback", "comments", "notes"):
        value = getattr(evaluation, field_name, None)

        if value:
            return str(value)

    return None


def _authorize_participant_report(
    participant: Participant,
    auth: AuthContext,
):
    if auth.actor_type in ("organizer", "admin"):
        return

    if auth.actor_type != "participant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    actor_id_matches = str(auth.actor_id) == str(participant.id)

    actor_email = getattr(auth.entity, "email", None)
    participant_email = getattr(participant, "email", None)

    email_matches = (
        actor_email is not None
        and participant_email is not None
        and actor_email.lower() == participant_email.lower()
    )

    if not actor_id_matches and not email_matches:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Participants can only access their own performance report",
        )


def _build_performance_context(
    participant: Participant,
    team: Team,
    team_member_count: int,
    event_id: UUID,
    round_scores: list[dict],
    statistics: dict,
) -> str:
    lines = [
        f"Participant: {participant.name}",
        f"Email: {participant.email}",
        f"Team: {team.name}",
        f"Team Size: {team_member_count}",
        f"Event ID: {event_id}",
        "",
        "Performance Summary:",
        f"- Rounds Participated: {statistics['rounds_participated']}",
        f"- Overall Average Score: {statistics['overall_average']:.1f}/100",
        f"- Best Score: {statistics['best_score']:.1f}/100",
        f"- Worst Score: {statistics['worst_score']:.1f}/100",
        f"- Total Evaluations: {statistics['total_evaluations']}",
        f"- Flagged Submissions: {statistics['flagged_submissions']}",
        f"- Progression: {statistics['progression']}",
        "",
        "Round-by-Round Performance:",
    ]

    for item in round_scores:
        score_display = (
            f"{item['score']:.1f}/100"
            if item["score"] is not None
            else "Not evaluated"
        )

        lines.append(
            f"- {item['round_name']} "
            f"(Round {item['round_index']}): "
            f"{score_display}, "
            f"Status: {item['status']}, "
            f"Judges: {item['judge_count']}"
        )

        for feedback in item["feedback"]:
            lines.append(f"  Feedback: {feedback}")

    return "\n".join(lines)


def _fallback_html_report(
    participant: Participant,
    team: Team,
    round_scores: list[dict],
    statistics: dict,
) -> str:
    round_rows = ""

    for item in round_scores:
        score = (
            f"{item['score']:.1f}"
            if item["score"] is not None
            else "Not evaluated"
        )

        round_rows += f"""
        <tr>
            <td>{item["round_index"]}</td>
            <td>{item["round_name"]}</td>
            <td>{score}</td>
            <td>{item["judge_count"]}</td>
            <td>{item["status"]}</td>
        </tr>
        """

    return f"""
    <div style="background:#0a0a0a;font-family:Inter,system-ui,-apple-system,'Segoe UI',Arial,sans-serif;max-width:900px;margin:0 auto;padding:24px;color:#f5f5f5;">
        <div style="background: linear-gradient(135deg, #e8503a, #d4432e); color: white; padding: 24px; border-radius: 16px;">
            <h1 style="margin: 0;">Performance Report</h1>
            <p style="margin: 8px 0 0 0;">{participant.name} · {team.name}</p>
        </div>

        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 24px 0;">
            <div style="padding: 16px; border: 1px solid #222222; border-radius: 12px; background:#111111;">
                <strong>Average</strong><br>{statistics["overall_average"]:.1f}
            </div>
            <div style="padding: 16px; border: 1px solid #222222; border-radius: 12px; background:#111111;">
                <strong>Best</strong><br>{statistics["best_score"]:.1f}
            </div>
            <div style="padding: 16px; border: 1px solid #222222; border-radius: 12px; background:#111111;">
                <strong>Rounds</strong><br>{statistics["rounds_participated"]}
            </div>
            <div style="padding: 16px; border: 1px solid #222222; border-radius: 12px; background:#111111;">
                <strong>Status</strong><br>{statistics["progression"]}
            </div>
        </div>

        <h2>Round Performance</h2>
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr>
                    <th style="text-align:left; border-bottom: 1px solid #222222; padding: 8px; color:#888888;">Round</th>
                    <th style="text-align:left; border-bottom: 1px solid #222222; padding: 8px; color:#888888;">Name</th>
                    <th style="text-align:left; border-bottom: 1px solid #222222; padding: 8px; color:#888888;">Score</th>
                    <th style="text-align:left; border-bottom: 1px solid #222222; padding: 8px; color:#888888;">Judges</th>
                    <th style="text-align:left; border-bottom: 1px solid #222222; padding: 8px; color:#888888;">Status</th>
                </tr>
            </thead>
            <tbody>{round_rows}</tbody>
        </table>

        <h2>Summary</h2>
        <p style="color:#aaaaaa;">
            Congratulations on your participation. This report summarizes your team's evaluated
            performance, round progression, and judging outcomes. Use the round-by-round details
            to identify where your team performed strongest and where future submissions can improve.
        </p>
        <p style="text-align:center;color:#555555;font-size:12px;margin-top:28px;">Generated by EKAM · Team EKAM</p>
    </div>
    """


def _generate_llm_html_report(
    performance_context: str,
    participant: Participant,
    team: Team,
    round_scores: list[dict],
    statistics: dict,
) -> str:
    settings = get_settings()
    groq_api_key = getattr(settings, "groq_api_key", None)

    if not groq_api_key:
        return _fallback_html_report(
            participant=participant,
            team=team,
            round_scores=round_scores,
            statistics=statistics,
        )

    model = getattr(settings, "groq_model", "llama-3.3-70b-versatile")

    client = Groq(api_key=groq_api_key)

    prompt = f"""
Generate a professional, encouraging participant performance report as HTML.

Requirements:
1. Congratulate the participant.
2. Highlight strengths based on scores and progression.
3. Mention constructive improvement areas.
4. Give specific recommendations for future hackathons or competitions.
5. Use a motivational tone.
6. Return only HTML with inline CSS.
7. Match the EKAM app theme: near-black background (#0a0a0a), card panels (#111111) with #222222 borders, white text (#ffffff) with muted gray (#888888), and a warm red-orange accent (#e8503a). Use the Inter/system-ui font. The outermost element must set background:#0a0a0a and color:#f5f5f5.
8. Do not invent scores or rounds.

Performance data:

{performance_context}
"""

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You generate concise, accurate, supportive event performance reports.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.3,
    )

    content = completion.choices[0].message.content

    if not content:
        return _fallback_html_report(
            participant=participant,
            team=team,
            round_scores=round_scores,
            statistics=statistics,
        )

    return content


async def generate_participant_performance_report_service(
    db: AsyncSession,
    event_id: UUID,
    participant_id: UUID,
    auth: AuthContext,
):
    participant_result = await db.execute(
        select(Participant).where(
            Participant.id == participant_id,
            Participant.event_id == event_id,
        )
    )
    participant = participant_result.scalars().first()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found for this event",
        )

    _authorize_participant_report(participant, auth)

    team_result = await db.execute(
        select(Team)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(
            TeamMember.participant_id == participant_id,
            Team.event_id == event_id,
        )
    )
    team = team_result.scalars().first()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant is not part of any team for this event",
        )

    team_members_result = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team.id)
    )
    team_members = team_members_result.scalars().all()

    submission_rows = (
        await db.execute(
            select(Submission, Round)
            .join(Round, Submission.round_id == Round.id)
            .where(
                Submission.team_id == team.id,
                Round.event_id == event_id,
            )
            .order_by(Round.created_at)
        )
    ).all()

    if not submission_rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No submissions found for participant team",
        )

    round_scores: list[dict] = []
    total_evaluations = 0
    flagged_submissions = 0

    for index, row in enumerate(submission_rows, start=1):
        submission, round_obj = row

        evaluations_result = await db.execute(
            select(Evaluation).where(Evaluation.submission_id == submission.id)
        )
        evaluations = evaluations_result.scalars().all()

        scores = [
            score
            for evaluation in evaluations
            if (score := _evaluation_score(evaluation)) is not None
        ]

        feedback = [
            item
            for evaluation in evaluations
            if (item := _evaluation_feedback(evaluation)) is not None
        ]

        average_score = mean(scores) if scores else None

        total_evaluations += len(scores)

        if submission.status == SubmissionStatus.flagged:
            flagged_submissions += 1

        round_scores.append(
            {
                "round_index": index,
                "round_id": str(round_obj.id),
                "round_name": round_obj.name,
                "submission_id": str(submission.id),
                "score": average_score,
                "judge_count": len(scores),
                "status": _enum_value(submission.status),
                "feedback": feedback,
            }
        )

    scored_rounds = [
        item["score"]
        for item in round_scores
        if item["score"] is not None
    ]

    overall_average = mean(scored_rounds) if scored_rounds else 0.0
    best_score = max(scored_rounds) if scored_rounds else 0.0
    worst_score = min(scored_rounds) if scored_rounds else 0.0

    progression = "advanced" if len(round_scores) > 1 else "participated"

    statistics = {
        "overall_average": float(overall_average),
        "best_score": float(best_score),
        "worst_score": float(worst_score),
        "rounds_participated": len(round_scores),
        "total_evaluations": total_evaluations,
        "flagged_submissions": flagged_submissions,
        "progression": progression,
    }

    performance_context = _build_performance_context(
        participant=participant,
        team=team,
        team_member_count=len(team_members),
        event_id=event_id,
        round_scores=round_scores,
        statistics=statistics,
    )

    report_html = _generate_llm_html_report(
        performance_context=performance_context,
        participant=participant,
        team=team,
        round_scores=round_scores,
        statistics=statistics,
    )

    report_data = {
        "participant_id": str(participant_id),
        "participant_name": participant.name,
        "participant_email": participant.email,
        "team_id": str(team.id),
        "team_name": team.name,
        "round_scores": round_scores,
        "statistics": statistics,
        "report_html": report_html,
    }

    report = ReportModel(
        event_id=event_id,
        title=f"Performance Report - {participant.name}",
        type="participant_performance",
        data=report_data,
    )

    db.add(report)
    await db.commit()
    await db.refresh(report)

    return {
        "report_id": str(report.id),
        "participant_name": participant.name,
        "team_name": team.name,
        "report_html": report_html,
        "statistics": statistics,
        "round_details": round_scores,
    }