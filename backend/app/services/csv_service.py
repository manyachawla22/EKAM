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


def parse_participant_csv(file_content: bytes) -> List[Dict[str, Any]]:
    """
    Parses a CSV file containing participant data.
    Expected columns (case-insensitive):
    - name (required)
    - email (required)
    - organization / institution (optional)
    - gender (optional)
    - experience_level (optional)
    - skills (optional, comma-separated)
    """
    try:
        # utf-8-sig strips a leading BOM (Excel/Sheets add one). Without this,
        # the first header — usually "name" — becomes "﻿name", so every
        # row is missing its required field and is silently skipped (0 imported).
        content = file_content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content))
        
        participants_data = []
        for row in reader:
            # normalize keys
            row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
            
            name = row.get("name")
            email = row.get("email")
            
            if not name or not email:
                continue # skip invalid rows
                
            skills_str = row.get("skills", "")
            skills = [s.strip() for s in skills_str.split(",")] if skills_str else []
            
            participants_data.append({
                "name": name,
                "email": email,
                "organization": row.get("organization") or row.get("institution"),
                "gender": row.get("gender") or None,
                # We extract generic properties that could map to custom logic later
                "skills": skills,
            })
            
        return participants_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse CSV: {str(e)}"
        )


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
            skills=data.get("skills") or [],
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
