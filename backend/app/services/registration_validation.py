"""Validation + normalization for public registrations (Task 6).

Pure helpers so the router stays thin and these are unit-testable:
  - validate_required: ensure required form fields are present in an answer set.
  - extract_identity: map the dynamic answers onto the typed Participant columns
    (name / email / phone / institution) by field-type/id heuristics, so existing
    organizer screens and CSV logic keep working alongside the full registration_data.

Hard gates that need the DB/clock (window, capacity, email-uniqueness) live in the
router; these are the form-shape rules.
"""

from typing import Any

from fastapi import HTTPException, status


def validate_required(form_fields: list[dict] | None, answers: dict[str, Any]) -> None:
    """Raise 422 if any required field is missing/blank in `answers`."""
    for f in (form_fields or []):
        if not isinstance(f, dict):
            continue
        if not f.get("required"):
            continue
        fid = f.get("field_id")
        if not fid:
            continue
        val = answers.get(fid)
        if val is None or (isinstance(val, str) and not val.strip()) or val == []:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Missing required field: {f.get('label') or fid}",
            )


def _match(field: dict, *needles: str) -> bool:
    hay = f"{(field.get('field_id') or '').lower()} {(field.get('label') or '').lower()}"
    return any(n in hay for n in needles)


def extract_identity(form_fields: list[dict] | None, answers: dict[str, Any]) -> dict[str, Any]:
    """Best-effort map of the dynamic answers onto known Participant columns.

    Returns a dict with any of: name, email, phone, institution, skills.
    Falls back to common field_ids when the form is the default set.
    """
    out: dict[str, Any] = {}
    fields = form_fields or []

    for f in fields:
        if not isinstance(f, dict):
            continue
        fid = f.get("field_id")
        if not fid or fid not in answers:
            continue
        val = answers.get(fid)
        if val in (None, "", []):
            continue
        ftype = (f.get("type") or "").lower()

        if "email" not in out and (ftype == "email" or _match(f, "email")):
            out["email"] = val
        elif "name" not in out and _match(f, "full_name", "name", "full name"):
            out["name"] = val
        elif "phone" not in out and (ftype == "tel" or _match(f, "phone", "whatsapp", "mobile", "contact")):
            out["phone"] = val
        elif "institution" not in out and _match(f, "college", "university", "institut", "organization", "organisation", "school"):
            out["institution"] = val
        elif _match(f, "skill", "tech", "stack"):
            if isinstance(val, list):
                out["skills"] = [str(s) for s in val]
            elif isinstance(val, str) and val.strip():
                out["skills"] = [s.strip() for s in val.split(",") if s.strip()]

    # Direct field_id fallbacks for the default form set.
    out.setdefault("email", answers.get("email"))
    out.setdefault("name", answers.get("full_name") or answers.get("name"))
    out.setdefault("phone", answers.get("phone"))
    out.setdefault("institution", answers.get("college") or answers.get("institution"))

    # Drop None values.
    return {k: v for k, v in out.items() if v not in (None, "", [])}
