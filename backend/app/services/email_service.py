
"""
EKAM Email Service

Drafts and sends emails.
Uses a draft-based model for batched emails (requires approval).
OTP/Magic links bypass approval for immediate delivery.
"""

import asyncio
import base64
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import resend

from app.models.email import EmailDraft, EmailType, EmailStatus
from app.models.approval import RequestType

from app.services.approval_service import create_approval_request
from app.services.magic_link_service import generate_magic_link
from app.core.config import settings


# Placeholder that AI-drafted / templated bodies can include where the
# recipient's personal one-click login link should appear. It is replaced at
# SEND time with a freshly minted, per-recipient magic link (see
# `_inject_magic_link`). If a body omits the placeholder, a login CTA is
# appended instead, so every participant/judge email is one-click regardless.
MAGIC_LINK_PLACEHOLDER = "{{magic_link}}"


async def magic_link_for_recipient(
    db: AsyncSession,
    event_id,
    email: str,
) -> Optional[str]:
    """Resolve the participant or judge with this email *within this event* and
    mint a single-use magic-login link for them. Returns ``None`` when the
    address doesn't belong to a participant/judge of the event (e.g. an
    organizer or an unknown address) so callers can skip injection gracefully.

    Per-recipient is the whole point: a shared link would log everyone in as the
    same person. Generation therefore happens here, at send time, never at draft
    time.
    """
    if not event_id or not email:
        return None

    from app.models.participant import Participant
    from app.models.judge import Judge

    normalized = email.strip().lower()

    participant = (
        await db.execute(
            select(Participant).where(
                Participant.event_id == event_id,
                func.lower(Participant.email) == normalized,
            )
        )
    ).scalars().first()
    if participant:
        return await generate_magic_link(
            db, str(participant.id), "participant", str(event_id)
        )

    judge = (
        await db.execute(
            select(Judge).where(
                Judge.event_id == event_id,
                func.lower(Judge.email) == normalized,
            )
        )
    ).scalars().first()
    if judge:
        return await generate_magic_link(db, str(judge.id), "judge", str(event_id))

    return None


def _inject_magic_link(body: Optional[str], link: str, is_html: bool) -> Optional[str]:
    """Substitute the magic-link placeholder, or append a login CTA if absent."""
    if not body:
        # No body at all — synthesize a minimal one so the link still goes out.
        return (
            f'<p><a href="{link}">Log in to EKAM</a></p>'
            if is_html
            else f"Log in to EKAM (one-click, no OTP needed):\n{link}\n"
        )

    if MAGIC_LINK_PLACEHOLDER in body:
        return body.replace(MAGIC_LINK_PLACEHOLDER, link)

    # No placeholder — append a clear call to action.
    if is_html:
        return (
            f"{body}"
            f'<p style="margin-top:16px">'
            f'<a href="{link}" '
            f'style="background:#e8503a;color:#fff;padding:10px 18px;'
            f'border-radius:6px;text-decoration:none;font-weight:600;display:inline-block">'
            f"Open EKAM &rarr;</a></p>"
            f'<p style="font-size:12px;color:#888">'
            f"This is your personal one-click login link — no OTP required. "
            f"It expires in 48 hours and can be used once.</p>"
        )
    return (
        f"{body}\n\n"
        f"Open EKAM (one-click login, no OTP needed):\n{link}\n\n"
        f"This personal link expires in 48 hours and can be used once."
    )


# =========================================================
# EMAIL TEMPLATES
# =========================================================

def _participant_login_template(event_name: str, event_hash: str, frontend_url: str) -> str:
    return (
        f"Hello,\n\n"
        f"Your team has been formed for {event_name}!\n\n"
        f"Click your personal one-click login link to open the participant portal "
        f"(no OTP needed):\n\n"
        f"{{{{magic_link}}}}\n\n"
        f"Prefer to log in manually? Visit {frontend_url}/auth and use:\n"
        f"  Event Hash : {event_hash}\n"
        f"  Your Email : (the address this email was sent to)\n"
        f"then request your OTP.\n\n"
        f"Best of luck,\n"
        f"Team EKAM"
    )


def _judge_login_template(event_name: str, event_hash: str, frontend_url: str) -> str:
    return (
        f"Hello,\n\n"
        f"You have been assigned as a judge for {event_name}.\n\n"
        f"Click your personal one-click login link to open the judge portal "
        f"(no OTP needed):\n\n"
        f"{{{{magic_link}}}}\n\n"
        f"Prefer to log in manually? Visit {frontend_url}/auth and use:\n"
        f"  Event Hash : {event_hash}\n"
        f"  Your Email : (the address this email was sent to)\n"
        f"then request your OTP.\n\n"
        f"Teams are looking forward to your evaluation.\n\n"
        f"Team EKAM"
    )


def _round_advancement_template(event_name: str, round_name: str) -> str:
    return (
        f"Hello,\n\n"
        f"Congratulations! Your team has advanced to {round_name} in {event_name}.\n\n"
        f"Check the participant portal for submission deadlines and further details.\n\n"
        f"Keep it up!\n\n"
        f"Team EKAM"
    )


# =========================================================
# DRAFT HELPERS (called by approval execution)
# =========================================================

async def draft_participant_login_emails(
    db: AsyncSession,
    event_id: str,
    event_name: str,
    event_hash: str,
    participant_emails: List[str],
    requested_by: str,
):
    """Draft login emails for all participants and queue for approval."""
    if not participant_emails:
        return None
    body = _participant_login_template(event_name, event_hash, settings.FRONTEND_URL)
    return await draft_bulk_emails(
        db=db,
        event_id=event_id,
        requested_by=requested_by,
        email_type=EmailType.team_assignment,
        subject=f"{event_name} — Your Team Is Set! Login Details Inside",
        body_html="",
        body_text=body,
        recipients=participant_emails,
    )


async def draft_judge_login_emails(
    db: AsyncSession,
    event_id: str,
    event_name: str,
    event_hash: str,
    judge_emails: List[str],
    requested_by: str,
):
    """Draft login emails for all assigned judges and queue for approval."""
    if not judge_emails:
        return None
    body = _judge_login_template(event_name, event_hash, settings.FRONTEND_URL)
    return await draft_bulk_emails(
        db=db,
        event_id=event_id,
        requested_by=requested_by,
        email_type=EmailType.invitation,
        subject=f"{event_name} — Judge Assignment Confirmed",
        body_html="",
        body_text=body,
        recipients=judge_emails,
    )


async def draft_round_advancement_emails(
    db: AsyncSession,
    event_id: str,
    event_name: str,
    round_name: str,
    participant_emails: List[str],
    requested_by: str,
):
    """Draft round advancement emails and queue for approval."""
    if not participant_emails:
        return None
    body = _round_advancement_template(event_name, round_name)
    return await draft_bulk_emails(
        db=db,
        event_id=event_id,
        requested_by=requested_by,
        email_type=EmailType.stage_update,
        subject=f"Congratulations! You've Advanced — {event_name}",
        body_html="",
        body_text=body,
        recipients=participant_emails,
    )


# =========================================================
# SENDING LOGIC
# =========================================================

async def _send_via_resend(
    recipient: str,
    subject: str,
    body: str,
    email_type: str,
    is_html: bool = False,
) -> bool:
    """
    Sends one email via the Resend SDK.
    Raises on failure so callers can mark drafts as failed.
    API key is read from settings.SMTP_PASSWORD (Resend API key stored there).
    """
    resend.api_key = settings.SMTP_PASSWORD

    params: resend.Emails.SendParams = {
        "from": settings.EMAIL_FROM,
        "to": [recipient],
        "subject": subject,
        "html" if is_html else "text": body,
    }

    response = await asyncio.to_thread(resend.Emails.send, params)
    print(f"[email_service] SENT [{email_type.upper()}] → {recipient}, id={response['id']}")
    return True


async def send_direct_email(
    to: str,
    subject: str,
    body_html: Optional[str] = None,
    body_text: Optional[str] = None,
    attachments: Optional[dict[str, bytes]] = None,
) -> bool:
    """
    Send a single email immediately via Resend (no approval queue).

    Used for system-triggered, non-bulk messages such as anomaly alerts to a
    judge or a generated report to the organizer. `attachments` maps a filename
    to its raw bytes. Never raises — returns True/False so callers (which run
    in best-effort side-effect paths) are not interrupted.
    """
    try:
        resend.api_key = settings.SMTP_PASSWORD

        params: dict = {
            "from": settings.EMAIL_FROM,
            "to": [to],
            "subject": subject,
        }
        if body_html:
            params["html"] = body_html
        if body_text:
            params["text"] = body_text
        if attachments:
            params["attachments"] = [
                {
                    "filename": filename,
                    "content": base64.b64encode(file_bytes).decode("ascii"),
                }
                for filename, file_bytes in attachments.items()
            ]

        response = await asyncio.to_thread(resend.Emails.send, params)
        print(f"[email_service] DIRECT email sent → {to}, id={response.get('id')}")
        return True
    except Exception as exc:
        print(f"[email_service] DIRECT email FAILED to {to}: {exc}")
        return False


async def send_authenticated_email(
    db: AsyncSession,
    event_id,
    to: str,
    subject: str,
    body_html: Optional[str] = None,
    body_text: Optional[str] = None,
    attachments: Optional[dict[str, bytes]] = None,
) -> bool:
    """Send a single immediate email with a per-recipient one-click login link
    injected (no OTP). Use for system-triggered messages to a known
    participant/judge — anomaly alerts, round results, etc.

    Falls back to plain `send_direct_email` if the recipient can't be resolved to
    a participant/judge of the event. Never raises.
    """
    try:
        link = await magic_link_for_recipient(db, event_id, to)
    except Exception as exc:
        print(f"[email_service] magic link generation failed for {to}: {exc}")
        link = None

    if link:
        body_html = _inject_magic_link(body_html, link, is_html=True) if body_html else body_html
        body_text = _inject_magic_link(body_text, link, is_html=False) if body_text else body_text
        # If the caller only supplied one body form, make sure the link still
        # ships by synthesizing the missing form.
        if not body_html and not body_text:
            body_text = _inject_magic_link(None, link, is_html=False)

    return await send_direct_email(
        to=to,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        attachments=attachments,
    )


async def send_email(
    db: AsyncSession,
    email_draft: EmailDraft,
) -> bool:
    """
    Attempts to send a drafted email and updates its status.
    Returns True on success, False on failure (never raises).
    """
    try:
        await _send_via_resend(
            recipient=email_draft.recipient_email,
            subject=email_draft.subject,
            body=email_draft.body_html or email_draft.body_text or "",
            email_type=email_draft.email_type.value,
            is_html=bool(email_draft.body_html),
        )
        email_draft.status = EmailStatus.sent
        email_draft.sent_at = datetime.now(timezone.utc)
        await db.commit()
        return True
    except Exception as exc:
        print(f"[email_service] FAILED to send to {email_draft.recipient_email}: {exc}")
        email_draft.status = EmailStatus.failed
        await db.commit()
        return False


# =========================================================
# IMMEDIATE EMAILS (No Approval Required)
# =========================================================

async def send_otp_email(email: str, otp: str):
    """
    Fixed-template OTP email — sends immediately, no approval required.
    Uses a structured template (not AI-drafted) because delivery speed matters.
    """
    try:
        await _send_via_resend(
            recipient=email,
            subject="Your EKAM Login Code",
            body=(
                f"Hello,\n\n"
                f"Your one-time login code for EKAM is:\n\n"
                f"    {otp}\n\n"
                f"This code expires in 10 minutes. Do not share it with anyone.\n\n"
                f"If you did not request this code, you can safely ignore this email.\n\n"
                f"Team EKAM"
            ),
            email_type="otp",
        )
    except Exception as exc:
        print(f"[email_service] OTP email failed for {email}: {exc}")


async def send_judge_invite_email(
    email: str,
    judge_name: str,
    event_name: str,
    event_hash: str,
    invite_link: str,
):
    """
    Immediate invite email to a judge with an accept/decline link.
    No approval queue — the organizer explicitly chose this person.
    """
    try:
        body = (
            f"Hello {judge_name},\n\n"
            f"You have been invited to judge \"{event_name}\" on EKAM.\n\n"
            f"Please click the link below to accept or decline this invitation:\n\n"
            f"    {invite_link}\n\n"
            f"If you accept, you will receive your login credentials "
            f"(Event Hash and OTP instructions) on the same page.\n\n"
            f"This invitation link is unique to you — please do not share it.\n\n"
            f"Team EKAM"
        )
        await _send_via_resend(
            recipient=email,
            subject=f"Judge Invitation — {event_name}",
            body=body,
            email_type="judge_invite",
        )
    except Exception as exc:
        print(f"[email_service] Judge invite email failed for {email}: {exc}")


async def send_magic_link_email(email: str, link: str):
    """
    Fixed-template magic link email — sends immediately, no approval required.
    """
    try:
        await _send_via_resend(
            recipient=email,
            subject="Your EKAM Magic Login Link",
            body=(
                f"Hello,\n\n"
                f"Click the link below to log in to EKAM:\n\n"
                f"    {link}\n\n"
                f"This link expires in 48 hours and can only be used once.\n\n"
                f"If you did not request this, you can safely ignore this email.\n\n"
                f"Team EKAM"
            ),
            email_type="magic_link",
        )
    except Exception as exc:
        print(f"[email_service] Magic link email failed for {email}: {exc}")


# =========================================================
# DRAFT-BASED EMAILS (Requires Approval)
# =========================================================

async def draft_email(
    db: AsyncSession,
    event_id: str,
    email_type: EmailType,
    recipient_email: str,
    subject: str,
    body_html: str,
    body_text: str | None = None,
    recipient_name: str | None = None,
    approval_id: str | None = None,
) -> EmailDraft:
    """Create a single email draft."""
    
    draft = EmailDraft(
        event_id=event_id,
        email_type=email_type,
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        status=EmailStatus.pending_approval if approval_id else EmailStatus.draft,
        approval_id=approval_id,
    )
    
    db.add(draft)
    await db.commit()
    await db.refresh(draft)
    return draft


async def draft_bulk_emails(
    db: AsyncSession,
    event_id: str,
    requested_by: str,
    email_type: EmailType,
    subject: str,
    body_html: str,
    recipients: List[str],
    body_text: str | None = None,
):
    """
    Create an approval request, then create email drafts linked to it.
    """
    
    payload = {
        "email_type": email_type.value,
        "subject": subject,
        "recipient_count": len(recipients)
    }
    
    approval = await create_approval_request(
        db=db,
        event_id=event_id,
        request_type=RequestType.email_batch,
        payload=payload,
        requested_by=requested_by
    )
    
    drafts = []
    for recipient in recipients:
        draft = EmailDraft(
            event_id=event_id,
            email_type=email_type,
            recipient_email=recipient,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            status=EmailStatus.pending_approval,
            approval_id=approval.id
        )
        db.add(draft)
        drafts.append(draft)
        
    await db.commit()
    return approval, drafts


async def execute_approved_email_batch(
    db: AsyncSession,
    approval_id: str
):
    """
    Executed by the Approval Service when an email batch is approved.
    Fetches all linked drafts, marks them as approved, and sends them.
    """
    result = await db.execute(
        select(EmailDraft).where(
            EmailDraft.approval_id == approval_id,
            EmailDraft.status == EmailStatus.pending_approval
        )
    )
    drafts = result.scalars().all()

    sent_count = 0
    for draft in drafts:
        # Mint a per-recipient one-click login link and inject it into the body
        # right before sending. Generation MUST be per recipient — a shared link
        # would authenticate everyone as the same person. Best-effort: if the
        # recipient isn't a participant/judge of the event (or generation
        # fails), the email still goes out, just without an auto-login link.
        try:
            link = await magic_link_for_recipient(db, draft.event_id, draft.recipient_email)
        except Exception as exc:
            print(f"[email_service] magic link generation failed for {draft.recipient_email}: {exc}")
            link = None

        if link:
            if draft.body_html:
                draft.body_html = _inject_magic_link(draft.body_html, link, is_html=True)
            if draft.body_text:
                draft.body_text = _inject_magic_link(draft.body_text, link, is_html=False)
            if not draft.body_html and not draft.body_text:
                draft.body_text = _inject_magic_link(None, link, is_html=False)

        # send_email() handles status update to sent/failed and commits internally
        success = await send_email(db, draft)
        if success:
            sent_count += 1

    return sent_count


async def list_drafts(
    db: AsyncSession,
    event_id: str
) -> List[EmailDraft]:
    """List all email drafts for an event."""
    result = await db.execute(
        select(EmailDraft).where(
            EmailDraft.event_id == event_id
        ).order_by(EmailDraft.created_at.desc())
    )
    return list(result.scalars().all())

