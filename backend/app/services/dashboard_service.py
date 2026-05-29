"""
EKAM Dashboard Service

Aggregates data for the different actor dashboards.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.models.event import Event, Round
from app.models.participant import Participant
from app.models.judge import Judge, JudgeAssignment
from app.models.team import Team, TeamMember
from app.models.submission import Submission, Evaluation


async def organizer_dashboard_service(
    db: AsyncSession,
    event_id: str
):
    """
    Returns aggregated metrics for the Organizer dashboard.
    """
    # Total Participants
    res = await db.execute(select(func.count(Participant.id)).where(Participant.event_id == event_id))
    total_participants = res.scalar() or 0

    # Total Judges
    res = await db.execute(select(func.count(Judge.id)).where(Judge.event_id == event_id))
    total_judges = res.scalar() or 0

    # Total Teams
    # Note: Depending on schema, teams might be tied to event via members. We'll simplify for now.
    res = await db.execute(select(func.count(Team.id))) 
    total_teams = res.scalar() or 0
    
    # Active Rounds
    res = await db.execute(select(Round).where(Round.event_id == event_id))
    rounds = res.scalars().all()
    
    return {
        "metrics": {
            "total_participants": total_participants,
            "total_judges": total_judges,
            "total_teams": total_teams
        },
        "rounds": [
            {"id": str(r.id), "name": r.name, "start_time": r.start_time, "end_time": r.end_time}
            for r in rounds
        ]
    }


async def participant_dashboard_service(
    db: AsyncSession,
    event_id: str,
    participant_id: str
):
    """
    Returns specific details for a Participant:
    - Their team details
    - Their team's submissions
    """
    # Get their team
    res = await db.execute(
        select(TeamMember).where(TeamMember.participant_id == participant_id)
    )
    team_member = res.scalars().first()
    
    team_data = None
    submissions_data = []
    
    if team_member:
        res_team = await db.execute(select(Team).where(Team.id == team_member.team_id))
        team = res_team.scalars().first()
        
        if team:
            team_data = {
                "id": str(team.id),
                "name": team.name,
                "theme_id": str(team.theme_id) if team.theme_id else None
            }
            
            # Submissions for this team
            res_sub = await db.execute(select(Submission).where(Submission.team_id == team.id))
            submissions = res_sub.scalars().all()
            submissions_data = [
                {
                    "id": str(s.id),
                    "round_id": str(s.round_id),
                    "status": s.status.value if hasattr(s, "status") else "submitted",
                    "submitted_at": s.submitted_at
                }
                for s in submissions
            ]
            
    return {
        "team": team_data,
        "submissions": submissions_data
    }


async def judge_dashboard_service(
    db: AsyncSession,
    event_id: str,
    judge_id: str
):
    """
    Returns specific details for a Judge:
    - Their assigned teams
    - Pending vs Completed evaluations
    """
    # Get assignments
    res = await db.execute(
        select(JudgeAssignment).where(JudgeAssignment.judge_id == judge_id)
    )
    assignments = res.scalars().all()
    
    assigned_teams = []
    evaluations_completed = 0
    
    for assign in assignments:
        assigned_teams.append(str(assign.team_id))
        
        # Check evaluations for this team by this judge
        # This requires joining Submission and Evaluation. We do a simplified check.
        res_evals = await db.execute(
            select(func.count(Evaluation.id)).where(Evaluation.judge_id == judge_id)
        )
        evals_count = res_evals.scalar() or 0
        evaluations_completed = evals_count # simplification for dashboard
        
    return {
        "assignments": {
            "total_assigned": len(assigned_teams),
            "evaluations_completed": evaluations_completed,
            "team_ids": assigned_teams
        }
    }