"""EKAM Public Router (Task 6) — no authentication.

The only anonymous surface in the app, isolated to one file so the blast radius
of "public access" is contained and the existing RBAC stays untouched. Provides:
  - GET  /public/events                 → cards of registerable events
  - GET  /public/events/{hash}          → event detail + the approved form spec
  - POST /public/events/{hash}/resume   → upload+parse a resume (returns prefill)
  - POST /public/events/{hash}/register → format-aware registration (auto-confirm)

Writes stay on plain HTTP. Hard gates: registration window, capacity, email
uniqueness, team-size, captcha. ATS scoring + resume parsing are best-effort and
never block a submission.
"""

import time
from collections import defaultdict, deque
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.models.event import Event as EventModel, EventStatus, TeamFormationType
from app.models.participant import Participant as ParticipantModel, RegistrationStatus
from app.models.team import Team as TeamModel, TeamMember as TeamMemberModel

from app.services.file_storage import (
    store_pdf,
    validate_pdf,
    public_base_url,
    local_path_for_url,
)
from app.services import resume_service, ats_service, captcha_service
from app.services.registration_validation import validate_required, extract_identity
from app.services.time_enforcement import registration_window_state

router = APIRouter(prefix="/public", tags=["Public"])


# ── Tiny in-memory per-IP rate limiter ──────────────────────────────────────
# Sufficient for the single-worker deploy (same boundary as the SSE event bus);
# move to Redis for multi-worker. Not a security control on its own — the
# captcha is — just a courtesy throttle against accidental floods.
_HITS: dict[str, deque] = defaultdict(deque)


def _rate_limit(key: str, limit: int, window_s: int) -> None:
    now = time.time()
    dq = _HITS[key]
    while dq and dq[0] < now - window_s:
        dq.popleft()
    if len(dq) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please wait a moment and try again.",
        )
    dq.append(now)


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── Response / request models ────────────────────────────────────────────────

class PublicEventCard(BaseModel):
    hash: str
    name: str
    type: str
    description: Optional[str] = None
    registration_open: bool
    registration_closes_at: Optional[str] = None
    format: str  # "individual" | "team"
    team_registration: bool  # True when a leader registers the whole (preformed) team


class PublicRoundSummary(BaseModel):
    name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class PublicEventDetail(PublicEventCard):
    registration_form_fields: List[Any] = []
    participants_model: str = "individual"
    individual_registration_allowed: bool = True
    min_team_size: int = 1
    max_team_size: int = 4
    rounds: List[PublicRoundSummary] = []


class MemberRegistration(BaseModel):
    answers: dict
    resume_url: str
    is_leader: bool = False


class RegisterRequest(BaseModel):
    captcha_token: Optional[str] = None
    # Individual:
    answers: Optional[dict] = None
    resume_url: Optional[str] = None
    # Team (preformed):
    team_name: Optional[str] = None
    members: Optional[List[MemberRegistration]] = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _is_team_event(event: EventModel) -> bool:
    return (
        (event.participants_model or "individual") == "team"
        and event.team_formation_type == TeamFormationType.preformed
    )


def _iso(dt) -> Optional[str]:
    return dt.isoformat() if dt else None


async def _get_active_event(db: AsyncSession, hash_: str) -> EventModel:
    event = (
        await db.execute(select(EventModel).where(EventModel.hash == hash_))
    ).scalars().first()
    if not event or event.status != EventStatus.active:
        raise HTTPException(status_code=404, detail="Event not found or not open.")
    return event


async def _participant_count(db: AsyncSession, event_id) -> int:
    return (
        await db.execute(
            select(func.count()).select_from(ParticipantModel).where(
                ParticipantModel.event_id == event_id
            )
        )
    ).scalar() or 0


def _ats_for(resume_url: str, event: EventModel) -> Optional[float]:
    """Re-read the stored resume and score it. Best-effort; None on any failure."""
    try:
        path = local_path_for_url(resume_url)
        if not path:
            return None
        text = resume_service.extract_text(path)
        return ats_service.score(text, event)
    except Exception:
        return None


async def _email_taken(db: AsyncSession, event_id, email: str) -> bool:
    existing = (
        await db.execute(
            select(ParticipantModel).where(
                ParticipantModel.event_id == event_id,
                func.lower(ParticipantModel.email) == email.lower(),
            )
        )
    ).scalars().first()
    return existing is not None


def _build_participant(event: EventModel, answers: dict, resume_url: str) -> ParticipantModel:
    identity = extract_identity(event.registration_form_fields, answers)
    email = identity.get("email")
    name = identity.get("name")
    if not email or not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A name and email are required to register.",
        )
    return ParticipantModel(
        event_id=event.id,
        name=str(name),
        email=str(email),
        institution=identity.get("institution"),
        phone=identity.get("phone"),
        gender=identity.get("gender"),
        skills=identity.get("skills") or [],
        registration_data=answers,
        resume_url=resume_url,
        ats_score=_ats_for(resume_url, event),
        status=RegistrationStatus.confirmed,
    )


async def _notify_organizer(db: AsyncSession, event: EventModel, msg: str) -> None:
    try:
        from app.services.notification_service import create_notification

        await create_notification(
            db,
            event_id=str(event.id),
            user_id=str(event.organizer_id),
            title="New registration",
            message=msg,
        )
    except Exception as exc:  # never break the registration on a notify failure
        print(f"[public] organizer notify failed: {exc}")


async def _autopropose(db: AsyncSession, event_id) -> None:
    try:
        from app.services.pipeline_service import autopropose

        await autopropose(db, str(event_id))
    except Exception as exc:
        print(f"[public] autopropose failed: {exc}")


# ── Read endpoints ────────────────────────────────────────────────────────────

@router.get("/events", response_model=List[PublicEventCard])
async def list_public_events(db: AsyncSession = Depends(get_db)):
    """All active events, with their current registration-open state and format."""
    events = (
        await db.execute(
            select(EventModel).where(EventModel.status == EventStatus.active)
            .order_by(EventModel.created_at.desc())
        )
    ).scalars().all()

    cards: List[PublicEventCard] = []
    for e in events:
        is_open, _ = registration_window_state(e)
        cards.append(
            PublicEventCard(
                hash=e.hash,
                name=e.name,
                type=e.type,
                description=e.description,
                registration_open=is_open,
                registration_closes_at=_iso(e.registration_closes_at),
                format=e.participants_model or "individual",
                team_registration=_is_team_event(e),
            )
        )
    return cards


@router.get("/events/{hash}", response_model=PublicEventDetail)
async def get_public_event(hash: str, db: AsyncSession = Depends(get_db)):
    """Event detail + the (approved/live) registration form the public UI renders."""
    from app.models.event import Round as RoundModel

    event = await _get_active_event(db, hash)
    is_open, _ = registration_window_state(event)

    rounds = (
        await db.execute(
            select(RoundModel).where(RoundModel.event_id == event.id)
            .order_by(RoundModel.start_date.asc().nullslast())
        )
    ).scalars().all()

    return PublicEventDetail(
        hash=event.hash,
        name=event.name,
        type=event.type,
        description=event.description,
        registration_open=is_open,
        registration_closes_at=_iso(event.registration_closes_at),
        format=event.participants_model or "individual",
        team_registration=_is_team_event(event),
        registration_form_fields=event.registration_form_fields or [],
        participants_model=event.participants_model or "individual",
        individual_registration_allowed=bool(
            event.individual_registration_allowed
            if event.individual_registration_allowed is not None
            else True
        ),
        min_team_size=event.min_team_size or 1,
        max_team_size=event.max_team_size or 4,
        rounds=[
            PublicRoundSummary(name=r.name, start_date=_iso(r.start_date), end_date=_iso(r.end_date))
            for r in rounds
        ],
    )


# ── Write endpoints ────────────────────────────────────────────────────────────

@router.post("/events/{hash}/resume", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    hash: str,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Public resume upload + parse. Stores the PDF and returns a prefill map the
    form uses to auto-fill what the resume reveals; unmatched fields stay blank."""
    _rate_limit(f"resume:{_client_ip(request)}", limit=20, window_s=300)
    event = await _get_active_event(db, hash)

    contents = await file.read()
    validate_pdf(file.content_type, contents)
    stored = store_pdf(contents, file.filename, public_base_url(str(request.base_url)))

    prefill: dict = {}
    try:
        text = resume_service.extract_text(stored["path"])
        prefill = await resume_service.parse_resume(text, event.registration_form_fields or [])
    except Exception as exc:  # parsing must never block the upload
        print(f"[public] resume parse failed: {exc}")

    return {"url": stored["url"], "name": stored["name"], "prefill": prefill}


@router.post("/events/{hash}/register", status_code=status.HTTP_201_CREATED)
async def register_public(
    hash: str,
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Format-aware public registration. Auto-confirms; registrant appears
    immediately on the organizer's participants list (+ live SSE)."""
    _rate_limit(f"register:{_client_ip(request)}", limit=10, window_s=300)

    event = await _get_active_event(db, hash)

    # 1) Captcha (no-op when no secret is configured).
    if not await captcha_service.verify(body.captcha_token, _client_ip(request)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Captcha verification failed.")

    # 2) Registration window.
    is_open, reason = registration_window_state(event)
    if not is_open:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=reason)

    form_fields = event.registration_form_fields or []
    cap = event.max_participants or 0
    team_event = _is_team_event(event)

    # ── Team (preformed) flow ────────────────────────────────────────────────
    if team_event:
        if not body.members or not (body.team_name or "").strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="This event requires team registration: provide a team name and members.",
            )
        n = len(body.members)
        lo, hi = event.min_team_size or 1, event.max_team_size or 4
        if n < lo or n > hi:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Team must have between {lo} and {hi} members (got {n}).",
            )
        # Validate every member + resume + per-member email uniqueness.
        seen_emails: set[str] = set()
        for m in body.members:
            validate_required(form_fields, m.answers)
            if not (m.resume_url or "").strip():
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A resume is required for every member.")
            ident = extract_identity(form_fields, m.answers)
            email = (ident.get("email") or "").lower()
            if not email:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Each member needs an email.")
            if email in seen_emails:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Duplicate email within the team: {email}")
            seen_emails.add(email)
            if await _email_taken(db, event.id, email):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{email} is already registered for this event.")

        # Capacity (count participants).
        if cap and (await _participant_count(db, event.id)) + n > cap:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Registration is full.")

        # Unique team name within the event.
        existing_team = (
            await db.execute(
                select(TeamModel).where(
                    TeamModel.event_id == event.id,
                    func.lower(TeamModel.name) == body.team_name.strip().lower(),
                )
            )
        ).scalars().first()
        if existing_team:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A team with that name already exists.")

        team = TeamModel(event_id=event.id, name=body.team_name.strip())
        db.add(team)
        await db.flush()  # get team.id

        has_leader = any(m.is_leader for m in body.members)
        created = []
        for i, m in enumerate(body.members):
            p = _build_participant(event, m.answers, m.resume_url)
            db.add(p)
            await db.flush()
            is_leader = m.is_leader or (not has_leader and i == 0)
            db.add(TeamMemberModel(team_id=team.id, participant_id=p.id, is_leader=is_leader))
            created.append(p)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A member is already registered for this event.")

        await _notify_organizer(db, event, f"Team '{team.name}' registered with {n} member(s).")
        await _autopropose(db, event.id)
        return {
            "success": True,
            "team_id": str(team.id),
            "team_name": team.name,
            "members": len(created),
            "status": "confirmed",
        }

    # ── Individual flow ───────────────────────────────────────────────────────
    answers = body.answers
    if not answers:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Registration answers are required.",
        )
    if not (body.resume_url or "").strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A resume is required.")

    validate_required(form_fields, answers)

    ident = extract_identity(form_fields, answers)
    email = (ident.get("email") or "").lower()
    if not email:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="An email is required.")
    if await _email_taken(db, event.id, email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You are already registered for this event.")
    if cap and (await _participant_count(db, event.id)) + 1 > cap:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Registration is full.")

    participant = _build_participant(event, answers, body.resume_url)
    db.add(participant)
    try:
        await db.commit()
        await db.refresh(participant)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You are already registered for this event.")

    await _notify_organizer(db, event, f"{participant.name} ({participant.email}) registered.")
    await _autopropose(db, event.id)
    return {
        "success": True,
        "participant_id": str(participant.id),
        "ats_score": participant.ats_score,
        "status": "confirmed",
    }
