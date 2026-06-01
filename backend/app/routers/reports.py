from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from uuid import UUID
from statistics import mean
from groq import Groq

from sklearn.ensemble import IsolationForest

from app.core.database import get_db
from app.core.config import get_settings
from app.middleware.auth import require_role
from app.models.user import User, UserRole
from app.models.report import Report
from app.models.submission import Evaluation, Submission, SubmissionStatus
from app.models.event import Round
from app.models.participant import Participant, Team, TeamMember
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


@router.get("/participant/{event_id}/{participant_id}")
async def generate_participant_performance_report(
    event_id: UUID,
    participant_id: UUID,
    current_user: User = Depends(require_role([UserRole.participant, UserRole.organizer])),
    db: AsyncSession = Depends(get_db)
):
    """Generate a personalized performance report for a participant using LLM analysis."""
    
    # Verify participant exists and is in the event
    participant_stmt = select(Participant).where(
        (Participant.id == participant_id) & (Participant.event_id == event_id)
    )
    participant = (await db.execute(participant_stmt)).scalars().first()
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    
    # Get participant's user info
    user_stmt = select(User).where(User.id == participant.user_id)
    participant_user = (await db.execute(user_stmt)).scalars().first()
    
    # Get team members
    team_member_stmt = select(TeamMember).where(TeamMember.participant_id == participant_id)
    team_member = (await db.execute(team_member_stmt)).scalars().first()
    if not team_member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not part of any team")
    
    # Get team info
    team_stmt = select(Team).where(Team.id == team_member.team_id)
    team = (await db.execute(team_stmt)).scalars().first()
    
    # Get all team members
    all_members_stmt = select(TeamMember).where(TeamMember.team_id == team.id)
    team_members = (await db.execute(all_members_stmt)).scalars().all()
    
    # Get all submissions for this team
    submission_stmt = select(Submission, Round).join(
        Round, Submission.round_id == Round.id
    ).where(
        (Submission.team_id == team.id) & (Round.event_id == event_id)
    ).order_by(Round.round_number)
    
    rows = (await db.execute(submission_stmt)).all()
    
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No submissions found for team")
    
    # Gather performance metrics
    round_scores = []
    total_evaluations = 0
    flagged_count = 0
    
    for submission, round_obj in rows:
        # Get evaluations for this submission
        eval_stmt = select(Evaluation).where(Evaluation.submission_id == submission.id)
        evaluations = (await db.execute(eval_stmt)).scalars().all()
        
        if evaluations:
            scores = [e.score for e in evaluations]
            avg_score = mean(scores)
            
            round_scores.append({
                "round_number": round_obj.round_number,
                "round_name": round_obj.name,
                "score": avg_score,
                "judge_count": len(evaluations),
                "status": submission.status,
                "feedback": submission.feedback
            })
            
            total_evaluations += len(evaluations)
            if submission.status == SubmissionStatus.flagged:
                flagged_count += 1
    
    # Calculate overall statistics
    all_scores = [rs["score"] for rs in round_scores]
    overall_avg = mean(all_scores) if all_scores else 0
    best_score = max(all_scores) if all_scores else 0
    worst_score = min(all_scores) if all_scores else 0
    progression = "advanced" if len(round_scores) > 1 else "participated"
    
    # Build context for LLM
    performance_context = f"""
Participant: {participant_user.name}
Team: {team.name}
Team Size: {len(team_members)} members
Event: {event_id}

Performance Summary:
- Rounds Participated: {len(round_scores)}
- Overall Average Score: {overall_avg:.1f}/100
- Best Score: {best_score:.1f}
- Worst Score: {worst_score:.1f}
- Status: {progression.title()}
- Flagged Submissions: {flagged_count}
- Total Evaluations: {total_evaluations}

Round-by-Round Performance:
"""
    
    for rs in round_scores:
        performance_context += f"\n- {rs['round_name']} (Round {rs['round_number']}): {rs['score']:.1f}/100 (Status: {rs['status'].value})"
        if rs['feedback']:
            performance_context += f"\n  Feedback: {rs['feedback']}"
    
    # Call Groq to generate personalized report
    settings = get_settings()
    client = Groq(api_key=settings.groq_api_key)
    
    prompt = f"""Based on the following participant performance data, generate a professional and encouraging performance report. 
The report should:
1. Congratulate them on their participation
2. Highlight their strengths based on their scores and progression
3. Provide constructive feedback on areas for improvement
4. Give specific recommendations for future competitions
5. Be motivational and supportive in tone

{performance_context}

Format the response as a well-structured HTML report with inline CSS. Include:
- A professional header with the participant name
- Performance metrics in a clear format
- Round-by-round analysis
- Strengths and areas for improvement
- Future recommendations
- A motivational closing

Use a modern design with a color scheme of blues and greens. Include inline CSS styling."""
    
    message = client.messages.create(
        model="mixtral-8x7b-32768",
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    
    report_html = message.content[0].text
    
    # Store report in database
    report_data = {
        "participant_id": str(participant_id),
        "team_id": str(team.id),
        "round_scores": round_scores,
        "overall_avg": overall_avg,
        "best_score": best_score,
        "worst_score": worst_score,
        "progression": progression
    }
    
    new_report = Report(
        event_id=event_id,
        title=f"Performance Report - {participant_user.name}",
        type="participant_performance",
        data=report_data,
    )
    db.add(new_report)
    await db.commit()
    
    return {
        "participant_name": participant_user.name,
        "team_name": team.name,
        "report_html": report_html,
        "statistics": {
            "overall_average": overall_avg,
            "best_score": best_score,
            "worst_score": worst_score,
            "rounds_participated": len(round_scores),
            "total_evaluations": total_evaluations,
            "flagged_submissions": flagged_count,
            "progression": progression
        },
        "round_details": round_scores
    }
