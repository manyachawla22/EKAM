from typing import List

# Minimal stub service for email draft support.
# This keeps email_triggers.py compatible while allowing the certificate flow to send emails directly.

async def draft_bulk_emails(
    db,
    event_id: str,
    requested_by: str,
    email_type,
    subject: str,
    body_html: str,
    body_text: str,
    recipients: List[str],
):
    # If you later want to persist drafts, add a database model and save here.
    print(f"Drafting {len(recipients)} {email_type} emails for event {event_id}")
    return recipients
