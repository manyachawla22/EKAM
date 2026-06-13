"""Shared PDF storage helper.

Extracted from routers/submissions.py so both the (auth-gated) submission upload
and the (public) resume upload write files the same way: PDF-only, ≤25 MB, stored
under uploads/submissions/ with an unguessable uuid-prefixed name, and served
unauthenticated from /submissions/files/{name}.
"""

import os
import re
import uuid

from fastapi import HTTPException, status

from app.core.config import settings


# Where uploaded PDFs live on the local machine (shared with submissions).
SUBMISSIONS_DIR = os.path.join(settings.UPLOAD_DIR, "submissions")

ALLOWED_CONTENT_TYPES = {"application/pdf"}
MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MB


def public_base_url(request_base_url: str | None = None) -> str:
    """Base URL for absolute file links. Prefers settings.PUBLIC_BASE_URL (ngrok),
    falling back to the host the request came in on."""
    configured = (settings.PUBLIC_BASE_URL or "").strip().rstrip("/")
    if configured:
        return configured
    return (request_base_url or "").rstrip("/")


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


def store_pdf(contents: bytes, filename: str, base_url: str) -> dict:
    """Persist a validated PDF and return {url, filename (stored), name (display), path}.

    The stored name is uuid-prefixed (unguessable) so the unauthenticated download
    endpoint can serve it by link only.
    """
    os.makedirs(SUBMISSIONS_DIR, exist_ok=True)

    display_name = safe_name(filename)
    stored_name = f"{uuid.uuid4().hex}_{display_name}"
    stored_path = os.path.join(SUBMISSIONS_DIR, stored_name)

    with open(stored_path, "wb") as out:
        out.write(contents)

    url = (
        f"{base_url}{settings.API_V1_STR}/submissions/files/{stored_name}"
    )
    return {"url": url, "filename": stored_name, "name": display_name, "path": stored_path}


def local_path_for_url(url: str) -> str | None:
    """Map a stored-file URL (…/submissions/files/<name>) back to its local path,
    if the file exists. Used to re-read a resume for ATS scoring. Returns None
    for anything that isn't a known local upload."""
    if not url:
        return None
    marker = "/submissions/files/"
    idx = url.find(marker)
    if idx == -1:
        return None
    name = os.path.basename(url[idx + len(marker):].split("?")[0])
    path = os.path.join(SUBMISSIONS_DIR, name)
    return path if os.path.isfile(path) else None
