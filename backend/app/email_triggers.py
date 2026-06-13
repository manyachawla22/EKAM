import asyncio
import json
from typing import Any

from groq import Groq
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.certificate import generate_certificate_html
from app.core.config import settings
from app.models.email import EmailType
from app.models.event import Event, EventStage
from app.models.judge import Judge, JudgeAssignment
from app.models.participant import Participant
from app.services.email_service import draft_bulk_emails, send_direct_email


# ---------------------------------------------------------------------
# SMALL HELPERS
# ---------------------------------------------------------------------


def _settings_value(*names: str, default: Any = None) -> Any:
    """
    Safely read config values even if config.py uses uppercase or lowercase names.
    """
    for name in names:
        value = getattr(settings, name, None)
        if value:
            return value

    return default


def _enum_value(value: Any) -> Any:
    """
    Return enum.value when available; otherwise return the original value.
    """
    return getattr(value, "value", value)


def _normalize_token(value: Any) -> str:
    """
    Normalize enum names/values like:
      registration_open
      Registration Open
      registration-open

    into a comparable lowercase token.
    """
    return (
        str(_enum_value(value))
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def _stage_tokens(stage: EventStage) -> set[str]:
    """
    Return both enum name and enum value tokens for safer compatibility across branches.
    """
    tokens: set[str] = set()

    for candidate in (
        getattr(stage, "name", None),
        getattr(stage, "value", None),
        stage,
    ):
        if candidate is not None:
            tokens.add(_normalize_token(candidate))

    return tokens


def _stage_is(stage: EventStage, *expected: str) -> bool:
    """
    Check whether a stage matches one of several possible stage names.
    This prevents crashes if branches used slightly different EventStage names.
    """
    actual_tokens = _stage_tokens(stage)
    expected_tokens = {_normalize_token(item) for item in expected}

    return bool(actual_tokens.intersection(expected_tokens))


def _certificate_label_for_stage(stage: EventStage) -> str:
    """
    Human-readable certificate achievement label.
    """
    if _stage_is(stage, "results_generated", "results"):
        return "Results Generated"

    if _stage_is(stage, "completed", "complete", "event_completed"):
        return "Event Completion"

    if _stage_is(stage, "evaluation", "evaluation_round"):
        return "Evaluation Round Completion"

    if _stage_is(stage, "submission", "submission_round"):
        return "Submission Round Completion"

    if _stage_is(stage, "team_formation"):
        return "Team Formation"

    return "Participation"


def _participant_is_certificate_eligible(participant: Participant) -> bool:
    """
    Certificates should generally go to confirmed/registered participants.

    This is intentionally tolerant because different branches may store participant
    status differently.
    """
    status_value = getattr(participant, "status", None)

    if status_value is None:
        return True

    normalized_status = _normalize_token(status_value)

    return normalized_status in {
        "confirmed",
        "registered",
        "approved",
        "accepted",
        "active",
    }


def _safe_certificate_filename(participant_name: str) -> str:
    """
    Create a simple safe HTML filename.
    """
    cleaned = "".join(
        char if char.isalnum() else "_"
        for char in participant_name.strip()
    ).strip("_")

    if not cleaned:
        cleaned = "participant"

    return f"certificate_{cleaned}.html"


# ---------------------------------------------------------------------
# AI EMAIL DRAFTING
# ---------------------------------------------------------------------


def _draft_email_content_sync(
    groq_client: Groq,
    model: str,
    email_type: str,
    context: dict,
) -> dict:
    """
    Synchronous Groq call.

    Called via asyncio.to_thread so it does not block the FastAPI event loop.
    """
    prompt = f"""You are EKAM, an autonomous event management system.

Draft a professional, warm email for the following situation.

Email type: {email_type}

Context:
{json.dumps(context, indent=2)}

Return ONLY valid JSON. No markdown fences. No extra text.

{{
    "subject": "...",
    "body_text": "plain text version",
    "body_html": "<p>html version</p>"
}}

Rules:
- Use actual names from context, never write [Name] or placeholders.
- Be concise and warm.
- Include the exact literal token {{{{magic_link}}}} once, on its own line in body_text and inside its own <p> in body_html, where the recipient should click to log in. It will be replaced with their personal one-click login link (no OTP). Do NOT invent a URL — use the token verbatim.
- Sign off as: Team EKAM
"""

    response = groq_client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0.7,
        max_tokens=800,
    )

    raw = response.choices[0].message.content.strip()

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
    AI-draft email content using Groq.

    Falls back to a plain template if Groq is unavailable or returns malformed JSON.
    """
    groq_api_key = _settings_value(
        "GROQ_API_KEY",
        "groq_api_key",
        default=None,
    )

    groq_model = _settings_value(
        "GROQ_MODEL",
        "groq_model",
        default="llama-3.3-70b-versatile",
    )

    if groq_api_key:
        try:
            client = Groq(api_key=groq_api_key)

            return await asyncio.to_thread(
                _draft_email_content_sync,
                client,
                groq_model,
                email_type,
                context,
            )

        except Exception as exc:
            print(
                f"[email_triggers] Groq drafting failed: {exc}. "
                "Using fallback template."
            )

    return _fallback_template(email_type, context)


def _fallback_template(email_type: str, context: dict) -> dict:
    """
    Minimal template used when AI drafting fails.
    """
    event_name = context.get("event_name", "EKAM Event")
    message = context.get("message", "")

    subject = f"[EKAM] Update from {event_name}"

    body_text = (
        f"Hello,\n\n"
        f"This is an update from {event_name}.\n\n"
        f"{message}\n\n"
        f"{{{{magic_link}}}}\n\n"
        f"Team EKAM"
    )

    body_html = (
        f"<p>Hello,</p>"
        f"<p>This is an update from <strong>{event_name}</strong>.</p>"
        f"<p>{message}</p>"
        f"<p>{{{{magic_link}}}}</p>"
        f"<p>Team EKAM</p>"
    )

    return {
        "subject": subject,
        "body_text": body_text,
        "body_html": body_html,
    }


# ---------------------------------------------------------------------
# STAGE-SPECIFIC EMAIL DRAFTERS
# ---------------------------------------------------------------------


async def on_registration_open(
    event: Event,
    db: AsyncSession,
    requested_by: str,
):
    """
    Draft a welcome email to all participants.
    """
    result = await db.execute(
        select(Participant).where(
            Participant.event_id == event.id,
        )
    )
    participants = result.scalars().all()

    if not participants:
        return

    context = {
        "event_name": event.name,
        "event_description": event.description or "",
        "event_type": str(_enum_value(getattr(event, "type", ""))),
        "message": (
            "Registration is now open. Log in to EKAM to complete your profile "
            "and participate in the event."
        ),
    }

    content = await draft_email_content("welcome", context)

    recipients = [
        participant.email
        for participant in participants
        if getattr(participant, "email", None)
    ]

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

        print(
            f"[email_triggers] Welcome email batch drafted for "
            f"{len(recipients)} participants"
        )


async def on_teams_formed(
    event: Event,
    teams: list,
    db: AsyncSession,
    requested_by: str,
):
    """
    Draft a team assignment email for each team.
    """
    for team in teams:
        members = team.get("members", [])

        if not members:
            continue

        teammates_summary = ", ".join(
            f"{member.get('name', 'Member')} "
            f"({member.get('institution', '')})"
            for member in members
        )

        context = {
            "event_name": event.name,
            "team_name": team.get("name", "Your Team"),
            "teammates": teammates_summary,
            "rationale": team.get("rationale", ""),
            "message": (
                "You have been assigned to a team. "
                "Log in to EKAM to view your team details."
            ),
        }

        content = await draft_email_content("team_assignment", context)

        recipients = [
            member["email"]
            for member in members
            if member.get("email")
        ]

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

            print(
                f"[email_triggers] Team assignment batch drafted for "
                f"{team.get('name')}"
            )


async def on_submission_stage(
    event: Event,
    db: AsyncSession,
    requested_by: str,
):
    """
    Draft a submission phase announcement to all participants.
    """
    result = await db.execute(
        select(Participant).where(
            Participant.event_id == event.id,
        )
    )
    participants = result.scalars().all()

    if not participants:
        return

    context = {
        "event_name": event.name,
        "message": (
            "The submission phase has now begun. "
            "Please submit your project before the deadline."
        ),
    }

    content = await draft_email_content("stage_update", context)

    recipients = [
        participant.email
        for participant in participants
        if getattr(participant, "email", None)
    ]

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

        print("[email_triggers] Submission stage email batch drafted")


async def on_evaluation_stage(
    event: Event,
    db: AsyncSession,
    requested_by: str,
    judge_assignments: list | None = None,
):
    """
    Draft evaluation-start emails for judges.

    If judge_assignments are not passed in, query them from DB.
    Each judge gets a draft with their assigned teams.
    """
    if not judge_assignments:
        judge_result = await db.execute(
            select(Judge).where(
                Judge.event_id == event.id,
            )
        )
        judges = judge_result.scalars().all()

        judge_assignments = []

        for judge in judges:
            assignment_result = await db.execute(
                select(JudgeAssignment).where(
                    JudgeAssignment.judge_id == judge.id,
                )
            )
            assignments = assignment_result.scalars().all()

            if assignments:
                judge_assignments.append(
                    {
                        "judge_name": judge.name or judge.email,
                        "judge_email": judge.email,
                        "teams": [
                            str(assignment.team_id)
                            for assignment in assignments
                        ],
                        "magic_link": "",
                        "deadline": "TBD",
                    }
                )

    for assignment in judge_assignments:
        judge_email = assignment.get("judge_email")

        if not judge_email:
            continue

        context = {
            "event_name": event.name,
            "judge_name": assignment.get("judge_name", "Judge"),
            "assigned_teams": assignment.get("teams", []),
            "deadline": assignment.get("deadline", "TBD"),
            "message": (
                "You have been assigned submissions to evaluate. "
                "Please log in to EKAM to begin."
            ),
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

        print(
            f"[email_triggers] Judge evaluation draft created for "
            f"{judge_email}"
        )


async def on_progression(
    event: Event,
    qualifying_teams: list,
    db: AsyncSession,
    requested_by: str,
):
    """
    Draft a progression congratulations email to all qualifying team members.
    """
    all_recipients: list[str] = []

    for team in qualifying_teams:
        all_recipients.extend(
            member["email"]
            for member in team.get("members", [])
            if member.get("email")
        )

    if not all_recipients:
        participant_result = await db.execute(
            select(Participant).where(
                Participant.event_id == event.id,
            )
        )
        all_recipients = [
            participant.email
            for participant in participant_result.scalars().all()
            if getattr(participant, "email", None)
        ]

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

    print(
        f"[email_triggers] Progression email batch drafted for "
        f"{len(all_recipients)} recipients"
    )


async def on_results_approved(
    event: Event,
    results: list,
    db: AsyncSession,
    requested_by: str,
):
    """
    Draft a results announcement email.
    """
    recipients = [
        participant.get("email")
        for participant in results
        if participant.get("email")
    ]

    if not recipients:
        participant_result = await db.execute(
            select(Participant).where(
                Participant.event_id == event.id,
            )
        )
        recipients = [
            participant.email
            for participant in participant_result.scalars().all()
            if getattr(participant, "email", None)
        ]

    if not recipients:
        return

    context = {
        "event_name": event.name,
        "message": (
            "Results have been announced. "
            "Log in to EKAM to check your score and feedback."
        ),
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

    print(
        f"[email_triggers] Results email batch drafted for "
        f"{len(recipients)} recipients"
    )


async def on_certificate_distribution(
    event: Event,
    db: AsyncSession,
    requested_by: str,
    achievement: str = "Participation",
):
    """
    Generate and directly email certificates to eligible participants.

    This intentionally does not replace existing approval-based email drafting.
    It only runs when trigger_stage_emails calls it.
    """
    participant_result = await db.execute(
        select(Participant).where(
            Participant.event_id == event.id,
        )
    )
    participants = participant_result.scalars().all()

    if not participants:
        print("[email_triggers] No participants found for certificate distribution")
        return

    sent_count = 0
    failed_count = 0
    skipped_count = 0

    for participant in participants:
        participant_email = getattr(participant, "email", None)

        if not participant_email:
            skipped_count += 1
            continue

        if not _participant_is_certificate_eligible(participant):
            skipped_count += 1
            continue

        participant_name = (
            getattr(participant, "name", None)
            or participant_email.split("@")[0]
            or "Participant"
        )

        try:
            certificate_html = generate_certificate_html(
                participant_name=participant_name,
                competition_name=event.name,
                achievement=achievement,
            )

            subject = f"{event.name} Certificate of {achievement}"

            body_text = (
                f"Dear {participant_name},\n\n"
                f"Congratulations on your participation in {event.name}.\n\n"
                f"Your certificate of {achievement} is attached as an HTML file.\n\n"
                f"Best regards,\n"
                f"Team EKAM"
            )

            body_html = f"""
<p>Dear {participant_name},</p>
<p>Congratulations on your participation in <strong>{event.name}</strong>.</p>
<p>Your certificate of <strong>{achievement}</strong> is attached as an HTML file.</p>
<p>Best regards,<br/>Team EKAM</p>
"""

            attachment_name = _safe_certificate_filename(participant_name)

            ok = await send_direct_email(
                to=participant_email,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                attachments={
                    attachment_name: certificate_html.encode("utf-8"),
                },
            )

            if ok:
                sent_count += 1
            else:
                failed_count += 1
                continue

        except Exception as exc:
            print(
                f"[email_triggers] Certificate email failed for "
                f"{participant_email}: {exc}"
            )
            failed_count += 1

    print(
        "[email_triggers] Certificate distribution complete: "
        f"{sent_count} sent, {failed_count} failed, {skipped_count} skipped. "
        f"Requested by: {requested_by}"
    )


# ---------------------------------------------------------------------
# MASTER TRIGGER
# ---------------------------------------------------------------------


async def trigger_stage_emails(
    event: Event,
    new_stage: EventStage,
    db: AsyncSession,
    requested_by: str,
    extra_data: dict | None = None,
):
    """
    Call this whenever event.stage changes.

    Existing behavior:
      - registration -> draft welcome emails
      - team_formation -> draft team emails
      - submission -> draft submission emails
      - evaluation -> draft judge emails
      - completed -> draft results/progression emails

    Added behavior:
      - results_generated -> directly send certificates
      - completed + extra_data["send_certificates"] == True -> directly send certificates
    """
    if extra_data is None:
        extra_data = {}

    stage_value = getattr(new_stage, "value", new_stage)

    print(f"\n[email_triggers] Handling email trigger for stage: {stage_value}")

    try:
        if _stage_is(new_stage, "registration", "registration_open"):
            await on_registration_open(
                event=event,
                db=db,
                requested_by=requested_by,
            )

        elif _stage_is(new_stage, "team_formation"):
            teams = extra_data.get("teams", [])

            if teams:
                await on_teams_formed(
                    event=event,
                    teams=teams,
                    db=db,
                    requested_by=requested_by,
                )

        elif _stage_is(new_stage, "submission", "submission_round"):
            await on_submission_stage(
                event=event,
                db=db,
                requested_by=requested_by,
            )

        elif _stage_is(new_stage, "evaluation", "evaluation_round"):
            judge_assignments = extra_data.get("judge_assignments")

            await on_evaluation_stage(
                event=event,
                db=db,
                requested_by=requested_by,
                judge_assignments=judge_assignments,
            )

        elif _stage_is(new_stage, "results_generated", "results"):
            achievement = extra_data.get(
                "certificate_achievement",
                _certificate_label_for_stage(new_stage),
            )

            await on_certificate_distribution(
                event=event,
                db=db,
                requested_by=requested_by,
                achievement=achievement,
            )

        elif _stage_is(new_stage, "completed", "complete", "event_completed"):
            results = extra_data.get("results", [])
            qualifying = extra_data.get("advancing_teams", [])

            if results:
                await on_results_approved(
                    event=event,
                    results=results,
                    db=db,
                    requested_by=requested_by,
                )

            if qualifying:
                await on_progression(
                    event=event,
                    qualifying_teams=qualifying,
                    db=db,
                    requested_by=requested_by,
                )

            if extra_data.get("send_certificates"):
                achievement = extra_data.get(
                    "certificate_achievement",
                    _certificate_label_for_stage(new_stage),
                )

                await on_certificate_distribution(
                    event=event,
                    db=db,
                    requested_by=requested_by,
                    achievement=achievement,
                )

    except Exception as exc:
        # Email failures should never crash the event pipeline.
        print(
            f"[email_triggers] ERROR while handling stage "
            f"{stage_value}: {exc}"
        )

    print(f"[email_triggers] Done handling email trigger for stage: {stage_value}\n")


