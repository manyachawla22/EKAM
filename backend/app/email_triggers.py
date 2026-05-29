# backend/app/team_formation/email_triggers.py

from google import genai
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import json
import os

from app.models.email import EmailType
from app.models.event import Event, EventStage
from app.models.participant import Participant
from app.services.email_service import draft_bulk_emails

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


# ─── GEMINI CONTENT DRAFTING ──────────────────────────────────

def draft_email_content(email_type: str, context: dict) -> dict:
    prompt = f"""
You are EKAM, an autonomous event management system.
Draft a professional warm email for the following situation.

Email type: {email_type}
Context: {json.dumps(context, indent=2)}

Return ONLY valid JSON, no markdown, no backticks:
{{
    "subject": "...",
    "body_text": "plain text version",
    "body_html": "<p>html version</p>"
}}

Rules:
- Use actual names from context, never write [Name] or placeholders
- Be concise and warm
- Sign off as Team EKAM
"""
    response = client.models.generate_content(
        model="gemini-1.5-flash-latest",
        contents=prompt
    )
    raw = response.text.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])


# ─── STAGE TRIGGERS ───────────────────────────────────────────

async def on_registration_open(
    event: Event,
    db: AsyncSession,
    requested_by: str
):
    result = await db.execute(
        select(Participant).where(
            Participant.event_id == event.id,
            Participant.status == "confirmed"
        )
    )
    participants = result.scalars().all()
    if not participants:
        return

    # draft one email per participant with their name
    # but use bulk for approval gate
    context = {
        "event_name": event.name,
        "event_description": event.description,
        "event_type": event.type,
    }
    content = draft_email_content("welcome", context)

    recipients = [p.email for p in participants]
    await draft_bulk_emails(
        db=db,
        event_id=str(event.id),
        requested_by=requested_by,
        email_type=EmailType.invitation,
        subject=content["subject"],
        body_html=content["body_html"],
        body_text=content["body_text"],
        recipients=recipients
    )
    print(f"✓ Welcome email batch drafted for {len(recipients)} participants")


async def on_teams_formed(
    event: Event,
    teams: list,
    db: AsyncSession,
    requested_by: str
):
    for team in teams:
        teammates_summary = ", ".join(
            f"{m['name']} ({m['institution']})"
            for m in team["members"]
        )
        context = {
            "event_name": event.name,
            "team_name": team["name"],
            "teammates": teammates_summary,
            "rationale": team.get("rationale", ""),
        }
        content = draft_email_content("team_assignment", context)
        recipients = [m["email"] for m in team["members"]]

        await draft_bulk_emails(
            db=db,
            event_id=str(event.id),
            requested_by=requested_by,
            email_type=EmailType.team_assignment,
            subject=content["subject"],
            body_html=content["body_html"],
            body_text=content["body_text"],
            recipients=recipients
        )
        print(f"✓ Team assignment batch drafted for {team['name']}")


async def on_submission_stage(
    event: Event,
    db: AsyncSession,
    requested_by: str
):
    result = await db.execute(
        select(Participant).where(
            Participant.event_id == event.id,
            Participant.status == "confirmed"
        )
    )
    participants = result.scalars().all()
    if not participants:
        return

    context = {
        "event_name": event.name,
        "stage": "submission",
        "message": "The submission phase has now begun. Please submit your project before the deadline."
    }
    content = draft_email_content("stage_update", context)
    recipients = [p.email for p in participants]

    await draft_bulk_emails(
        db=db,
        event_id=str(event.id),
        requested_by=requested_by,
        email_type=EmailType.stage_update,
        subject=content["subject"],
        body_html=content["body_html"],
        body_text=content["body_text"],
        recipients=recipients
    )
    print(f"✓ Submission stage email batch drafted")


async def on_evaluation_stage(
    event: Event,
    judge_assignments: list,
    db: AsyncSession,
    requested_by: str
):
    for assignment in judge_assignments:
        context = {
            "judge_name": assignment["judge_name"],
            "event_name": event.name,
            "assigned_teams": assignment["teams"],
            "magic_link": assignment["magic_link"],
            "deadline": assignment.get("deadline", "TBD"),
        }
        content = draft_email_content("judge_notification", context)

        await draft_bulk_emails(
            db=db,
            event_id=str(event.id),
            requested_by=requested_by,
            email_type=EmailType.magic_link,
            subject=content["subject"],
            body_html=content["body_html"],
            body_text=content["body_text"],
            recipients=[assignment["judge_email"]]
        )
        print(f"✓ Judge magic link drafted for {assignment['judge_email']}")


async def on_results_approved(
    event: Event,
    results: list,
    db: AsyncSession,
    requested_by: str
):
    context = {
        "event_name": event.name,
        "message": "Results have been announced. Check your score and feedback below."
    }
    content = draft_email_content("result", context)
    recipients = [p["email"] for p in results]

    await draft_bulk_emails(
        db=db,
        event_id=str(event.id),
        requested_by=requested_by,
        email_type=EmailType.result,
        subject=content["subject"],
        body_html=content["body_html"],
        body_text=content["body_text"],
        recipients=recipients
    )
    print(f"✓ Results email batch drafted for {len(recipients)} participants")


async def on_progression(
    event: Event,
    qualifying_teams: list,
    db: AsyncSession,
    requested_by: str
):
    all_recipients = []
    for team in qualifying_teams:
        all_recipients.extend([m["email"] for m in team["members"]])

    context = {
        "event_name": event.name,
        "message": "Congratulations! Your team has qualified for the next round."
    }
    content = draft_email_content("progression", context)

    await draft_bulk_emails(
        db=db,
        event_id=str(event.id),
        requested_by=requested_by,
        email_type=EmailType.progression,
        subject=content["subject"],
        body_html=content["body_html"],
        body_text=content["body_text"],
        recipients=all_recipients
    )
    print(f"✓ Progression email batch drafted for {len(all_recipients)} participants")


# ─── MASTER TRIGGER ───────────────────────────────────────────

async def trigger_stage_emails(
    event: Event,
    new_stage: EventStage,
    db: AsyncSession,
    requested_by: str,
    extra_data: dict = {}
):
    """
    Call this whenever event.stage changes.

    Usage:
    await trigger_stage_emails(
        event=event,
        new_stage=EventStage.team_formation,
        db=db,
        requested_by=str(current_user.id),
        extra_data={"teams": result_teams}
    )
    """
    print(f"\n📧 Triggering emails for stage: {new_stage}")

    if new_stage == EventStage.registration:
        await on_registration_open(event, db, requested_by)

    elif new_stage == EventStage.team_formation:
        teams = extra_data.get("teams", [])
        if teams:
            await on_teams_formed(event, teams, db, requested_by)

    elif new_stage == EventStage.submission:
        await on_submission_stage(event, db, requested_by)

    elif new_stage == EventStage.evaluation:
        judge_assignments = extra_data.get("judge_assignments", [])
        if judge_assignments:
            await on_evaluation_stage(event, judge_assignments, db, requested_by)

    elif new_stage == EventStage.completed:
        results = extra_data.get("results", [])
        qualifying = extra_data.get("qualifying_teams", [])
        if results:
            await on_results_approved(event, results, db, requested_by)
        if qualifying:
            await on_progression(event, qualifying, db, requested_by)

    print(f"✓ All email drafts created for stage: {new_stage}\n")