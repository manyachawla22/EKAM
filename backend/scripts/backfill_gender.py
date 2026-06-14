"""
One-off backfill: populate participants.gender from a participants CSV.

Background: parse_participant_csv used to drop the `gender` column, so any
participant imported via CSV before that fix has gender = NULL. This script
reads the CSV and fills gender by matching on email (only where it's currently
empty, so it never clobbers data entered through the public registration page).

Run from the backend directory (so .env loads):
    python scripts/backfill_gender.py ../participants.csv
Defaults to ../participants.csv when no path is given.
"""

import asyncio
import csv
import io
import sys
from pathlib import Path

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.participant import Participant


def read_gender_by_email(csv_path: Path) -> dict[str, str]:
    # utf-8-sig strips a leading BOM (Excel/Sheets add one) so the first header
    # isn't mangled — same handling as the live CSV import path.
    content = csv_path.read_bytes().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))

    mapping: dict[str, str] = {}
    for row in reader:
        row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        email = (row.get("email") or "").lower()
        gender = row.get("gender") or None
        if email and gender:
            mapping[email] = gender
    return mapping


async def backfill(csv_path: Path) -> None:
    gender_by_email = read_gender_by_email(csv_path)
    if not gender_by_email:
        print("No (email, gender) pairs found in CSV — nothing to do.")
        return

    print(f"Read {len(gender_by_email)} gender values from {csv_path}")

    updated = 0
    skipped_no_match = 0
    skipped_has_gender = 0

    async with AsyncSessionLocal() as db:
        for email, gender in gender_by_email.items():
            # Match across events; email is the participant's identity. There may
            # be more than one row if the same person registered for several events.
            result = await db.execute(
                select(Participant).where(Participant.email.ilike(email))
            )
            participants = result.scalars().all()

            if not participants:
                skipped_no_match += 1
                print(f"  no participant for {email}")
                continue

            for p in participants:
                if p.gender:
                    skipped_has_gender += 1
                    continue
                p.gender = gender
                updated += 1
                print(f"  {email} -> {gender}")

        if updated:
            await db.commit()

    print(
        f"\nDone. updated={updated} "
        f"already_had_gender={skipped_has_gender} no_match={skipped_no_match}"
    )


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../participants.csv")
    if not path.exists():
        sys.exit(f"CSV not found: {path.resolve()}")
    asyncio.run(backfill(path))
