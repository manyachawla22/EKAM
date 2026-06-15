"""
EKAM generic communication service (Task 3, Stage 3b — Automated Communications).

Fires a blueprint event's `communications[]` touchpoints when the pipeline enters
a stage. Each touchpoint is AI-drafted from the blueprint context and routed
through the **existing approval-gated email pipeline**:

    draft_bulk_emails  →  email_batch ApprovalRequest  →  organizer reviews/edits
    in ApprovalEditor  →  execute_approved_email_batch sends (with per-recipient
    magic-link injection + the existing throttle/retry).

So EKAM's human-in-the-loop, per-stage email approval is **preserved** for
blueprint events — there is NO send-without-approval path here (decision §13.6).
Legacy hackathon events keep using `email_triggers`; blueprint events use this
generic path. Best-effort throughout: a drafting failure never blocks the pipeline.
"""

from __future__ import annotations

from typing import List

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email import EmailType
from app.models.judge import Judge
from app.models.participant import Participant


def _resolve_role(blueprint: dict, role_id) -> dict | None:
    for r in (blueprint.get("roles") or []):
        if r.get("id") == role_id:
            return r
    return None


def _email_type_for(trigger: str, step_id: str) -> EmailType:
    t = (trigger or "") + " " + (step_id or "")
    if "registration" in t:
        return EmailType.invitation
    if "winner" in t:
        return EmailType.result
    if "advancement" in t or "progression" in t:
        return EmailType.progression
    return EmailType.stage_update


def _stage_ids_for_step(blueprint: dict, rounds: list, step_id: str) -> set[str]:
    """Reverse of build_steps: the blueprint stage id(s) whose pipeline step is
    `step_id`. Used to match a touchpoint's `trigger` (a blueprint stage id) to the
    pipeline step just entered. Mirrors `_build_steps_from_blueprint` exactly."""
    from app.services.pipeline_service import _blueprint_round_groups

    stages = blueprint.get("stages") or []
    mapping: dict[str, str] = {}  # stage_id -> step_id
    groups = _blueprint_round_groups(stages)
    for i, g in enumerate(groups):
        if i >= len(rounds):
            break
        rid = str(rounds[i].id)
        if g["submission"]:
            mapping[g["submission"].get("id", "")] = f"round:{rid}:submission"
        mapping[g["evaluation"].get("id", "")] = f"round:{rid}:evaluation"
        if g["progression"]:
            mapping[g["progression"].get("id", "")] = f"round:{rid}:advancement"
    for s in stages:
        sid = s.get("id") or ""
        if sid in mapping:
            continue
        t = (s.get("type") or "").lower()
        if t == "registration":
            mapping[sid] = "registration"
        elif t == "team_formation":
            mapping[sid] = "team_formation"
        elif t == "entry_formation":
            mapping[sid] = "entry_formation"
        elif t in ("progression", "bracket") and (s.get("rule") or {}).get("kind") == "winners":
            mapping[sid] = "winner_announcement"
        elif t == "communication":
            continue
        else:
            mapping[sid] = f"custom:{sid}"
    return {sid for sid, st in mapping.items() if st == step_id}


async def _recipients_for_role(db: AsyncSession, event, blueprint: dict, role_id) -> List[str]:
    role = _resolve_role(blueprint, role_id)
    kind = (role or {}).get("kind", "participant")
    if kind == "judge":
        rows = (await db.execute(
            select(Judge.email).where(Judge.event_id == event.id)
        )).scalars().all()
    else:
        rows = (await db.execute(
            select(Participant.email).where(Participant.event_id == event.id)
        )).scalars().all()
    # de-dup, drop blanks
    seen, out = set(), []
    for e in rows:
        if e and e.lower() not in seen:
            seen.add(e.lower())
            out.append(e)
    return out


async def fire_post_registration(db: AsyncSession, event) -> int:
    """When the pipeline LEAVES registration, propose an approval-gated welcome /
    confirmation email to every registered participant (with their magic link) so
    they can reach their dashboard.

    This is essential for **preformed-team** and **individual** events: they have no
    team-formation step, so nothing else would ever email the participants. (The
    blueprint's "registration" touchpoint fires at DEPLOY, when nobody has signed up
    yet — useless as the actual participant outreach.) Approval-gated like every
    other batch (organizer reviews/edits/sends in the Approvals panel); no direct
    send. Blueprint events only; best-effort — never blocks the pipeline."""
    blueprint = getattr(event, "blueprint", None)
    if not blueprint:
        return 0
    try:
        from app.email_triggers import draft_email_content
        from app.services.email_service import draft_bulk_emails

        rows = (await db.execute(
            select(Participant.email).where(Participant.event_id == event.id)
        )).scalars().all()
        seen, recipients = set(), []
        for e in rows:
            if e and e.lower() not in seen:
                seen.add(e.lower())
                recipients.append(e)
        if not recipients:
            return 0

        context = {
            "event_name": event.name,
            "role": "participant",
            "message": (
                f"You're registered for {event.name}! Log in to EKAM with the link "
                "below to see your dashboard, the schedule, and your next steps."
            ),
        }
        content = await draft_email_content("invitation", context)
        await draft_bulk_emails(
            db=db,
            event_id=str(event.id),
            requested_by=str(event.organizer_id),
            email_type=EmailType.invitation,
            subject=content["subject"],
            body_html=content["body_html"],
            recipients=recipients,
            body_text=content["body_text"],
        )
        print(f"[communication_service] proposed post-registration welcome to "
              f"{len(recipients)} participant(s) for {event.name}")
        return 1
    except Exception as exc:  # never block the pipeline
        print(f"[communication_service] post-registration draft failed (ignored): {exc}")
        return 0


async def fire_stage_communications(db: AsyncSession, event, step_id: str) -> int:
    """Draft (approval-gated) every communication whose trigger matches the stage
    just entered. Returns how many email batches were drafted. Blueprint events
    only; no-op otherwise. Never raises into the caller."""
    blueprint = getattr(event, "blueprint", None)
    if not blueprint:
        return 0
    comms = blueprint.get("communications") or []
    if not comms:
        return 0

    try:
        from app.services.pipeline_service import _ordered_rounds
        from app.email_triggers import draft_email_content
        from app.services.email_service import draft_bulk_emails

        rounds = await _ordered_rounds(db, event.id)
        triggers = _stage_ids_for_step(blueprint, rounds, step_id) | {step_id}
        matching = [c for c in comms if (c.get("trigger") or "") in triggers]
        if not matching:
            return 0

        # Stage label for nicer copy (best-effort).
        label_by_stage = {s.get("id"): s.get("label") for s in (blueprint.get("stages") or [])}
        stage_label = next((label_by_stage.get(t) for t in triggers if label_by_stage.get(t)), step_id)

        fired = 0
        for c in matching:
            recipients = await _recipients_for_role(db, event, blueprint, c.get("to_role"))
            if not recipients:
                continue
            role = _resolve_role(blueprint, c.get("to_role")) or {}
            context = {
                "event_name": event.name,
                "role": role.get("label", "participant"),
                "message": (
                    f"An update for the '{stage_label}' phase of {event.name}. "
                    "Please log in to EKAM for details and next steps."
                ),
            }
            content = await draft_email_content("stage_update", context)
            await draft_bulk_emails(
                db=db,
                event_id=str(event.id),
                requested_by=str(event.organizer_id),
                email_type=_email_type_for(c.get("trigger") or "", step_id),
                subject=content["subject"],
                body_html=content["body_html"],
                recipients=recipients,
                body_text=content["body_text"],
            )
            fired += 1
        if fired:
            print(f"[communication_service] drafted {fired} approval-gated batch(es) for step {step_id}")
        return fired
    except Exception as exc:  # never block the pipeline on comms
        print(f"[communication_service] fire failed for {step_id} (ignored): {exc}")
        return 0
