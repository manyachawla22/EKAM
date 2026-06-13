"""Resume parsing for the public registration page (Task 6).

Two responsibilities, both best-effort and non-fatal:
  - extract_text(path): pull text out of an uploaded resume PDF (pdfplumber).
  - parse_resume(text, form_fields): map what we can read onto the event's
    dynamic registration_form_fields, returning a partial {field_id: value} map
    the frontend uses to pre-fill the form. Un-extracted fields stay blank.

Uses Groq/Llama (already wired) for the semantic mapping, with a deterministic
regex fallback for the high-value fields (email / phone / linkedin) so the
feature degrades gracefully when the LLM is unavailable. Never raises.
"""

import asyncio
import json
import re
from typing import Any

import pdfplumber

from app.core.config import settings


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\s\-()]{8,}\d)")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/[^\s)]+", re.I)


def extract_text(path: str) -> str:
    """Extract text from a PDF resume. Returns '' on any failure."""
    try:
        parts: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        return "\n".join(parts).strip()
    except Exception:
        return ""


def _regex_prefill(text: str, form_fields: list[dict]) -> dict[str, Any]:
    """Deterministic fallback: fill email/phone/linkedin/name by field type+id heuristics."""
    out: dict[str, Any] = {}
    email = EMAIL_RE.search(text)
    phone = PHONE_RE.search(text)
    linkedin = LINKEDIN_RE.search(text)

    for f in form_fields:
        if not isinstance(f, dict):
            continue
        fid = f.get("field_id") or ""
        ftype = (f.get("type") or "").lower()
        low = fid.lower()
        label = (f.get("label") or "").lower()
        hay = f"{low} {label}"

        if (ftype == "email" or "email" in hay) and email:
            out[fid] = email.group(0)
        elif (ftype == "tel" or any(k in hay for k in ("phone", "whatsapp", "mobile", "contact"))) and phone:
            out[fid] = phone.group(0).strip()
        elif "linkedin" in hay and linkedin:
            out[fid] = linkedin.group(0)
    return out


def _llm_prefill(text: str, form_fields: list[dict]) -> dict[str, Any]:
    """Ask the LLM to map resume text onto the form fields. Returns {} on any error."""
    try:
        from groq import Groq

        # Trim very long resumes to keep the prompt cheap/fast.
        snippet = text[:6000]
        fields_spec = [
            {
                "field_id": f.get("field_id"),
                "label": f.get("label"),
                "type": f.get("type"),
                "options": f.get("options"),
            }
            for f in form_fields
            if isinstance(f, dict) and f.get("field_id")
        ]
        system = (
            "You extract structured data from a resume to pre-fill a registration "
            "form. Return ONLY a JSON object mapping field_id -> value for fields you "
            "can fill with HIGH confidence from the resume. Omit any field you are "
            "unsure about. For 'select' fields, the value MUST be one of the given "
            "options. Do not invent data. Output JSON only."
        )
        user = (
            f"FORM FIELDS:\n{json.dumps(fields_spec)}\n\n"
            f"RESUME TEXT:\n{snippet}\n\n"
            "Return the JSON object now."
        )
        client = Groq(api_key=settings.GROQ_API_KEY)
        resp = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.0,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        # Keep only known field_ids; drop empties.
        valid_ids = {f.get("field_id") for f in form_fields if isinstance(f, dict)}
        return {
            k: v
            for k, v in data.items()
            if k in valid_ids and v not in (None, "", [], {})
        }
    except Exception:
        return {}


async def parse_resume(text: str, form_fields: list[dict] | None) -> dict[str, Any]:
    """Return a partial {field_id: value} prefill map. Best-effort; never raises."""
    if not text or not form_fields:
        return {}
    try:
        # LLM mapping in a thread (the groq client is sync); regex as the backstop.
        llm = await asyncio.to_thread(_llm_prefill, text, form_fields)
    except Exception:
        llm = {}
    regex = _regex_prefill(text, form_fields)
    # LLM wins where present; regex fills the rest.
    merged = {**regex, **llm}
    return merged
