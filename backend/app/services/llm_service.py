"""Lightweight, reusable Groq JSON-completion helper.

Both the team-formation rationale and the judge assessment-guide features need
the same thing: ask an LLM for a small structured JSON object, and fall back
gracefully when the key is missing or the call fails. This keeps that logic in
one place instead of duplicating the Groq plumbing that lives in routers/ai.py.

`complete_json` returns ``None`` on any failure (no key, rate limit, unparseable
output) so callers can substitute a deterministic fallback.
"""

import asyncio
import json
import re
from typing import Optional

from app.core.config import settings

# Mirror the model preference used by the AI event chatbot.
_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama3-8b-8192",
]


def _parse_json(raw: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    text = re.sub(r"\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("Unbalanced JSON object")


def _complete_sync(system: str, context: str, max_tokens: int) -> dict:
    from groq import Groq

    client = Groq(api_key=settings.GROQ_API_KEY)
    last_err: Exception = RuntimeError("no models tried")
    for model in _MODELS:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": context},
                ],
                temperature=0.3,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            return _parse_json(resp.choices[0].message.content or "")
        except Exception as e:  # rate limit, truncation, parse error → next model
            last_err = e
            continue
    raise last_err


async def complete_json(
    system: str, context: str, max_tokens: int = 1200
) -> Optional[dict]:
    """Return a parsed JSON object from the LLM, or ``None`` if unavailable."""
    if not settings.GROQ_API_KEY:
        return None
    try:
        return await asyncio.to_thread(_complete_sync, system, context, max_tokens)
    except Exception as e:
        print(f"[llm_service] completion failed: {type(e).__name__}: {e}")
        return None
