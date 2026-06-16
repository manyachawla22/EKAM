"""Supabase Storage client for submission/resume PDFs.

Talks to the Storage REST API directly with the service-role key (no `supabase`
SDK dependency — keeps requirements lean and avoids the SDK's sync/async split).

The `submissions` bucket is PUBLIC, so files are served from the public object
URL. That preserves the pre-Supabase UX: links are unguessable (uuid-prefixed
object names) and open in a new browser tab with no auth header.
"""

import requests

from app.core.config import settings


BUCKET = settings.SUPABASE_BUCKET
_BASE = settings.SUPABASE_URL.rstrip("/")


def _auth_headers() -> dict:
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    return {"Authorization": f"Bearer {key}", "apikey": key}


def public_url(object_name: str) -> str:
    """The public URL the frontend opens for a stored object."""
    return f"{_BASE}/storage/v1/object/public/{BUCKET}/{object_name}"


def upload(object_name: str, contents: bytes, content_type: str = "application/pdf") -> str:
    """Upload bytes to the bucket (upsert) and return the public URL.

    Raises RuntimeError on a non-2xx response so callers surface the failure
    instead of silently storing a dead link.
    """
    url = f"{_BASE}/storage/v1/object/{BUCKET}/{object_name}"
    headers = {**_auth_headers(), "Content-Type": content_type, "x-upsert": "true"}
    resp = requests.post(url, headers=headers, data=contents, timeout=30)
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Supabase upload failed ({resp.status_code}) for {object_name}: {resp.text}"
        )
    return public_url(object_name)


def download(object_name: str) -> bytes | None:
    """Fetch an object's bytes (service-role auth works for public or private).
    Returns None if the object is missing or the request fails."""
    url = f"{_BASE}/storage/v1/object/{BUCKET}/{object_name}"
    try:
        resp = requests.get(url, headers=_auth_headers(), timeout=30)
    except requests.RequestException:
        return None
    return resp.content if resp.status_code == 200 else None


def object_name_from_url(url: str | None) -> str | None:
    """Extract the stored object name from any known file-URL form:

    - Supabase public: …/storage/v1/object/public/submissions/<name>
    - Supabase signed: …/storage/v1/object/sign/submissions/<name>?token=…
    - Supabase authed: …/storage/v1/object/submissions/<name>
    - Legacy ngrok:    …/api/v1/submissions/files/<name>
    """
    if not url:
        return None
    for marker in (
        f"/storage/v1/object/public/{BUCKET}/",
        f"/storage/v1/object/sign/{BUCKET}/",
        f"/storage/v1/object/{BUCKET}/",
        "/submissions/files/",
    ):
        idx = url.find(marker)
        if idx != -1:
            name = url[idx + len(marker):].split("?")[0].lstrip("/")
            return name or None
    return None
