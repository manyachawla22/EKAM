"""
EKAM CSV Service

Handles parsing and bulk inserting of Participants and Judges from CSV files.
"""

import csv
import io
from typing import List, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.participant import Participant
from app.models.judge import Judge


# Header keywords → typed Participant column. The first column whose normalized
# header contains any of these keywords maps onto the typed field; EVERY column is
# additionally preserved verbatim in registration_data so nothing is ever dropped.
_NAME_KEYS = ("name", "full name", "full_name")
_EMAIL_KEYS = ("email", "e-mail")
_ORG_KEYS = ("organization", "organisation", "institution", "college", "university", "school", "company")
_GENDER_KEYS = ("gender", "sex")
_PHONE_KEYS = ("phone", "mobile", "contact", "whatsapp")
_AGE_KEYS = ("age",)
_SKILL_KEYS = ("skill", "tech", "stack")


def _first_matching(row: Dict[str, str], keys) -> Any:
    """Value of the first column whose header contains one of `keys`."""
    for header, value in row.items():
        if any(k in header for k in keys):
            if value not in (None, ""):
                return value
    return None


def parse_participant_csv(file_content: bytes) -> List[Dict[str, Any]]:
    """
    Parses a CSV file containing participant data.

    Maps known columns (case-insensitive, keyword-matched on the header) onto the
    typed Participant columns — name, email, organization/institution, gender,
    phone, age, skills — AND preserves the full row in `registration_data` so any
    event-specific question the organizer added to the sample CSV is captured too.
    Only `name` and `email` are required; other columns are optional.
    """
    try:
        # utf-8-sig strips a leading BOM (Excel/Sheets add one). Without this,
        # the first header — usually "name" — becomes "﻿name", so every
        # row is missing its required field and is silently skipped (0 imported).
        content = file_content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content))

        participants_data = []
        for row in reader:
            # normalize keys + values
            row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}

            name = _first_matching(row, _NAME_KEYS) or row.get("name")
            email = _first_matching(row, _EMAIL_KEYS) or row.get("email")

            if not name or not email:
                continue  # skip invalid rows

            skills_str = _first_matching(row, _SKILL_KEYS) or ""
            skills = [s.strip() for s in skills_str.split(",") if s.strip()] if skills_str else []

            age_raw = _first_matching(row, _AGE_KEYS)
            age = None
            if age_raw:
                try:
                    age = int(float(str(age_raw).strip()))
                except (TypeError, ValueError):
                    age = None

            participants_data.append({
                "name": name,
                "email": email,
                "organization": _first_matching(row, _ORG_KEYS),
                "gender": _first_matching(row, _GENDER_KEYS),
                "phone": _first_matching(row, _PHONE_KEYS),
                "age": age,
                "skills": skills,
                # Keep the complete row so event-specific fields aren't lost.
                "registration_data": dict(row),
            })

        return participants_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse CSV: {str(e)}"
        )


def generate_participant_sample_csv(event) -> str:
    """Build a CSV template whose columns match THIS event's registration
    requirements (#3), so the organizer fills exactly the fields the event needs
    and the importer can populate them. Always includes name/email/gender/skills
    (gender drives team formation, skills drive matching), then appends any other
    fields the organizer defined on the event's registration form.
    """
    # Base columns the importer maps onto typed Participant fields.
    headers: List[str] = ["name", "email", "gender", "phone", "organization", "skills"]
    seen = {h.lower() for h in headers}

    for f in (getattr(event, "registration_form_fields", None) or []):
        if not isinstance(f, dict):
            continue
        label = (f.get("label") or f.get("field_id") or "").strip()
        if not label:
            continue
        if label.lower() in seen:
            continue
        # Skip the ones already covered by a base column (name/email/etc.).
        hay = f"{(f.get('field_id') or '').lower()} {label.lower()}"
        if any(k in hay for k in _NAME_KEYS + _EMAIL_KEYS + _GENDER_KEYS + _PHONE_KEYS + _ORG_KEYS + _SKILL_KEYS):
            continue
        headers.append(label)
        seen.add(label.lower())

    # Two illustrative example rows so the format is unambiguous.
    examples = [
        {"name": "Asha Verma", "email": "asha@example.com", "gender": "Female",
         "phone": "9876543210", "organization": "IIT Bombay", "skills": "Python, ML"},
        {"name": "Rahul Nair", "email": "rahul@example.com", "gender": "Male",
         "phone": "9123456780", "organization": "NIT Trichy", "skills": "React, Node"},
    ]

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers)
    writer.writeheader()
    for ex in examples:
        writer.writerow({h: ex.get(h, "") for h in headers})
    return buf.getvalue()


def parse_judge_csv(file_content: bytes) -> List[Dict[str, Any]]:
    """
    Parses a CSV file containing judge data.
    Expected columns (case-insensitive):
    - name (required)
    - email (required)
    - organization / institution (optional)
    - expertise (optional, comma-separated)
    """
    try:
        # utf-8-sig strips a leading BOM (Excel/Sheets add one). Without this,
        # the first header — usually "name" — becomes "﻿name", so every
        # row is missing its required field and is silently skipped (0 imported).
        content = file_content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content))
        
        judges_data = []
        for row in reader:
            row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
            
            name = row.get("name")
            email = row.get("email")
            
            if not name or not email:
                continue
                
            expertise_str = row.get("expertise", "")
            expertise = [e.strip() for e in expertise_str.split(",")] if expertise_str else []
            
            judges_data.append({
                "name": name,
                "email": email,
                "organization": row.get("organization") or row.get("institution"),
                "expertise": expertise,
            })
            
        return judges_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse CSV: {str(e)}"
        )


async def bulk_insert_participants(
    db: AsyncSession,
    event_id: str,
    participants_data: List[Dict[str, Any]]
) -> Dict[str, int]:
    """
    Bulk insert participants. Skips rows whose email already exists for this
    event or repeats within the file, so re-uploading the same CSV is safe and
    never trips the unique (event_id, email) constraint.
    Returns {"inserted": n, "skipped": m}.
    """
    existing = await db.execute(
        select(Participant.email).where(Participant.event_id == event_id)
    )
    seen = {e.lower() for (e,) in existing.all() if e}

    inserted = 0
    skipped = 0
    for data in participants_data:
        email = (data.get("email") or "").strip()
        if not email or email.lower() in seen:
            skipped += 1
            continue
        seen.add(email.lower())
        db.add(Participant(
            event_id=event_id,
            name=data["name"],
            email=email,
            institution=data.get("organization"),  # CSV uses 'organization', model uses 'institution'
            gender=data.get("gender"),
            phone=data.get("phone"),
            age=data.get("age"),
            skills=data.get("skills") or [],
            registration_data=data.get("registration_data"),
        ))
        inserted += 1

    if inserted > 0:
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to import participants (a row may conflict with existing data).",
            )

    return {"inserted": inserted, "skipped": skipped}


async def bulk_insert_judges(
    db: AsyncSession,
    event_id: str,
    judges_data: List[Dict[str, Any]]
) -> Dict[str, int]:
    """
    Bulk insert judges. Skips rows whose email already exists for this event or
    repeats within the file, so re-uploading the same CSV is safe and never
    trips the unique (event_id, email) constraint.
    Returns {"inserted": n, "skipped": m}.
    """
    existing = await db.execute(
        select(Judge.email).where(Judge.event_id == event_id)
    )
    seen = {e.lower() for (e,) in existing.all() if e}

    inserted = 0
    skipped = 0
    for data in judges_data:
        email = (data.get("email") or "").strip()
        if not email or email.lower() in seen:
            skipped += 1
            continue
        seen.add(email.lower())
        db.add(Judge(
            event_id=event_id,
            name=data["name"],
            email=email,
            institution=data.get("organization"),  # CSV uses 'organization', model uses 'institution'
            expertise=data.get("expertise") or [],
        ))
        inserted += 1

    if inserted > 0:
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to import judges (a row may conflict with existing data).",
            )

    return {"inserted": inserted, "skipped": skipped}
