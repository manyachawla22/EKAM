"""Shared PDF storage helper (Supabase Storage).

Both the (auth-gated) submission upload and the (public) resume upload write
files the same way: PDF-only, ≤25 MB, uploaded to the Supabase `submissions`
bucket under an unguessable uuid-prefixed object name, and served from the
bucket's public object URL.

Previously these PDFs lived on the local disk under uploads/submissions/ and were
served through ngrok at /submissions/files/{name}; that is gone. `read_pdf_bytes`
re-fetches a stored PDF for server-side reuse (resume ATS scoring, quiz grading).
"""

import os
import re
import uuid

from fastapi import HTTPException, status

from app.services import supabase_storage


ALLOWED_CONTENT_TYPES = {"application/pdf"}
MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MB


def safe_name(filename: str) -> str:
    """Strip a filename down to a safe .pdf basename."""
    base = os.path.basename(filename or "file.pdf")
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", base).strip("_") or "file.pdf"
    if not cleaned.lower().endswith(".pdf"):
        cleaned += ".pdf"
    return cleaned


def validate_pdf(content_type: str | None, contents: bytes) -> None:
    """Raise HTTPException unless `contents` is a non-empty PDF within the size cap."""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed.",
        )
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    if len(contents) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (max 25 MB).",
        )


def store_pdf(contents: bytes, filename: str) -> dict:
    """Upload a validated PDF to Supabase Storage.

    Returns {url, filename (stored object name), name (display name)}. The stored
    name is uuid-prefixed (unguessable) so the public bucket link is link-only.
    """
    display_name = safe_name(filename)
    stored_name = f"{uuid.uuid4().hex}_{display_name}"
    url = supabase_storage.upload(stored_name, contents)
    return {"url": url, "filename": stored_name, "name": display_name}


def read_pdf_bytes(url_or_name: str | None) -> bytes | None:
    """Re-fetch a stored PDF's bytes from Supabase, given its public URL or its
    object name. Used to re-read a resume/answer PDF for scoring. Returns None for
    anything that isn't a known stored file (e.g. a GitHub/demo link)."""
    if not url_or_name:
        return None
    name = supabase_storage.object_name_from_url(url_or_name)
    if name is None:
        # Already a bare object name (no recognizable URL markers)?
        name = url_or_name if "/" not in url_or_name else None
    if not name:
        return None
    return supabase_storage.download(name)
