"""
EKAM Email Triggers

AI-powered email drafting using Groq.

Architecture:
  - Info / bulk emails:  AI drafts → EmailDraft created → ApprovalRequest → organizer approves → SMTP sends
  - OTP / magic link:   Fixed template → SMTP sends immediately (no approval needed)

This module handles ONLY the info/bulk path.
OTP and magic link sending lives in email_service.py.
"""

import asyncio
import json

from groq import Groq
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.models.email import EmailType
from app.models.event import Event, EventStage
from app.models.judge import Judge, JudgeAssignment
from app.models.participant import Participant
from app.services.email_service import draft_bulk_emails


# ─── AI EMAIL DRAFTING ────────────────────────────────────────


def _draft_email_content_sync(groq_client: Groq, model: str, email_type: str, context: dict) -> dict:
    """
    Synchronous Groq call.  Called via asyncio.to_thread so it doesn't block
    the FastAPI event loop.
    """
    prompt = f"""You are EKAM, an autonomous event management system.
Draft a professional, warm email for the following situation.
Email type: {email_type}
Context: {json.dumps(context, indent=2)}
Return ONLY valid JSON (no markdown fences, no extra text):
{{
    "subject": "...",
    "body_text": "plain text version",
    "body_html": "<p>html version</p>"
}}
Rules:
- Use actual names from context, never write [Name] or placeholders
- Be concise and warm
- Sign off as: Team EKAM
"""
    resp = groq_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=800,
    )
    raw = resp.choices[0].message.content.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
        raise


async def draft_email_content(email_type: str, context: dict) -> dict:
    """
    AI-drafts email content using Groq.
    Falls back to a plain template if Groq is unavailable or returns malformed JSON.
    """
    if settings.GROQ_API_KEY:
        try:
            client = Groq(api_key=settings.GROQ_API_KEY)
            return await asyncio.to_thread(
                _draft_email_content_sync,
                client,
                settings.GROQ_MODEL,
                email_type,
                context,
            )
        except Exception as exc:
            print(f"[email_triggers] Groq drafting failed: {exc} — using fallback template")

    return _fallback_template(email_type, context)


def _fallback_template(email_type: str, context: dict) -> dict:
    """Minimal template used when AI drafting fails."""
    event_name = context.get("event_name", "EKAM Event")
    message = context.get("message", "")
    subject = f"[EKAM] Update from {event_name}"
    body_text = f"Hello,\n\nThis is an update from {event_name}.\n{message}\n\nTeam EKAM"
    body_html = (
        f"<p>Hello,</p>"
        f"<p>This is an update from <strong>{event_name}</strong>.</p>"
        f"<p>{message}</p>"
        f"<p>Team EKAM</p>"
    )
    return {"subject": subject, "body_text": body_text, "body_html": body_html}


# ─── STAGE-SPECIFIC DRAFTERS ──────────────────────────────────


async def on_registration_open(event: Event, db: AsyncSession, requested_by: str):
    """Draft a welcome email to all confirmed participants."""
    result = await db.execute(
        select(Participant).where(Participant.event_id == event.id)
    )
    participants = result.scalars().all()
    if not participants:
        return

    context = {
        "event_name": event.name,
        "event_description": event.description or "",
        "event_type": event.type,
        "message": "Registration is now open. Log in to EKAM to complete your profile and join your team.",
    }
    content = await draft_email_content("welcome", context)
    recipients = [p.email for p in participants if p.email]

    if recipients:
        await draft_bulk_emails(
            db=db,
            event_id=str(event.id),
            requested_by=requested_by,
            email_type=EmailType.invitation,
            subject=content["subject"],
            body_html=content["body_html"],
            body_text=content["body_text"],
            recipients=recipients,
        )
        print(f"[email_triggers] Welcome email batch drafted for {len(recipients)} participants")


async def on_teams_formed(event: Event, teams: list, db: AsyncSession, requested_by: str):
    """Draft a team assignment email for each team."""
    for team in teams:
        members = team.get("members", [])
        if not members:
            continue

        teammates_summary = ", ".join(
            f"{m.get('name', 'Member')} ({m.get('institution', '')})"
            for m in members
        )
        context = {
            "event_name": event.name,
            "team_name": team.get("name", "Your Team"),
            "teammates": teammates_summary,
            "rationale": team.get("rationale", ""),
            "message": "You have been assigned to a team. Log in to EKAM to meet your teammates.",
        }
        content = await draft_email_content("team_assignment", context)
        recipients = [m["email"] for m in members if m.get("email")]

        if recipients:
            await draft_bulk_emails(
                db=db,
                event_id=str(event.id),
                requested_by=requested_by,
                email_type=EmailType.team_assignment,
                subject=content["subject"],
                body_html=content["body_html"],
                body_text=content["body_text"],
                recipients=recipients,
            )
            print(f"[email_triggers] Team assignment batch drafted for {team.get('name')}")


async def on_submission_stage(event: Event, db: AsyncSession, requested_by: str):
    """Draft a submission phase announcement to all participants."""
    result = await db.execute(
        select(Participant).where(Participant.event_id == event.id)
    )
    participants = result.scalars().all()
    if not participants:
        return

    context = {
        "event_name": event.name,
        "message": "The submission phase has now begun. Please submit your project before the deadline.",
    }
    content = await draft_email_content("stage_update", context)
    recipients = [p.email for p in participants if p.email]

    if recipients:
        await draft_bulk_emails(
            db=db,
            event_id=str(event.id),
            requested_by=requested_by,
            email_type=EmailType.stage_update,
            subject=content["subject"],
            body_html=content["body_html"],
            body_text=content["body_text"],
            recipients=recipients,
        )
        print(f"[email_triggers] Submission stage email batch drafted")


async def on_evaluation_stage(event: Event, db: AsyncSession, requested_by: str, judge_assignments: list = None):
    """
    Draft evaluation-start emails for judges.
    If judge_assignments aren't passed in, queries them from DB.
    Each judge gets their own draft (with their specific teams listed).
    """
    if not judge_assignments:
        # Query judge assignments for this event
        res = await db.execute(
            select(Judge).where(Judge.event_id == event.id)
        )
        judges = res.scalars().all()

        judge_assignments = []
        for judge in judges:
            res_assign = await db.execute(
                select(JudgeAssignment).where(JudgeAssignment.judge_id == judge.id)
            )
            assignments = res_assign.scalars().all()
            if assignments:
                judge_assignments.append({
                    "judge_name": judge.name or judge.email,
                    "judge_email": judge.email,
                    "teams": [str(a.team_id) for a in assignments],
                    "magic_link": "",
                    "deadline": "TBD",
                })

    for assignment in judge_assignments:
        judge_email = assignment.get("judge_email")
        if not judge_email:
            continue

        context = {
            "event_name": event.name,
            "judge_name": assignment.get("judge_name", "Judge"),
            "assigned_teams": assignment.get("teams", []),
            "deadline": assignment.get("deadline", "TBD"),
            "message": "You have been assigned submissions to evaluate. Please log in to EKAM to begin.",
        }
        content = await draft_email_content("judge_notification", context)

        await draft_bulk_emails(
            db=db,
            event_id=str(event.id),
            requested_by=requested_by,
            email_type=EmailType.stage_update,
            subject=content["subject"],
            body_html=content["body_html"],
            body_text=content["body_text"],
            recipients=[judge_email],
        )
        print(f"[email_triggers] Judge evaluation draft created for {judge_email}")


async def on_progression(event: Event, qualifying_teams: list, db: AsyncSession, requested_by: str):
    """Draft a progression congratulations email to all qualifying team members."""
    all_recipients = []
    for team in qualifying_teams:
        all_recipients.extend(
            m["email"] for m in team.get("members", []) if m.get("email")
        )

    if not all_recipients:
        # Fall back to all participants if member emails weren't provided
        res = await db.execute(
            select(Participant).where(Participant.event_id == event.id)
        )
        all_recipients = [p.email for p in res.scalars().all() if p.email]

    if not all_recipients:
        return

    context = {
        "event_name": event.name,
        "message": "Congratulations! Your team has qualified for the next round.",
    }
    content = await draft_email_content("progression", context)

    await draft_bulk_emails(
        db=db,
        event_id=str(event.id),
        requested_by=requested_by,
        email_type=EmailType.progression,
        subject=content["subject"],
        body_html=content["body_html"],
        body_text=content["body_text"],
        recipients=all_recipients,
    )
    print(f"[email_triggers] Progression email batch drafted for {len(all_recipients)} recipients")


async def on_results_approved(event: Event, results: list, db: AsyncSession, requested_by: str):
    """Draft a results announcement email."""
    recipients = [p.get("email") for p in results if p.get("email")]
    if not recipients:
        res = await db.execute(
            select(Participant).where(Participant.event_id == event.id)
        )
        recipients = [p.email for p in res.scalars().all() if p.email]

    if not recipients:
        return

    context = {
        "event_name": event.name,
        "message": "Results have been announced. Log in to EKAM to check your score and feedback.",
    }
    content = await draft_email_content("result", context)

    await draft_bulk_emails(
        db=db,
        event_id=str(event.id),
        requested_by=requested_by,
        email_type=EmailType.result,
        subject=content["subject"],
        body_html=content["body_html"],
        body_text=content["body_text"],
        recipients=recipients,
    )
    print(f"[email_triggers] Results email batch drafted for {len(recipients)} recipients")


# ─── MASTER TRIGGER ───────────────────────────────────────────


async def trigger_stage_emails(
    event: Event,
    new_stage: EventStage,
    db: AsyncSession,
    requested_by: str,
    extra_data: dict = None,
):
    """
    Call this whenever event.stage changes to automatically draft the appropriate
    AI-written email batch.  All drafts go into ApprovalRequest → organizer approves
    → SMTP sends.  Nothing sends automatically.

    Usage:
        await trigger_stage_emails(
            event=event,
            new_stage=EventStage.submission,
            db=db,
            requested_by=str(organizer_id),
            extra_data={"advancing_teams": [...]},
        )
    """
    if extra_data is None:
        extra_data = {}

    print(f"\n[email_triggers] Drafting emails for stage transition → {new_stage.value}")

    try:
        if new_stage == EventStage.registration:
            await on_registration_open(event, db, requested_by)

        elif new_stage == EventStage.team_formation:
            teams = extra_data.get("teams", [])
            if teams:
                await on_teams_formed(event, teams, db, requested_by)

        elif new_stage == EventStage.submission:
            await on_submission_stage(event, db, requested_by)

        elif new_stage == EventStage.evaluation:
            judge_assignments = extra_data.get("judge_assignments")
            await on_evaluation_stage(event, db, requested_by, judge_assignments)

        elif new_stage == EventStage.completed:
            results = extra_data.get("results", [])
            qualifying = extra_data.get("advancing_teams", [])
            if results:
                await on_results_approved(event, results, db, requested_by)
            if qualifying:
                await on_progression(event, qualifying, db, requested_by)

    except Exception as exc:
        # Email drafting failures must never crash the pipeline
        print(f"[email_triggers] ERROR drafting emails for stage {new_stage.value}: {exc}")

    print(f"[email_triggers] Done drafting emails for stage: {new_stage.value}\n")
