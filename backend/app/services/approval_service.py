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
    elif action == ApprovalStatus.rejected and approval.request_type == RequestType.anomaly_review:
        # Rejecting an anomaly review = "not worth considering": dismiss it so it
        # never reaches the judge and the organizer's glow clears (#2/#4).
        from app.services.ml_anomaly_report_service import dispatch_anomaly_review

        anomaly_id = (approval.payload or {}).get("anomaly_id")
        if anomaly_id:
            await dispatch_anomaly_review(db, str(anomaly_id), approved=False)

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

    elif approval.request_type == RequestType.anomaly_review:
        # Organizer confirmed the anomaly is worth considering (#2): now (and
        # only now) notify the judge + organizer and reveal it on the judge page.
        from app.services.ml_anomaly_report_service import dispatch_anomaly_review

        anomaly_id = (approval.payload or {}).get("anomaly_id")
        if anomaly_id:
            await dispatch_anomaly_review(db, str(anomaly_id), approved=True)

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

    # Task 3: persist the approved blueprint onto the event so the GENERIC pipeline
    # activates — `build_steps` reads `event.blueprint` and falls back to the
    # hackathon default only when it's NULL. This is the wire that turns a deployed
    # blueprint into a running blueprint-driven event. Frozen after this point.
    blueprint = payload.get("blueprint")
    if blueprint:
        event.blueprint = blueprint
        # Apply the (possibly EDITED) public registration form from the reviewed
        # blueprint so form edits made on the Blueprint Review screen actually take
        # effect on approval (KI-1). Derives a smart per-format default when the
        # blueprint proposed none. Lazy import (ai.py imports this module).
        try:
            from app.routers.ai import _derive_registration_fields

            event.registration_form_fields = _derive_registration_fields(blueprint)
        except Exception as exc:
            print(f"[approval_service] registration-form derive on deploy failed: {exc}")
    await db.commit()

    # Materialize rounds/judges/rubric only if not already done (idempotent).
    existing_round = (
        await db.execute(select(Round).where(Round.event_id == event.id).limit(1))
    ).scalars().first()
    if existing_round is None:
        await db.refresh(event)
        if blueprint:
            # Blueprint-driven materialization (Task 3): rounds/rubrics straight from
            # the (possibly edited) blueprint so they pair 1:1 with build_steps;
            # judges from config with role labels. Reproduces the hackathon flow for
            # a hackathon blueprint (theme_selection/judge_assignment stages present).
            from app.services.event_generator import generate_from_blueprint

            await generate_from_blueprint(db, event, blueprint, config)
        elif config:
            from app.routers.ai import _materialize_rounds_judges_rubric

            await _materialize_rounds_judges_rubric(db, event, config)

        # Task 3: draft the registration/welcome touchpoint for blueprint events
        # through the existing approval-gated email_batch flow (first deploy only).
        if blueprint:
            try:
                from app.services.communication_service import fire_stage_communications

                await db.refresh(event)
                await fire_stage_communications(db, event, "registration")
            except Exception as exc:
                print(f"[approval_service] deploy welcome communications failed: {exc}")

    # Task 3 (roles-as-labels): when the blueprint defines a single evaluator role
    # (e.g. Reviewer / Investor / Jury), stamp it onto the event's judges. Pure
    # label — same Judge account/permissions; the judging UI shows it. Multi-role
    # per-judge assignment is a later generator enhancement.
    if blueprint:
        try:
            from app.models.judge import Judge

            judge_roles = [r for r in (blueprint.get("roles") or []) if r.get("kind") == "judge"]
            if len(judge_roles) == 1 and (judge_roles[0].get("label") or "").strip():
                label = judge_roles[0]["label"].strip()
                judges = (
                    await db.execute(select(Judge).where(Judge.event_id == event.id))
                ).scalars().all()
                changed = False
                for j in judges:
                    if not j.role_label or j.role_label == "Judge":
                        j.role_label = label
                        changed = True
                if changed:
                    await db.commit()
        except Exception as exc:
            print(f"[approval_service] applying judge role_label failed: {exc}")
