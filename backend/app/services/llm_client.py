"""
EKAM LLM seam (Task 3).

A thin, provider-agnostic boundary for the Task-3 intelligence calls (critic +
blueprint synthesis). Everything else in the app keeps calling Groq directly;
only Task-3 goes through here, so the critic/synthesis calls can be pointed at
Claude later via ONE config flag without touching call sites.

Default provider = Groq/Llama (already wired, no new key/billing). To switch the
agent/critic to a stronger model, set in the environment / settings:

    # Gemini 2.0 Flash — FREE tier, best free structured-extraction quality.
    # Needs:  pip install google-genai
    LLM_PROVIDER=gemini
    GEMINI_API_KEY=...                 # free key from https://aistudio.google.com

    # …or Claude (pay-as-you-go; not free):
    LLM_PROVIDER=anthropic
    ANTHROPIC_API_KEY=sk-ant-...
    LLM_MODEL=claude-sonnet-4-6        # optional explicit model override

The deterministic checks in event_validator.py are model-independent and remain
the hard gate regardless of which provider answers here.
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional

from app.core.config import settings


# Groq fallbacks mirror routers/ai.py so behaviour is consistent app-wide.
# NOTE: keep these to CURRENT Groq production models. `llama3-8b-8192` AND
# `gemma2-9b-it` are both decommissioned (400 model_decommissioned) — a dead model
# here silently kills the whole Gemini→Groq fallback chain, so extraction returns
# an empty blueprint whenever Gemini is busy/quota'd (caught by
# scripts/eval_blueprints.py). The Scout model is the same one used as a primary in
# routers/ai._MODELS, so it's a known-good backstop.
_GROQ_FALLBACKS = ["llama-3.1-8b-instant", "meta-llama/llama-4-scout-17b-16e-instruct"]


def _cfg(name: str, default=None):
    return getattr(settings, name, None) or default


def _extract_json(raw: str) -> dict:
    """Best-effort JSON parse: whole string first, then the outermost {...}."""
    raw = (raw or "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
        raise


# ── Groq backend ──────────────────────────────────────────────────────────────

def _groq_json_sync(system: str, user: str, model: str, max_tokens: int) -> dict:
    from groq import Groq

    client = Groq(api_key=_cfg("GROQ_API_KEY"))
    models = [model] + [m for m in _GROQ_FALLBACKS if m != model]
    last_err: Exception = RuntimeError("no model attempted")
    for m in models:
        try:
            resp = client.chat.completions.create(
                model=m,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.1,          # low-temp: the critic must be stable
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            return _extract_json(resp.choices[0].message.content or "")
        except Exception as e:  # try the next fallback model
            last_err = e
            continue
    raise RuntimeError(f"Groq JSON call failed: {last_err}") from last_err


# ── Gemini backend (optional, behind config) — free tier, strong extraction ──

def _gemini_keys() -> list[str]:
    """The Gemini key pool: GEMINI_API_KEYS (comma-separated) ∪ GEMINI_API_KEY,
    de-duped, order preserved. Each free-tier key from a SEPARATE project carries
    its own 20 req/day quota, so a pool multiplies daily capacity."""
    raw = (_cfg("GEMINI_API_KEYS", "") or "")
    keys = [k.strip() for k in raw.replace("\n", ",").split(",") if k.strip()]
    single = (_cfg("GEMINI_API_KEY", "") or "").strip()
    if single:
        keys.append(single)
    seen: set[str] = set()
    out: list[str] = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


# Rotating start cursor so load spreads across the pool instead of always burning
# key #1 first (which would hit its daily cap while later keys sit idle).
_gemini_cursor = 0


def _is_quota_or_overload(exc: Exception) -> bool:
    s = str(exc).lower()
    return any(t in s for t in ("429", "resource_exhausted", "quota", "503", "unavailable", "rate limit"))


def _gemini_json_sync(system: str, user: str, model: str, max_tokens: int) -> dict:
    # New unified Google SDK: `pip install google-genai`. Imported lazily so the
    # dependency is only required when the provider is actually selected.
    global _gemini_cursor
    from google import genai
    from google.genai import types

    keys = _gemini_keys()
    if not keys:
        raise RuntimeError("No Gemini API key configured")

    cfg_kwargs = dict(
        system_instruction=system,
        temperature=0.1,                     # low-temp: stable structured output
        max_output_tokens=max_tokens,
        response_mime_type="application/json",
    )
    # Gemini 2.5 models "think" by default — those reasoning tokens count against
    # max_output_tokens and can TRUNCATE the JSON (parse error → fallback). For
    # structured extraction we don't want thinking, so disable it when supported.
    try:
        cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    except Exception:
        pass

    last_err: Exception | None = None
    start = _gemini_cursor
    _gemini_cursor = (_gemini_cursor + 1) % len(keys)
    # Try each key once, starting at the rotating cursor. A quota/overload error
    # rotates to the NEXT key; any other error (or running out of keys) propagates
    # so complete_json() can fall back to Groq.
    for off in range(len(keys)):
        key = keys[(start + off) % len(keys)]
        try:
            client = genai.Client(api_key=key)
            resp = client.models.generate_content(
                model=model, contents=user,
                config=types.GenerateContentConfig(**cfg_kwargs),
            )
            return _extract_json(resp.text or "")
        except Exception as exc:
            last_err = exc
            if _is_quota_or_overload(exc) and off < len(keys) - 1:
                continue        # this key is tapped out / busy — try the next one
            raise
    raise last_err if last_err else RuntimeError("Gemini call failed")


# ── Anthropic backend (optional, behind config) ──────────────────────────────

def _anthropic_json_sync(system: str, user: str, model: str, max_tokens: int) -> dict:
    import anthropic  # only imported if the provider is actually selected

    client = anthropic.Anthropic(api_key=_cfg("ANTHROPIC_API_KEY"))
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=0.1,
        system=system + "\n\nReturn ONLY a single valid JSON object. No prose, no fences.",
        messages=[{"role": "user", "content": user}],
    )
    parts = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
    return _extract_json("".join(parts))


# ── Public API ────────────────────────────────────────────────────────────────

def provider() -> str:
    return (_cfg("LLM_PROVIDER", "groq") or "groq").strip().lower()


def default_model() -> str:
    explicit = (_cfg("LLM_MODEL") or "").strip()
    if explicit:
        return explicit
    p = provider()
    if p == "anthropic":
        return "claude-sonnet-4-6"
    if p == "gemini":
        return "gemini-2.5-flash"
    return _cfg("GROQ_MODEL", "llama-3.3-70b-versatile")


async def complete_json(
    system: str,
    user: str,
    *,
    model: Optional[str] = None,
    max_tokens: int = 1200,
) -> dict:
    """Run a JSON-mode completion off the event loop. Raises on hard failure;
    callers (the critic) degrade gracefully so the LLM is never a hard gate."""
    model = model or default_model()
    p = provider()
    groq_model = _cfg("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Try the selected provider first. If it fails at RUNTIME (e.g. a Gemini 429
    # quota error, a transient outage) AND a Groq key is available, fall back to
    # Groq so the agent/critic keep working — degraded, never down. A missing key
    # skips straight to the fallback (no wasted call).
    try:
        if p == "anthropic" and _cfg("ANTHROPIC_API_KEY"):
            return await asyncio.to_thread(_anthropic_json_sync, system, user, model, max_tokens)
        if p == "gemini" and _gemini_keys():
            return await asyncio.to_thread(_gemini_json_sync, system, user, model, max_tokens)
    except Exception as exc:
        if p != "groq" and _cfg("GROQ_API_KEY"):
            print(f"[llm_client] {p} call failed ({exc}); falling back to Groq.")
            return await asyncio.to_thread(_groq_json_sync, system, user, groq_model, max_tokens)
        raise

    # Default provider is Groq, or the selected provider's key is missing.
    return await asyncio.to_thread(
        _groq_json_sync, system, user, model if p == "groq" else groq_model, max_tokens,
    )


def is_available() -> bool:
    """True when the selected provider (or the Groq fallback) has a usable key."""
    p = provider()
    if p == "anthropic" and _cfg("ANTHROPIC_API_KEY"):
        return True
    if p == "gemini" and _gemini_keys():
        return True
    return bool(_cfg("GROQ_API_KEY"))
