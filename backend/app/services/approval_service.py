from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.approval import ApprovalRequest, ApprovalStatus, RequestType


async def create_approval_request(
    db: AsyncSession,
    event_id: str,
    request_type: RequestType,
    payload: dict,
    requested_by: str,
) -> ApprovalRequest:
    """Create a new approval request in the pending state."""
    
    approval = ApprovalRequest(
        event_id=event_id,
        request_type=request_type,
        payload=payload,
        requested_by=requested_by,
        status=ApprovalStatus.pending
    )
    
    db.add(approval)
    await db.commit()
    await db.refresh(approval)

    await _publish_approval_signal(db, event_id, approval)

    return approval


async def _publish_approval_signal(db: AsyncSession, event_id, approval) -> None:
    """Push a live 'approval' signal to the event's organizer (SSE). Best-effort."""
    try:
        from app.models.event import Event
        from app.services.event_bus import safe_publish

        event = (
            await db.execute(select(Event).where(Event.id == event_id))
        ).scalars().first()
        if event and event.organizer_id:
            await safe_publish(
                [str(event.organizer_id)],
                {
                    "type": "approval",
                    "event_id": str(event_id),
                    "approval_id": str(approval.id),
                    "status": getattr(approval.status, "value", str(approval.status)),
                },
            )
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[approval_service] approval signal failed: {exc}")


async def list_pending_approvals(
    db: AsyncSession,
    event_id: str
) -> List[ApprovalRequest]:
    """List all pending approval requests for an event."""
    
    result = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.event_id == event_id,
            ApprovalRequest.status == ApprovalStatus.pending
        ).order_by(ApprovalRequest.requested_at.desc())
    )
    
    return list(result.scalars().all())


async def list_approval_history(
    db: AsyncSession,
    event_id: str
) -> List[ApprovalRequest]:
    """List all approval requests for an event (including resolved)."""
    
    result = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.event_id == event_id
        ).order_by(ApprovalRequest.requested_at.desc())
    )
    
    return list(result.scalars().all())


async def get_approval(
    db: AsyncSession,
    approval_id: str
) -> ApprovalRequest:
    """Get a specific approval request."""
    
    result = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id
        )
    )
    approval = result.scalars().first()
    
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found"
        )

    return approval


async def update_approval_payload(
    db: AsyncSession,
    approval_id: str,
    payload: dict,
) -> ApprovalRequest:
    """Edit a pending approval's proposal before it is approved.

    For email batches, propagate subject/body edits to the linked EmailDraft
    rows so the eventual send reflects the changes.
    """
    approval = await get_approval(db, approval_id)

    if approval.status != ApprovalStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit a request that is already {approval.status.value}",
        )

    approval.payload = payload

    if approval.request_type == RequestType.email_batch:
        from app.models.email import EmailDraft

        drafts = (
            await db.execute(
                select(EmailDraft).where(EmailDraft.approval_id == approval.id)
            )
        ).scalars().all()
        for d in drafts:
            if payload.get("subject"):
                d.subject = payload["subject"]
            if payload.get("body_html") is not None:
                d.body_html = payload["body_html"]
            if payload.get("body_text") is not None:
                d.body_text = payload["body_text"]

    await db.commit()
    await db.refresh(approval)
    return approval


async def review_approval(
    db: AsyncSession,
    approval_id: str,
    action: ApprovalStatus,
    reviewer_id: str,
    notes: str | None = None,
    cutoff_score: float | None = None,
) -> ApprovalRequest:
    """Approve, reject, or request revision on an approval request."""

    if action not in [ApprovalStatus.approved, ApprovalStatus.rejected, ApprovalStatus.revised]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be approved, rejected, or revised."
        )

    approval = await get_approval(db, approval_id)

    if approval.status != ApprovalStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot review request that is already {approval.status.value}"
        )

    # Let the organizer set the advancement cutoff at approval time.
    if cutoff_score is not None and approval.request_type == RequestType.stage_transition:
        approval.payload = {**(approval.payload or {}), "cutoff_score": cutoff_score}

    approval.status = action
    approval.reviewed_by = reviewer_id
    approval.review_notes = notes
    approval.reviewed_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(approval)

    if action == ApprovalStatus.approved:
        await execute_approved_action(db, approval)

    # Signal the organizer's other open views that the pending list changed
    # (the badge/panel should refresh). Pipeline-affecting executions publish
    # their own 'pipeline' signal from execute_pipeline_transition.
    await _publish_approval_signal(db, approval.event_id, approval)

    return approval


async def execute_approved_action(
    db: AsyncSession,
    approval: ApprovalRequest
):
    """
    Dispatch the payload to the appropriate service for execution.
    This will be fully wired up in Phase 4 (CP-SAT), Phase 5 (Emails), etc.
    """
    
    # Wire up the actual execution functions for Phase 4
    if approval.request_type == RequestType.team_formation:
        from app.services.assignment_service import execute_team_formation
        await execute_team_formation(db, approval.payload)
        
    elif approval.request_type == RequestType.judge_assignment:
        from app.services.assignment_service import execute_judge_assignment
        await execute_judge_assignment(db, approval.payload)
        
    elif approval.request_type == RequestType.email_batch:
        from app.services.email_service import execute_approved_email_batch
        await execute_approved_email_batch(db, str(approval.id))

    elif approval.request_type == RequestType.leaderboard_publish:
        pass  # leaderboard is read-only; no mutation needed on publish

    elif approval.request_type == RequestType.stage_transition:
        from app.services.pipeline_service import execute_stage_transition
        await execute_stage_transition(db, approval.payload)

    elif approval.request_type == RequestType.progression:
        # Progression reuses the stage transition executor — both advance teams
        from app.services.pipeline_service import execute_stage_transition
        await execute_stage_transition(db, approval.payload)

    elif approval.request_type == RequestType.registration_form:
        await _execute_registration_form(db, approval)

    elif approval.request_type == RequestType.event_deploy:
        await _execute_event_deploy(db, approval)

    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unknown request type {approval.request_type}"
        )


async def _execute_registration_form(db: AsyncSession, approval: ApprovalRequest) -> None:
    """Apply an approved public-registration-form proposal to the Event.

    Idempotent: re-approval simply overwrites the live field set. The payload
    shape is {"fields": [...], "participants_model"?, "individual_registration_allowed"?}.
    Until this runs, the public detail endpoint serves no/old fields, so the
    form goes live only after approval — the human-in-the-loop gate the user asked for.
    """
    from app.models.event import Event

    payload = approval.payload or {}
    fields = payload.get("fields")

    event = (
        await db.execute(select(Event).where(Event.id == approval.event_id))
    ).scalars().first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found for registration_form approval",
        )

    if isinstance(fields, list):
        event.registration_form_fields = fields
    if payload.get("participants_model") in ("individual", "team"):
        event.participants_model = payload["participants_model"]
    if isinstance(payload.get("individual_registration_allowed"), bool):
        event.individual_registration_allowed = payload["individual_registration_allowed"]

    await db.commit()


async def _execute_event_deploy(db: AsyncSession, approval: ApprovalRequest) -> None:
    """Publish a gated AI event (option C). Flips the draft event to active and
    materializes rounds/judges/rubric on first approval. Idempotent: re-approval
    of an already-materialized event just re-asserts active and skips materialization.
    The registration form goes live with it (its fields are already on the row)."""
    from app.models.event import Event, EventStatus, EventStage, Round

    payload = approval.payload or {}
    config = payload.get("config") or {}

    event = (
        await db.execute(select(Event).where(Event.id == approval.event_id))
    ).scalars().first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found for event_deploy approval",
        )

    event.status = EventStatus.active
    if event.stage is None:
        event.stage = EventStage.registration
    await db.commit()

    # Materialize rounds/judges/rubric only if not already done (idempotent).
    existing_round = (
        await db.execute(select(Round).where(Round.event_id == event.id).limit(1))
    ).scalars().first()
    if existing_round is None and config:
        from app.routers.ai import _materialize_rounds_judges_rubric

        await db.refresh(event)
        await _materialize_rounds_judges_rubric(db, event, config)
