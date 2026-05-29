"""
EKAM CSV Service

Handles parsing and bulk inserting of Participants and Judges from CSV files.
"""

import csv
import io
from typing import List, Dict, Any
from fastapi import HTTPException, status
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
        content = file_content.decode("utf-8")
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
        content = file_content.decode("utf-8")
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
) -> int:
    """Bulk insert participants into DB. Returns count inserted."""
    count = 0
    for data in participants_data:
        p = Participant(
            event_id=event_id,
            name=data["name"],
            email=data["email"],
            organization=data.get("organization"),
            skills=data.get("skills")
        )
        db.add(p)
        count += 1
        
    if count > 0:
        await db.commit()
        
    return count


async def bulk_insert_judges(
    db: AsyncSession,
    event_id: str,
    judges_data: List[Dict[str, Any]]
) -> int:
    """Bulk insert judges into DB. Returns count inserted."""
    count = 0
    for data in judges_data:
        j = Judge(
            event_id=event_id,
            name=data["name"],
            email=data["email"],
            organization=data.get("organization"),
            expertise=data.get("expertise")
        )
        db.add(j)
        count += 1
        
    if count > 0:
        await db.commit()
        
    return count
