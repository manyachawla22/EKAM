"""ATS scoring for registrants (Task 6).

`Participant.ats_score` exists in the schema but was never computed anywhere.
This fills it: a 0–100 relevance score of a resume against the event, used by the
organizer (and reusable later by team formation).

Deliberately **deterministic** (keyword/skills overlap + completeness signals)
rather than an LLM call: this runs on an unauthenticated, rate-sensitive endpoint
where a per-request LLM call would add cost, latency, and a DoS surface. An LLM
rubric-based scorer is a clean future upgrade. Best-effort — returns None on
failure and never raises into the request path.
"""

import re
from typing import Any


_STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that", "will", "are", "our",
    "you", "your", "all", "can", "build", "building", "event", "events", "based",
    "using", "into", "out", "via", "per", "any", "who", "how", "what", "where",
    "a", "an", "of", "to", "in", "on", "at", "by", "is", "it", "as", "or",
    "hackathon", "competition", "contest", "challenge", "round", "rounds",
}

# Generic resume-quality signals (presence boosts the score a little).
_COMPLETENESS_HINTS = (
    "experience", "education", "project", "projects", "skills", "internship",
    "certification", "achievement", "award",
)

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z+#.]{2,}")


def _keywords(*texts: str) -> set[str]:
    toks: set[str] = set()
    for t in texts:
        if not t:
            continue
        for w in _WORD_RE.findall(t.lower()):
            w = w.strip(".")
            if len(w) >= 3 and w not in _STOPWORDS:
                toks.add(w)
    return toks


def event_keywords(event: Any) -> set[str]:
    """Build the relevance vocabulary from the event's name/type/description and
    any skills hinted by its registration-form fields."""
    parts = [
        str(getattr(event, "name", "") or ""),
        str(getattr(event, "type", "") or ""),
        str(getattr(event, "description", "") or ""),
    ]
    # Pull labels of skill-ish fields so the vocabulary reflects what's asked for.
    fields = getattr(event, "registration_form_fields", None) or []
    for f in fields:
        if isinstance(f, dict):
            label = f.get("label") or ""
            if any(k in label.lower() for k in ("skill", "tech", "stack", "language", "tool")):
                parts.append(str(label))
                for opt in (f.get("options") or []):
                    parts.append(str(opt))
    return _keywords(*parts)


def score(resume_text: str, event: Any) -> float | None:
    """0–100 relevance score of the resume against the event. None if not scorable."""
    try:
        if not resume_text:
            return None
        text = resume_text.lower()
        kws = event_keywords(event)
        if not kws:
            # No vocabulary to match against — fall back to a pure completeness score.
            present = sum(1 for h in _COMPLETENESS_HINTS if h in text)
            return round(min(present / len(_COMPLETENESS_HINTS) * 100, 100.0), 1)

        hits = sum(1 for k in kws if k in text)
        relevance = hits / len(kws)  # 0..1
        completeness = sum(1 for h in _COMPLETENESS_HINTS if h in text) / len(_COMPLETENESS_HINTS)

        # 80% relevance to the event, 20% generic resume completeness.
        raw = (0.8 * relevance + 0.2 * completeness) * 100
        return round(min(raw, 100.0), 1)
    except Exception:
        return None
