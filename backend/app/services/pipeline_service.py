"""
EKAM Pipeline Service

Handles stage transitions and progression logic for teams.
Integrates with the Approval Workflow.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.approval import RequestType
from app.models.event import Event, EventStage, Round
from app.models.participant import Participant
from app.models.team import Team
from app.models.notification import NotificationType
from app.services.approval_service import create_approval_request
from app.services.leaderboard_service import generate_leaderboard_service
from app.services.notification_service import create_notification


async def propose_stage_transition(
    db: AsyncSession,
    event_id: str,
    requested_by: str,
    target_stage: str,
    cutoff_score: float,
    round_id: str | None = None,
):
    """
    Queries the leaderboard for the current (or specified) round, applies the
    cutoff_score, and creates an ApprovalRequest listing which teams advance and
    which are eliminated.
    """
    current_round = None

    if round_id:
        res = await db.execute(
            select(Round).where(Round.id == round_id, Round.event_id == event_id)
        )
        current_round = res.scalars().first()
    else:
        # Most recent round for the event
        res = await db.execute(
            select(Round)
            .where(Round.event_id == event_id)
            .order_by(Round.start_date.desc())
        )
        current_round = res.scalars().first()

    advancing_teams = []
    eliminated_teams = []

    if current_round:
        leaderboard = await generate_leaderboard_service(db, current_round.id)

        for submission in leaderboard:
            score = submission.final_score or 0.0
            res_team = await db.execute(select(Team).where(Team.id == submission.team_id))
            team = res_team.scalars().first()
            team_name = team.name if team else str(submission.team_id)

            entry = {
                "team_id": str(submission.team_id),
                "team_name": team_name,
                "score": score,
            }
            if score >= cutoff_score:
                advancing_teams.append(entry)
            else:
                eliminated_teams.append(entry)
    else:
        # No rounds yet — propose advancing every team (event pre-round)
        res = await db.execute(select(Team))
        all_teams = res.scalars().all()
        advancing_teams = [
            {"team_id": str(t.id), "team_name": t.name, "score": 0.0}
            for t in all_teams
        ]

    payload = {
        "event_id": event_id,
        "target_stage": target_stage,
        "round_id": str(current_round.id) if current_round else None,
        "cutoff_score": cutoff_score,
        "advancing_teams": advancing_teams,
        "eliminated_teams": eliminated_teams,
        "requested_by": requested_by,  # preserved for email trigger after approval
    }

    approval = await create_approval_request(
        db=db,
        event_id=event_id,
        request_type=RequestType.stage_transition,
        payload=payload,
        requested_by=requested_by,
    )

    return approval


async def execute_stage_transition(
    db: AsyncSession,
    payload: dict,
):
    """
    Executed by the Approval Service once a stage transition is approved.
    1. Updates the event stage.
    2. Sends in-app notifications to all participants.
    3. Drafts AI-written bulk emails via email_triggers (→ approval → SMTP).
    """
    event_id = payload.get("event_id")
    target_stage = payload.get("target_stage")
    requested_by = payload.get("requested_by", "system")

    if not event_id or not target_stage:
        return

    # 1. Update event stage
    new_stage_enum = None
    event = None
    try:
        res = await db.execute(select(Event).where(Event.id == event_id))
        event = res.scalars().first()

        if event:
            try:
                new_stage_enum = EventStage(target_stage)
                event.stage = new_stage_enum
            except ValueError:
                pass  # unknown stage string — skip enum update
            await db.commit()
    except Exception:
        await db.rollback()
        raise

    # 2. In-app notifications to all participants
    res_p = await db.execute(
        select(Participant).where(Participant.event_id == event_id)
    )
    participants = res_p.scalars().all()
    stage_label = target_stage.replace("_", " ").title()
    for p in participants:
        await create_notification(
            db=db,
            event_id=event_id,
            user_id=str(p.id),
            title="Stage Update",
            message=f"The event has advanced to the {stage_label} stage.",
            notification_type=NotificationType.info,
        )

    # 3. AI-draft bulk emails via email_triggers (fire-and-forget errors)
    if event and new_stage_enum:
        try:
            from app.email_triggers import trigger_stage_emails
            extra_data = {
                "advancing_teams": payload.get("advancing_teams", []),
            }
            await trigger_stage_emails(
                event=event,
                new_stage=new_stage_enum,
                db=db,
                requested_by=requested_by,
                extra_data=extra_data,
            )
        except Exception as exc:
            # Email drafting must never block the pipeline
            print(f"[pipeline_service] email trigger failed: {exc}")
