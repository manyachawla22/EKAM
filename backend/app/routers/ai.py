import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import groq as _groq
from groq import Groq
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.auth_context import AuthContext
from app.core.utils import generate_event_hash
from app.middleware.auth import require_actor_type
from app.models.event import (
    Event as EventModel,
    EventStage,
    EventStatus,
    TeamFormationType,
    Round as RoundModel,
    RoundStatus,
)
from app.models.judge import Judge as JudgeModel
from app.models.rubric import RubricCriterion
from app.models.theme import Theme as ThemeModel
from app.services.csv_service import parse_participant_csv, parse_judge_csv

router = APIRouter()

# India Standard Time is a fixed +05:30 offset (no DST), so we model it as a
# constant offset rather than zoneinfo("Asia/Kolkata") — the latter needs the
# IANA tz database, which isn't present on Windows without the `tzdata` package.
IST = timezone(timedelta(hours=5, minutes=30))

# Every /ai/* endpoint that creates or mutates event data is organizer/admin
# only — the rest of EKAM is behind event-scoped RBAC and this router was the
# one open door. The frontend already sends the organizer's bearer token here.
_organizer_only = Depends(require_actor_type(["organizer", "admin"]))

# Per-event async locks serialize read-modify-write on the JSON files so two
# concurrent requests for the same event can't clobber each other's changes.
# Different events still proceed in parallel.
_event_locks: Dict[str, asyncio.Lock] = {}
_event_locks_guard = asyncio.Lock()
_index_lock = asyncio.Lock()


async def _event_lock(event_id: str) -> asyncio.Lock:
    async with _event_locks_guard:
        lock = _event_locks.get(event_id)
        if lock is None:
            lock = asyncio.Lock()
            _event_locks[event_id] = lock
        return lock


def _is_uuid(value: Any) -> bool:
    """True only for a well-formed UUID string. Used to reject event_ids that
    could escape the data directory via path traversal (e.g. '..')."""
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


_MODELS = ["llama-3.3-70b-versatile", "meta-llama/llama-4-scout-17b-16e-instruct"]
_FALLBACK_MODELS = ["llama-3.1-8b-instant", "llama3-8b-8192"]
_counter = 0


def _next_model() -> str:
    global _counter
    m = _MODELS[_counter % len(_MODELS)]
    _counter += 1
    return m


def _today() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d")


# ── Section system prompts ─────────────────────────────────────────────────────

def _sec1_system() -> str:
    today = _today()
    return f"""Extract core event details, timeline, and participant structure from the organizer's message.
Return ONLY valid JSON — no markdown, no prose.
Include ONLY fields you can confidently extract. Omit unknown fields entirely.
Extract team formation constraints if mentioned.
Allowed team matching constraints:
- gender_diversity
- avoid_same_college
- balance_experience
- keep_friends_together
- separate_participants

DATE MATH (today = {today}, timezone = Asia/Kolkata +05:30):
  "opens now" / "today" → {today}T00:00:00+05:30
  "in N days" → add N days to {today}
  "March 15 9 AM IST" → 2026-03-15T09:00:00+05:30

Extract the event name/title ONLY if the organizer explicitly states it (e.g. "called X", "named X", "X 2026 Hackathon"). If no clear name is given, omit it — it will be asked separately.

THEMES/TRACKS: If the message describes one or more themes, tracks, or problem statements that teams compete under, extract them into "tracks". Capture each theme's name, description, and required_skills when given (e.g. "Theme: Edge AI Utilities — required skills Python, ML — build a small reliable edge ML utility").

OUTPUT SCHEMA (include only present fields):
{{
  "core": {{
    "name": "official event name, only if explicitly stated",
    "theme": "2-4 keyword phrase only",
    "event_type": "hackathon|case_competition|quiz|ideathon|coding_contest",
    "mode": "online|offline|hybrid",
    "description": "1-2 sentence auto-generated summary",
    "tagline": "",
    "tracks": [
      {{"track_id":"t1","name":"Edge AI Utilities","description":"Build a small reliable edge ML utility","required_skills":["Python","ML"]}}
    ],
    "venue": {{"name":"","city":"","state":"","country":""}},
    "contact": {{"email":"","phone":""}}
  }},
  "timeline": {{
    "timezone": "Asia/Kolkata",
    "registration": {{"opens_at":"ISO8601+05:30","closes_at":"ISO8601+05:30"}},
    "key_dates": [{{"name":"Event Start","date":"ISO8601+05:30","description":""}}]
  }},
  "participants": {{
    "model": "individual|teams",
    "individual_registration_allowed": true,
    "auto_team_matching_allowed": false,
    "team_matching": {{
      "enabled": true,
      "constraints": [
        {{
          "type": "gender_diversity",
          "min_per_team": 1
        }},
        {{
          "type": "avoid_same_college"
        }},
        {{
          "type": "balance_experience"
        }}
      ]
    }},
    "team": {{"min_size":4,"max_size":4}},
    "capacity": {{"max_teams":50,"max_participants":200}},
    "eligibility": {{"open_to":["students"]}}
  }}
}}"""


def _sec2_system() -> str:
    return """Extract rounds and judging panel from the organizer's message.
Return ONLY valid JSON — no markdown, no prose.
Include ONLY fields you can confidently extract. Omit unknown fields entirely.

ROUND TYPE MAPPING:
  oa / online assessment / quiz → "coding"
  idea submission / pdf / deck → "online_submission"
  prototype / github + video / coding sprint → "online_submission"
  offline hack / live coding → "coding"
  final presentation / live pitch / demo day → "live_presentation"

If scoring criteria ARE mentioned, weights MUST sum to 100 and max_score = weight, min_score = 0.
If scoring criteria are NOT mentioned, omit the scoring.criteria array entirely — still extract the round name, type, and dates.
Last round must have "is_final_round": true.

OUTPUT SCHEMA:
{
  "rounds": [
    {
      "round_id": "round_1",
      "round_number": 1,
      "round_name": "Idea Submission",
      "type": "online_submission",
      "deliverables": [
        {"name":"Idea Deck","type":"file","file_types":["pdf","pptx"],"required":true}
      ],
      "scoring": {
        "criteria": [
          {"criterion_id":"c1","name":"Innovation","weight":50,"max_score":50,"min_score":0}
        ]
      },
      "advancement": {"method":"top_n","value":10,"qualifies_to_round_id":"round_2"},
      "is_final_round": false
    }
  ],
  "judging_panel": {
    "judges": [
      {"judge_id":"judge_1","name":"Actual Name Only","company":"Company","expertise":["AI"]}
    ]
  }
}
CRITICAL: Only populate judges if the organizer gives REAL names (e.g. "Akshat Sharma from Google").
If the message only mentions a count ("3 judges") or companies without names, omit judging_panel entirely — do NOT create placeholder entries like "Judge 1"."""


def _sec3_system() -> str:
    return """Extract prizes and metadata from the organizer's message.
Return ONLY valid JSON — no markdown, no prose.
Include ONLY fields you can confidently extract. Omit unknown fields entirely.

CRITICAL: If the message contains NO prize, award, or cash information, return {} — do NOT invent, assume, or placeholder prize values.

total_pool = sum of ALL prize amounts (distribution + special awards).

OUTPUT SCHEMA:
{
  "prizes": {
    "currency": "INR",
    "total_pool": "₹1,10,000",
    "distribution": [
      {"rank":1,"title":"1st Place","amount":"₹50,000","description":"Cash prize","per_team":true},
      {"rank":2,"title":"2nd Place","amount":"₹30,000","per_team":true},
      {"rank":3,"title":"3rd Place","amount":"₹20,000","per_team":true}
    ],
    "special_awards": [
      {"name":"Best Women-Led Team","amount":"₹10,000","description":""}
    ],
    "certificates": {"participant_certificate":true,"winner_certificate":true}
  },
  "metadata": {
    "tags": ["climate","ai","hackathon"],
    "difficulty_level": "beginner|intermediate|advanced",
    "target_audience": "college students"
  }
}"""


def _followup_system() -> str:
    today = _today()
    return f"""You extract a specific event field from an organizer's short reply.
Return ONLY valid JSON — no markdown, no prose.
Today = {today}, timezone = Asia/Kolkata (+05:30).

DATE MATH: "in N days" = {today} + N days | "today/now" = {today}T00:00:00+05:30

The context will say "Field: <key>" — extract ONLY that field and wrap it in the correct top-level key.

EXAMPLES:
You will be told which field is being answered. Extract ONLY that field and return
the matching JSON structure. For example:

Field: venue → reply "IIT Delhi, Delhi" → {{"core":{{"venue":{{"name":"IIT Delhi","city":"Delhi","state":"Delhi","country":"India"}}}}}}
Field: contact → reply "abc@gmail.com 9876543210" → {{"core":{{"contact":{{"email":"abc@gmail.com","phone":"9876543210"}}}}}}
Field: registration → reply "opens today closes in 7 days" → {{"timeline":{{"registration":{{"opens_at":"{today}T00:00:00+05:30","closes_at":"COMPUTED_DATE"}}}}}}
Field: teams → reply "50 teams 4 each, up to 200 participants" → {{"participants":{{"capacity":{{"max_teams":50,"max_participants":200}},"team":{{"min_size":4,"max_size":4}}}}}}
  (Always capture max_participants when a total participant/registration cap is given, e.g. "max 2 participants" → capacity.max_participants = 2. If only team count and size are given, you may compute max_participants = max_teams × max_size.)
Field: judges → reply "Aarav Mehta from Google, AI expert" → {{"judging_panel":{{"judges":[{{"judge_id":"judge_1","name":"Aarav Mehta","company":"Google","expertise":["AI"]}}]}}}}
Field: rounds → extract full rounds array as {{"rounds":[...]}} with scoring, deliverables, advancement.
Field: prizes → reply "total 10k, 1st 5k, 2nd 5k" →
{{"prizes":{{"currency":"INR","total_pool":"₹10,000","distribution":[{{"rank":1,"title":"1st Place","amount":"₹5,000","per_team":true}},{{"rank":2,"title":"2nd Place","amount":"₹5,000","per_team":true}}],"special_awards":[]}}}}
Field: tracks → capture each theme's name, description, AND required_skills when given.
  reply "Edge AI Utilities — Python, ML — build a small reliable edge ML utility" → {{"core":{{"tracks":[{{"track_id":"t1","name":"Edge AI Utilities","description":"build a small reliable edge ML utility","required_skills":["Python","ML"]}}]}}}}
  reply "AI, Web3, Climate Tech" → {{"core":{{"tracks":[{{"track_id":"t1","name":"AI","description":"","required_skills":[]}},{{"track_id":"t2","name":"Web3","description":"","required_skills":[]}},{{"track_id":"t3","name":"Climate Tech","description":"","required_skills":[]}}]}}}}
Field: team_constraints → reply "at least 1 girl per team, members from different colleges" → {{"participants":{{"team_formation_constraints":"at least 1 girl per team, members from different colleges"}}}}

PRIZE RULES:
- Convert shorthand amounts: "10k"→"₹10,000", "1L"/"1,00,000"→"₹1,00,000", "5000"→"₹5,000"
- total_pool = sum of ALL prizes given. If only distribution given, sum them.
- Always wrap inside {{"prizes": {{...}}}} — never return prizes fields at the top level.
- If the user says no prizes / skip, return {{"prizes": {{"total_pool": "none"}}}}"""


# ── Skip detection ─────────────────────────────────────────────────────────────

_SKIP_PHRASES = {
    "no", "none", "n/a", "not needed", "skip", "na", "nope",
    "not applicable", "no thanks", "tbd", "later", "not sure",
    "dont know", "don't know", "idk",
}

# Core identity fields that cannot be skipped — the event is meaningless without
# them, so a "skip" reply is ignored and the question is asked again.
_NON_SKIPPABLE = {"name", "theme"}


def _is_skip(text: str) -> bool:
    return text.lower().strip().rstrip(".!,") in _SKIP_PHRASES


# ── What's still needed ────────────────────────────────────────────────────────

_FAKE_POOL_VALUES = {
    "", "tbd", "n/a", "na", "not mentioned", "not specified",
    "none", "no prizes", "₹0", "$0", "0", "unknown", "nil", "null",
}


def _sum_prize_distribution(distribution: list) -> str:
    """Sum prize amounts from distribution list and return formatted string, or '' on failure."""
    total = 0
    for entry in distribution:
        if not isinstance(entry, dict):
            continue
        raw = str(entry.get("amount", "")).replace(",", "").replace("₹", "").replace("$", "").strip()
        raw = re.sub(r"[^\d.]", "", raw)
        try:
            total += int(float(raw))
        except (ValueError, TypeError):
            return ""
    return f"₹{total:,}" if total else ""


def _prize_pool_missing(cfg: dict) -> bool:
    """Return True when total_pool is absent, empty, or a hallucinated placeholder."""
    total_pool = (cfg.get("prizes") or {}).get("total_pool", "")
    if not total_pool:
        return True
    normalized = str(total_pool).strip().lower()
    if normalized in _FAKE_POOL_VALUES:
        return True
    # A real prize value must contain at least one digit
    return not any(c.isdigit() for c in normalized)


_PLACEHOLDER_NAMES = {
    "judge 1", "judge 2", "judge 3", "judge 4", "judge 5",
    "judge1", "judge2", "judge3", "judge4", "judge5",
    "judge name", "actual name only", "placeholder", "tbd", "name",
}


def _has_real_judges(cfg: dict) -> bool:
    """Return True only if at least one judge has a real (non-placeholder) name."""
    judges = (cfg.get("judging_panel") or {}).get("judges") or []
    for j in judges:
        if not isinstance(j, dict):
            continue
        name = (j.get("name") or "").strip().lower()
        if name and name not in _PLACEHOLDER_NAMES and not name.startswith("judge "):
            return True
    return False


def _next_question(cfg: dict) -> Tuple[str, Optional[str], bool]:
    core = cfg.get("core", {})
    tl = cfg.get("timeline", {})
    reg = tl.get("registration", {})
    skipped = set(cfg.get("_skipped", []))

    checks = [
        (not core.get("name"),
         "name", "What is the name of the event?"),
        (not core.get("theme"),
         "theme", "What is the theme or focus area of the event?"),
        (not core.get("tracks"),
         "tracks", "What themes or tracks can teams compete under? For each, share its name, a short description, and the required skills (e.g. 'Edge AI Utilities — Python, ML — build a small reliable edge ML utility' — skip if not applicable)."),
        (not core.get("mode"),
         "mode", "Will this be online, offline, or hybrid?"),
        (core.get("mode") in ("offline", "hybrid") and not core.get("venue", {}).get("city"),
         "venue", "What is the venue name and city?"),
        (not core.get("contact", {}).get("email") and not core.get("contact", {}).get("phone"),
         "contact", "What is the contact email or phone for the event?"),
        (not reg.get("opens_at") or not reg.get("closes_at"),
         "registration", "When does registration open and close?"),
        ((not cfg.get("participants", {}).get("team", {}).get("min_size"))
         or (not cfg.get("participants", {}).get("capacity", {}).get("max_teams")
             and not cfg.get("participants", {}).get("capacity", {}).get("max_participants")),
         "teams", "What is the team size, and how many teams or participants can take part in total?"),
        (not cfg.get("participants", {}).get("team_formation_constraints"),
         "team_constraints", "Any team formation constraints? (e.g. 'at least 1 girl per team', 'members from different colleges' — skip if none)"),
        (not cfg.get("rounds"),
         "rounds", "Describe the rounds — names, types, and scoring criteria with weights."),
        (not _has_real_judges(cfg),
         "judges", "Tell me about the judges — names, companies, and areas of expertise."),
        (_prize_pool_missing(cfg),
         "prizes", "What is the prize pool and how is it distributed?"),
    ]

    for condition, field_key, question in checks:
        if condition and field_key not in skipped:
            return question, field_key, False

    return "All required fields are collected.", None, True


# ── File helpers ───────────────────────────────────────────────────────────────

def _data_dir() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data",
    )




def _load_index() -> list:
    path = os.path.join(_data_dir(), "index.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_index(entries: list) -> None:
    os.makedirs(_data_dir(), exist_ok=True)
    path = os.path.join(_data_dir(), "index.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, default=str, ensure_ascii=False)


def _load_config(event_id: str) -> dict:
    path = os.path.join(_data_dir(), event_id, "event.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"event_id": event_id, "version": "1.0"}


def _save_config(event_id: str, config: dict) -> str:
    dirpath = os.path.join(_data_dir(), event_id)
    os.makedirs(dirpath, exist_ok=True)
    path = os.path.join(dirpath, "event.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, default=str, ensure_ascii=False)
    return path


# ── Roster (participants / judges) file storage ─────────────────────────────────
# Deployed events live as JSON files keyed by event_id (see _save_config), not in
# the SQL events table. Their participant/judge rosters are stored the same way so
# CSV upload and listing work without a DB-side event row.

def _event_exists(event_id: str) -> bool:
    return os.path.exists(os.path.join(_data_dir(), event_id, "event.json"))


def _roster_path(event_id: str, kind: str) -> str:
    return os.path.join(_data_dir(), event_id, f"{kind}.json")


def _load_roster(event_id: str, kind: str) -> list:
    path = _roster_path(event_id, kind)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_roster(event_id: str, kind: str, items: list) -> None:
    dirpath = os.path.join(_data_dir(), event_id)
    os.makedirs(dirpath, exist_ok=True)
    with open(_roster_path(event_id, kind), "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, default=str, ensure_ascii=False)


# ── Core helpers ───────────────────────────────────────────────────────────────

def _deep_merge(base: dict, update: dict) -> dict:
    result = dict(base)
    for key, val in update.items():
        if val is None:
            result.setdefault(key, val)
        elif isinstance(val, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def _merge_pairs(pairs: list) -> dict:
    result: dict = {}
    for key, val in pairs:
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            for k, v in val.items():
                result[key][k] = v
        else:
            result[key] = val
    return result


def _parse_json(raw: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    text = re.sub(r"\s*```$", "", text).strip()
    try:
        return json.loads(text, object_pairs_hook=_merge_pairs)
    except json.JSONDecodeError:
        pass
    depth = 0
    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in: {text[:300]}")
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start: i + 1], object_pairs_hook=_merge_pairs)
    raise ValueError(f"Cannot parse JSON: {text[:300]}")


def _retry_after(err_str: str) -> str:
    m = re.search(r"Please try again in ([\w.]+)", err_str)
    return m.group(1) if m else "a few minutes"


# ── Model calling ──────────────────────────────────────────────────────────────

def _call_model_sync(
    client: Groq, model: str, context: str, max_tokens: int, system: str
) -> Tuple[dict, str]:

    def _invoke(m: str, toks: int) -> str:
        resp = client.chat.completions.create(
            model=m,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": context},
            ],
            temperature=0.2,
            max_tokens=toks,
        )
        choice = resp.choices[0]
        raw = choice.message.content or ""
        if choice.finish_reason == "length":
            raise RuntimeError("TRUNCATED")
        return raw

    def _try_fallbacks(toks: int) -> Tuple[str, str]:
        last_err: Exception = RuntimeError("All fallback models failed")
        for fb in _FALLBACK_MODELS:
            try:
                return _invoke(fb, toks), fb
            except RuntimeError as e:
                if "TRUNCATED" in str(e):
                    toks = min(toks * 2, 4096)
                last_err = e
            except _groq.RateLimitError as e:
                last_err = e
            except Exception as e:
                last_err = e
        if isinstance(last_err, _groq.RateLimitError):
            raise RuntimeError(f"RATE_LIMIT:{_retry_after(str(last_err))}") from last_err
        raise RuntimeError(f"All models failed: {last_err}") from last_err

    used = model
    raw = ""
    try:
        raw = _invoke(model, max_tokens)
    except RuntimeError as e:
        if "TRUNCATED" in str(e):
            raw, used = _try_fallbacks(max_tokens * 2)
        else:
            raise
    except _groq.RateLimitError:
        raw, used = _try_fallbacks(max_tokens)
    except Exception as e:
        err = str(e)
        if any(k in err for k in ("413", "rate_limit", "too large", "tokens per minute", "json_validate")):
            raw, used = _try_fallbacks(max_tokens)
        else:
            raise RuntimeError(f"Groq error ({model}): {err}") from e

    try:
        return _parse_json(raw), used
    except (ValueError, json.JSONDecodeError):
        if used == model:
            raw, used = _try_fallbacks(max_tokens)
            return _parse_json(raw), used
        raise ValueError(f"Unparseable JSON after fallbacks: {raw[:300]}")


# ── Parallel initial extraction ────────────────────────────────────────────────

async def _extract_initial_parallel(client: Groq, user_text: str) -> Tuple[dict, List[str]]:
    """Run 3 parallel section extractions on the initial event description."""
    sections = [
        (_sec1_system(), _MODELS[0]),
        (_sec2_system(), _MODELS[1 % len(_MODELS)]),
        (_sec3_system(), _FALLBACK_MODELS[0]),
    ]

    async def one(system: str, model: str) -> dict:
        try:
            result, _ = await asyncio.to_thread(
                _call_model_sync, client, model, user_text, 2000, system
            )
            return result if isinstance(result, dict) else {}
        except Exception:
            return {}

    results = await asyncio.gather(*[one(s, m) for s, m in sections])

    merged: dict = {}
    for r in results:
        if isinstance(r, dict):
            merged = _deep_merge(merged, r)

    return merged, [m for _, m in sections]


# ── _enrich_config ─────────────────────────────────────────────────────────────

def _enrich_config(config: dict) -> dict:
    """Fill default schema fields (matching example_json) without overwriting collected data."""
    now = datetime.now(IST).isoformat(timespec="seconds")

    if not isinstance(config.get("core"), dict):
        config["core"] = {}
    core = config["core"]
    core.setdefault("tagline", "")
    core.setdefault("tracks", [])
    core.setdefault("cover_image_url", "")
    core.setdefault("language", "English")
    venue = core.setdefault("venue", {})
    venue.setdefault("address", "")
    venue.setdefault("latitude", None)
    venue.setdefault("longitude", None)
    venue.setdefault("map_link", "")
    contact = core.setdefault("contact", {})
    contact.setdefault("whatsapp_group", "")
    contact.setdefault("discord_invite", "")
    contact.setdefault("helpdesk_hours", "")

    if not isinstance(config.get("participants"), dict):
        config["participants"] = {}
    participants = config["participants"]
    participants.setdefault("model", "individual")
    participants.setdefault("individual_registration_allowed", participants.get("model") == "individual")
    participants.setdefault("auto_team_matching_allowed", False)
    team = participants.setdefault("team", {})
    team.setdefault("exact_size", None)
    team.setdefault("can_team_have_mentor", False)
    team.setdefault("team_name_required", True)
    team.setdefault("team_code_required", True)
    team.setdefault("allow_team_join_after_creation", True)
    capacity = participants.setdefault("capacity", {})
    max_teams = capacity.get("max_teams") or 0
    max_size = team.get("max_size") or 4
    if max_teams and not capacity.get("max_participants"):
        capacity["max_participants"] = max_teams * max_size
    capacity.setdefault("waitlist_enabled", True)
    capacity.setdefault("waitlist_capacity", 20)
    eligibility = participants.setdefault("eligibility", {})
    eligibility.setdefault("open_to", ["students"])
    eligibility.setdefault("colleges_allowed", ["any"])
    eligibility.setdefault("specific_colleges", [])
    eligibility.setdefault("countries_allowed", ["India"])
    eligibility.setdefault("specific_countries", [])
    eligibility.setdefault("min_year_of_study", None)
    eligibility.setdefault("max_year_of_study", None)
    eligibility.setdefault("branches_allowed", ["any"])
    eligibility.setdefault("specific_branches", [])
    eligibility.setdefault("age_min", None)
    eligibility.setdefault("age_max", None)
    eligibility.setdefault("additional_criteria", "")
    participants.setdefault("team_formation_constraints", "")
    participants.setdefault("registration_form_fields", [
        {"field_id": "full_name", "label": "Full Name", "type": "text", "required": True},
        {"field_id": "email", "label": "Email Address", "type": "email", "required": True, "unique_per_event": True},
        {"field_id": "phone", "label": "WhatsApp Number", "type": "tel", "required": True},
        {"field_id": "college", "label": "College/University", "type": "text", "required": True},
        {"field_id": "year_of_study", "label": "Year of Study", "type": "select", "required": True,
         "options": ["1st Year", "2nd Year", "3rd Year", "4th Year", "5th Year", "PG", "PhD"]},
        {"field_id": "branch", "label": "Branch/Specialization", "type": "text", "required": False},
        {"field_id": "linkedin_url", "label": "LinkedIn Profile", "type": "url", "required": False},
    ])
    participants.setdefault("team_matching", {
        "enabled": False,
        "constraints": []
    })
    auto_team = participants.get("auto_team_matching_allowed", False)
    participants.setdefault("team_formation", {
        "method": "auto_ml" if auto_team else "manual",
        "allow_participants_to_form_teams": not auto_team,
        "allow_participants_to_invite_others": not auto_team,
        "csv_upload_template_columns": ["team_name"] + [f"member{i}_email" for i in range(1, max_size + 1)],
    })

    if not isinstance(config.get("rounds"), list):
        config["rounds"] = []
    round_ids = [r.get("round_id") for r in config["rounds"] if isinstance(r, dict) and r.get("round_id")]
    for i, rnd in enumerate(r for r in config["rounds"] if isinstance(r, dict)):
        rnd.setdefault("description", "")
        rnd.setdefault("dates", {})
        if not isinstance(rnd.get("deliverables"), list):
            rnd["deliverables"] = []
        for j, d in enumerate(d for d in rnd["deliverables"] if isinstance(d, dict)):
            d.setdefault("deliverable_id", f"del_{i + 1}_{j + 1}")
            d.setdefault("description", "")
            d.setdefault("required", True)
        scoring = rnd.setdefault("scoring", {})
        scoring.setdefault("total_max_score", 100)
        scoring.setdefault("passing_score", None)
        scoring.setdefault("auto_calculate_total", True)
        if not isinstance(scoring.get("criteria"), list):
            scoring["criteria"] = []
        for crit in scoring["criteria"]:
            if not isinstance(crit, dict):
                continue
            crit.setdefault("min_score", 0)
            crit.setdefault("score_type", "integer")
            crit.setdefault("description", "")
        rnd.setdefault("judging", {
            "judges_per_team": 2,
            "judge_assignment_method": "balanced",
            "avoid_judge_team_conflict": True,
            "scoring_method": "average",
            "allow_judge_comments": True,
            "make_comments_visible_to_participants": True,
            "allow_judge_to_see_other_scores": False,
        })
        rnd.setdefault("notifications", {
            "send_reminder_48h": True,
            "send_reminder_24h": True,
            "send_reminder_6h": True,
            "send_submission_confirmation": True,
            "send_results_email": True,
        })

    if isinstance(config.get("judging_panel"), list):
        config["judging_panel"] = {"judges": config["judging_panel"]}
    jp = config.setdefault("judging_panel", {})
    if not isinstance(jp.get("judges"), list):
        jp["judges"] = []
    jp.setdefault("judge_instructions", "Evaluate based on innovation, feasibility, and presentation quality. Provide constructive feedback for each team.")
    for judge in jp["judges"]:
        if not isinstance(judge, dict):
            continue
        judge.setdefault("email", "")
        judge.setdefault("title", "")
        judge.setdefault("bio", "")
        judge.setdefault("profile_image_url", "")
        judge.setdefault("linkedin_url", "")
        judge.setdefault("assigned_rounds", round_ids)
        judge.setdefault("max_teams_to_judge", 20)
        judge.setdefault("timezone", "Asia/Kolkata")

    if not isinstance(config.get("prizes"), dict):
        config["prizes"] = {}
    prizes = config["prizes"]
    prizes.setdefault("currency", "INR")
    if not isinstance(prizes.get("distribution"), list):
        prizes["distribution"] = []
    for dist in prizes["distribution"]:
        if isinstance(dist, dict):
            dist.setdefault("per_team", True)
            dist.setdefault("additional_benefits", [])
    prizes.setdefault("special_awards", [])
    prizes.setdefault("certificates", {
        "participant_certificate": True,
        "finalist_certificate": True,
        "winner_certificate": True,
        "judge_certificate": True,
        "organizer_certificate": True,
    })

    config.setdefault("resources", {
        "rules_document": {"title": "Official Rulebook", "url": "", "version": "1.0"},
        "faq": [],
        "resources": [],
        "mentors": [],
    })

    status = config.setdefault("status", {
        "current_phase": "draft",
        "published_at": None,
        "created_at": now,
        "updated_at": now,
        "created_by": "",
        "is_template": False,
        "template_id": None,
        "cloned_from_event_id": None,
    })
    status["updated_at"] = now

    expected = capacity.get("max_participants") or (max_teams * max_size)
    config.setdefault("metadata", {
        "tags": [],
        "difficulty_level": "intermediate",
        "target_audience": "",
        "expected_participants": expected,
        "sponsors": [],
        "organizing_team": [],
    })

    tl = config.setdefault("timeline", {})
    tl.setdefault("timezone", "Asia/Kolkata")

    # Normalize open_to to always be a list
    try:
        open_to = config["participants"]["eligibility"]["open_to"]
        if isinstance(open_to, str):
            config["participants"]["eligibility"]["open_to"] = [open_to]
    except (KeyError, TypeError):
        pass

    return config


# ── Static sections ────────────────────────────────────────────────────────────

def _static_sections() -> dict:
    return {
        "branding": {
            "primary_color": "#4F46E5",
            "secondary_color": "#10B981",
            "logo_url": "",
            "favicon_url": "",
            "social_links": {"linkedin": "", "twitter": "", "instagram": ""},
        },
        "analytics": {
            "track_registrations": True,
            "track_website_visits": True,
            "track_email_opens": True,
            "track_link_clicks": True,
            "google_analytics_id": None,
            "facebook_pixel_id": None,
        },
        "post_event": {
            "generate_report": True,
            "report_sections": [
                "participation_stats",
                "score_distribution",
                "judge_performance",
                "participant_feedback",
            ],
            "auto_release_certificates": True,
            "certificate_generation_delay_hours": 24,
            "feedback_form_enabled": True,
            "archived_for_cloning": True,
        },
        "communication": {
            "email_templates": {
                "registration_confirmation": {
                    "subject": "Registration confirmed for {event_name}",
                    "body_template": "email_templates/registration_confirmation.html",
                    "variables": ["participant_name", "event_name", "team_name", "dashboard_link"],
                },
                "submission_reminder": {
                    "subject": "Reminder: Submit your {round_name} entry by {deadline}",
                    "body_template": "email_templates/submission_reminder.html",
                    "variables": ["participant_name", "round_name", "deadline", "submission_link"],
                },
                "results": {
                    "subject": "{event_name} — Your results are ready",
                    "body_template": "email_templates/results.html",
                    "variables": ["participant_name", "event_name", "result", "feedback_link"],
                },
            },
            "deadline_reminders": {
                "registration_close": {"send_at_hours_before": [48, 24, 6, 1], "channel": ["email"]},
                "submission_deadline": {"send_at_hours_before": [48, 24, 6, 1], "channel": ["email"]},
            },
        },
        "integrations": {
            "discord": {
                "auto_create_roles": True,
                "auto_assign_participant_role": True,
                "channels_to_create": ["announcements", "team-finding", "general", "submissions"],
            },
            "zoom": {"enabled": False, "waiting_room_enabled": True},
            "calendar": {"auto_add_events": False},
        },
    }


def _compact_config(config: dict) -> dict:
    """Strip large/static sections from config before sending as context."""
    skip = {"branding", "analytics", "post_event", "communication", "integrations",
            "resources", "_skipped", "registration_form_fields"}
    return {k: v for k, v in config.items() if k not in skip}


# ── Request/Response models ────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    event_id: Optional[str] = None
    event_config: Optional[Dict[str, Any]] = None


class SaveConfigRequest(BaseModel):
    event_config: Dict[str, Any]
    event_id: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/chat", dependencies=[_organizer_only])
async def chat(request: ChatRequest):
    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")

    client = Groq(api_key=settings.GROQ_API_KEY)
    # Prefer explicit `request.event_id`, then any `event_id` present inside
    # `request.event_config` (some clients send the full config back), and
    # finally fall back to a new UUID. This prevents losing state when the
    # client omits `event_id` but includes `event_config`. A client-supplied id
    # that isn't a valid UUID is discarded (path-traversal guard).
    event_id = request.event_id or (request.event_config or {}).get("event_id") or ""
    if not _is_uuid(event_id):
        event_id = str(uuid.uuid4())

    # Serialize concurrent turns for the same event so a slow model call in one
    # request can't let another overwrite the JSON file with stale state.
    lock = await _event_lock(event_id)
    async with lock:
        return await _chat_turn(client, event_id, request)


async def _chat_turn(client: Groq, event_id: str, request: ChatRequest) -> dict:
    config = _load_config(event_id)
    config.setdefault("_skipped", [])

    user_messages = [m for m in request.messages if m.role == "user"]
    user_reply = user_messages[-1].content.strip() if user_messages else ""

    # Python determines what is still missing BEFORE processing this turn.
    # `next_field` is the authoritative key for the question being answered —
    # use it directly instead of reverse-mapping the question text (which used
    # to mis-fire, e.g. the venue question contains the word "name").
    next_q, next_field, _ = _next_question(config)

    models_used: List[str] = []
    updates: dict = {}

    # ── Detect first turn ─────────────────────────────────────────────────────
    is_initial = len(user_messages) == 1 and not config.get("core", {}).get("name")

    if is_initial:
        # Run 3 parallel section extractions
        updates, models_used = await _extract_initial_parallel(client, user_reply)

    elif _is_skip(user_reply):
        # User said "no" / "not needed" — mark field as skipped, unless it's a
        # required identity field (name/theme), in which case ignore the skip so
        # the question is asked again.
        field_key = next_field
        if (
            field_key
            and field_key not in _NON_SKIPPABLE
            and field_key not in config["_skipped"]
        ):
            config["_skipped"].append(field_key)
        updates = {}

    else:
        # Targeted single-model extraction for the specific field being answered
        field_key = next_field or "unknown"
        context = (
            f"Field: {field_key}\n"
            f"Question asked: {next_q}\n\n"
            f"Current config:\n{json.dumps(_compact_config(config), default=str)}\n\n"
            f"User reply: {user_reply}"
        )
        try:
            result, model_used = await asyncio.to_thread(
                _call_model_sync, client, _next_model(), context, 1500, _followup_system()
            )
            models_used = [model_used]
            updates = result if isinstance(result, dict) else {}
        except RuntimeError as e:
            err_str = str(e)
            if err_str.startswith("RATE_LIMIT:"):
                raise HTTPException(
                    status_code=429,
                    detail=f"AI rate limit reached. Please try again in {err_str.split(':', 1)[1]}.",
                )
            raise HTTPException(status_code=500, detail=err_str)
        except ValueError:
            # The model returned JSON we couldn't parse (a transient formatting
            # hiccup). Degrade gracefully — keep updates empty so the same
            # question is asked again — instead of surfacing a 500.
            models_used = []
            updates = {}

        # Python safety net for simple fields the AI might miss. Gate each net on
        # the field actually being answered (`field_key`) — not on substrings of
        # the question text, which collide (venue contains "name", tracks contains
        # "themes") and could write the wrong value when an earlier field was skipped.
        core = config.get("core", {})
        updates_core = updates.get("core", {})
        if field_key == "name" and not core.get("name") and not updates_core.get("name"):
            updates = _deep_merge(updates, {"core": {"name": user_reply}})
        elif field_key == "theme" and not core.get("theme") and not updates_core.get("theme"):
            updates = _deep_merge(updates, {"core": {"theme": user_reply}})
        elif field_key == "mode" and not core.get("mode") and not updates_core.get("mode"):
            mv = user_reply.lower().strip()
            if mv in ("online", "offline", "hybrid"):
                updates = _deep_merge(updates, {"core": {"mode": mv}})

        # Prize safety net: if AI put prizes fields at wrong nesting level, fix it
        if field_key == "prizes":
            prize_updates = updates.get("prizes", {})
            # If AI returned top-level total_pool instead of wrapping in prizes key
            if not prize_updates.get("total_pool") and updates.get("total_pool"):
                updates = _deep_merge(updates, {"prizes": {"total_pool": updates.pop("total_pool")}})
            # If AI still didn't set total_pool but gave distribution, compute total from it
            prize_updates = updates.get("prizes", {})
            if not prize_updates.get("total_pool") and isinstance(prize_updates.get("distribution"), list):
                total = _sum_prize_distribution(prize_updates["distribution"])
                if total:
                    updates = _deep_merge(updates, {"prizes": {"total_pool": total}})
            # Last resort: if AI produced nothing useful, store raw reply so question moves forward
            if _prize_pool_missing({"prizes": updates.get("prizes", {})}):
                updates = _deep_merge(updates, {"prizes": {"total_pool": user_reply.strip()}})
                # The user has now answered the prize question once. A non-numeric
                # reply ("decide later") still fails _prize_pool_missing, which
                # would re-ask forever — so mark prizes resolved to advance.
                if "prizes" not in config["_skipped"]:
                    config["_skipped"].append("prizes")

    # ── Merge updates into config ─────────────────────────────────────────────
    if updates:
        config = _deep_merge(config, updates)

    # Normalize theme: must be a short phrase, not a sentence. Truncate to a few
    # keywords rather than discarding (setting it to None would re-ask the theme
    # question every turn if the model kept returning a long phrase).
    theme = config.get("core", {}).get("theme", "")
    if isinstance(theme, str) and len(theme) > 50:
        config["core"]["theme"] = " ".join(theme.split()[:6])[:50].strip()

    config.setdefault("event_id", event_id)
    config.setdefault("version", "1.0")

    for key, val in _static_sections().items():
        config.setdefault(key, val)

    config = _enrich_config(config)
    _save_config(event_id, config)

    # Re-check after merge — Python is authoritative
    message, _, is_complete = _next_question(config)

    return {
        "message": message,
        "event_config": config,
        "is_complete": is_complete,
        "event_id": event_id,
        "_models_used": models_used,
    }


async def _materialize_rounds_judges_rubric(
    db: AsyncSession, event: EventModel, config: dict
) -> None:
    """First-deploy setup: create the event's themes, rounds, seed each round's
    rubric from the AI scoring criteria, and invite any judges that have an email."""
    # ── Themes (from core.tracks) ──
    tracks_cfg = ((config.get("core") or {}).get("tracks")) or []
    seen_theme_names = set()
    for t in tracks_cfg:
        if not isinstance(t, dict):
            continue
        tname = str(t.get("name") or "").strip()
        if not tname or tname.lower() in seen_theme_names:
            continue
        seen_theme_names.add(tname.lower())
        skills = t.get("required_skills") or []
        if not isinstance(skills, list):
            skills = []
        db.add(
            ThemeModel(
                event_id=event.id,
                name=tname[:200],
                description=(str(t.get("description") or "")[:1000]) or None,
                required_skills=[str(s)[:60] for s in skills],
            )
        )
    if seen_theme_names:
        await db.commit()

    # ── Rounds ──
    rounds_cfg = config.get("rounds") or []
    created: List[Tuple[RoundModel, dict]] = []
    # Stamp rounds with strictly increasing created_at values. Postgres
    # func.now() returns the *transaction* start time, so every round added in
    # this single-commit batch would otherwise share an identical created_at —
    # and any `ORDER BY created_at` (the judge dashboard, the pipeline's per-round
    # step order) would then return them jumbled and inconsistently per query.
    from app.services.time_enforcement import parse_dt

    def _round_dates(r: dict):
        """Pull start/end out of a round's `dates` block, tolerant of key names."""
        d = r.get("dates") or {}
        start = parse_dt(
            d.get("start") or d.get("starts_at") or d.get("opens_at") or d.get("start_date")
        )
        end = parse_dt(
            d.get("end") or d.get("ends_at") or d.get("deadline")
            or d.get("closes_at") or d.get("submission_deadline") or d.get("end_date")
        )
        return start, end

    base_now = datetime.now(timezone.utc)
    if rounds_cfg:
        for idx, r in enumerate(rounds_cfg):
            rname = r.get("round_name") or r.get("name") or f"Round {idx + 1}"
            start_date, end_date = _round_dates(r)
            rnd = RoundModel(
                event_id=event.id,
                name=str(rname)[:120],
                status=RoundStatus.upcoming,
                start_date=start_date,
                end_date=end_date,
                created_at=base_now + timedelta(seconds=idx),
            )
            db.add(rnd)
            created.append((rnd, r))
    else:
        rnd = RoundModel(
            event_id=event.id,
            name="Round 1",
            status=RoundStatus.upcoming,
            created_at=base_now,
        )
        db.add(rnd)
        created.append((rnd, {}))
    await db.commit()
    for rnd, _ in created:
        await db.refresh(rnd)

    # ── Rubric per round (from scoring.criteria when present) ──
    for rnd, r in created:
        criteria = ((r.get("scoring") or {}).get("criteria")) or []
        rows = []
        for pos, c in enumerate(criteria):
            cname = str(c.get("name") or "").strip()
            if not cname:
                continue
            max_score = c.get("max_score") or c.get("weight") or 10
            rows.append(
                RubricCriterion(
                    round_id=rnd.id,
                    name=cname[:120],
                    description=(str(c.get("description") or "")[:300]) or None,
                    max_score=float(max_score),
                    position=pos,
                )
            )
        if rows:
            db.add_all(rows)
    await db.commit()

    # ── Judges (only those with a usable email) ──
    judges_cfg = ((config.get("judging_panel") or {}).get("judges")) or []
    for j in judges_cfg:
        email = str(j.get("email") or "").strip()
        if not email or "@" not in email:
            continue
        existing = (
            await db.execute(
                select(JudgeModel).where(
                    JudgeModel.event_id == event.id,
                    JudgeModel.email == email,
                )
            )
        ).scalars().first()
        if existing:
            continue
        db.add(
            JudgeModel(
                event_id=event.id,
                name=j.get("name") or email.split("@")[0],
                email=email,
                institution=j.get("company") or j.get("institution") or None,
                expertise=j.get("expertise") or [],
            )
        )
    await db.commit()


@router.post("/deploy")
async def deploy_event(
    request: SaveConfigRequest,
    auth: AuthContext = Depends(require_actor_type(["organizer", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Deploy an AI-designed event as a real SQL event so it appears on the
    organizer dashboard (which reads the `events` table). Idempotent on event_id:
    re-deploying updates event-level fields; rounds/judges/rubric are materialized
    once on the first deploy so later manual edits are preserved. The JSON config
    + index are kept in sync for the roster/detail endpoints."""
    config = request.event_config.copy()
    event_id = request.event_id or config.get("event_id") or ""
    if not _is_uuid(event_id):
        event_id = str(uuid.uuid4())
    event_uuid = uuid.UUID(event_id)
    config["event_id"] = event_id

    short_hash = generate_event_hash(event_id)
    config["hash"] = short_hash

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    config.setdefault("status", {})
    config["status"]["current_phase"] = "ready"
    config["status"]["updated_at"] = now_iso
    config["status"].setdefault("created_at", now_iso)

    # Persist the JSON config (chat already saved it; deploy may carry edits).
    lock = await _event_lock(event_id)
    async with lock:
        filepath = _save_config(event_id, config)

    # ── Materialize as a real SQL event so the dashboard (/events) can see it ──
    core = config.get("core") or {}
    participants = config.get("participants") or {}
    team = participants.get("team") or {}
    capacity = participants.get("capacity") or {}

    name = core.get("name") or "Untitled Event"
    etype = core.get("event_type") or "hackathon"
    description = core.get("description") or ""
    try:
        min_size = int(team.get("min_size") or 1)
        max_size = int(team.get("max_size") or 4)
    except (TypeError, ValueError):
        min_size, max_size = 1, 4
    try:
        max_participants = int(capacity.get("max_participants") or 0)
    except (TypeError, ValueError):
        max_participants = 0

    # Registration window from the AI config timeline (IST → UTC).
    from app.services.time_enforcement import parse_dt

    reg_cfg = ((config.get("timeline") or {}).get("registration")) or {}
    reg_opens = parse_dt(reg_cfg.get("opens_at"))
    reg_closes = parse_dt(reg_cfg.get("closes_at"))

    # ── Public registration page (Task 6) ───────────────────────────────────
    # Promote the form spec from the AI JSON into SQL so the public, unauthenticated
    # endpoints can serve it without touching disk. For AI-deployed events we
    # populate the form directly (preserving the one-shot deploy UX); the manual
    # editor's later edits go through the registration_form approval gate.
    p_model = (participants.get("model") or "individual").lower()
    if p_model not in ("individual", "team"):
        p_model = "individual"
    individual_reg_allowed = bool(
        participants.get("individual_registration_allowed", p_model == "individual")
    )
    auto_team = bool(participants.get("auto_team_matching_allowed", False))
    form_fields = participants.get("registration_form_fields") or None
    eligibility_cfg = participants.get("eligibility") or None
    # Teams the participants bring themselves (leader registers members) →
    # preformed; individual events or org-formed (auto-matched) teams →
    # platform_generated. team_formation_type is stored only (not consumed by
    # the pipeline), so deriving it here is safe.
    derived_formation = (
        TeamFormationType.preformed
        if (p_model == "team" and not auto_team)
        else TeamFormationType.platform_generated
    )

    organizer_id = auth.entity.id

    existing = (
        await db.execute(select(EventModel).where(EventModel.id == event_uuid))
    ).scalars().first()
    is_new = existing is None

    if existing:
        if str(existing.organizer_id) != str(organizer_id):
            raise HTTPException(status_code=403, detail="This event belongs to another organizer.")
        existing.name = name
        existing.type = etype
        existing.description = description
        existing.min_team_size = min_size
        existing.max_team_size = max_size
        existing.max_participants = max_participants
        existing.registration_opens_at = reg_opens
        existing.registration_closes_at = reg_closes
        existing.participants_model = p_model
        existing.individual_registration_allowed = individual_reg_allowed
        existing.eligibility = eligibility_cfg
        existing.team_formation_type = derived_formation
        # Only seed the form on first population — don't clobber an organizer's
        # approved manual edits on re-deploy.
        if not existing.registration_form_fields and form_fields:
            existing.registration_form_fields = form_fields
        event = existing
    else:
        event = EventModel(
            id=event_uuid,
            organizer_id=organizer_id,
            name=name,
            hash=short_hash,
            description=description,
            type=etype,
            # Gated deploy: a new event lands as DRAFT and is only published
            # (→ active) when the organizer approves the event_deploy request.
            # Draft events are excluded from the public listing (status filter).
            status=EventStatus.draft,
            stage=EventStage.registration,
            team_formation_type=derived_formation,
            min_team_size=min_size,
            max_team_size=max_size,
            max_participants=max_participants,
            registration_opens_at=reg_opens,
            registration_closes_at=reg_closes,
            participants_model=p_model,
            individual_registration_allowed=individual_reg_allowed,
            eligibility=eligibility_cfg,
            registration_form_fields=form_fields,
        )
        db.add(event)

    await db.commit()
    await db.refresh(event)

    # Gated deploy (option C): instead of materializing + going live here, create
    # a pending `event_deploy` approval. The event stays draft (new) until the
    # organizer approves it in the Approvals panel — at which point the executor
    # flips it to active and materializes rounds/judges/rubric (+ the form goes
    # live with it, since the form fields are already on the row). Re-deploys of
    # an already-live event update its fields immediately (it's already public)
    # and still record an approval for audit; the executor is idempotent.
    from app.models.approval import RequestType as _RequestType
    from app.services.approval_service import create_approval_request

    deploy_approval = await create_approval_request(
        db,
        event_id=str(event.id),
        request_type=_RequestType.event_deploy,
        payload={"event_id": event_id, "config": config},
        requested_by=str(organizer_id),
    )

    # Keep the deployed-events index in sync (used by /ai/events).
    async with _index_lock:
        index = [e for e in _load_index() if e.get("event_id") != event_id]
        index.insert(0, {
            "event_id": event_id,
            "hash": short_hash,
            "name": name,
            "type": etype,
            "mode": core.get("mode", ""),
            "theme": core.get("theme", ""),
            "description": description,
            "deployed_at": now_iso,
            "judges_count": len((config.get("judging_panel") or {}).get("judges") or []),
            "rounds_count": len(config.get("rounds") or []),
            "max_teams": capacity.get("max_teams", 0),
            "max_participants": capacity.get("max_participants", 0),
            "prize_pool": (config.get("prizes") or {}).get("total_pool", ""),
        })
        _save_index(index)

    return {
        "success": True,
        "event_id": event_id,
        "hash": short_hash,
        "file_path": filepath,
        "status": "pending_approval",
        "approval_id": str(deploy_approval.id),
    }


@router.get("/events", dependencies=[_organizer_only])
async def list_deployed_events():
    return _load_index()


@router.get("/events/{hash}", dependencies=[_organizer_only])
async def get_deployed_event(hash: str):
    index = _load_index()
    entry = next((e for e in index if e.get("hash") == hash), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Event not found")
    return _load_config(entry["event_id"])


# ── Per-event roster endpoints (by event_id) ────────────────────────────────────
# These use a two-segment path (/events/{event_id}/...) so they never collide with
# the single-segment /events/{hash} lookup above.

class ParticipantEntry(BaseModel):
    name: str
    email: str
    institution: Optional[str] = ""
    skills: Optional[List[str]] = None


class JudgeEntry(BaseModel):
    name: str
    email: str
    institution: Optional[str] = ""
    expertise: Optional[List[str]] = None


def _require_event(event_id: str) -> None:
    # Reject non-UUID ids before they touch the filesystem (path-traversal guard),
    # then confirm the event actually exists.
    if not _is_uuid(event_id) or not _event_exists(event_id):
        raise HTTPException(status_code=404, detail="Event not found")


@router.get("/events/{event_id}/detail", dependencies=[_organizer_only])
async def get_event_detail(event_id: str):
    _require_event(event_id)
    return _load_config(event_id)


@router.get("/events/{event_id}/participants", dependencies=[_organizer_only])
async def list_event_participants(event_id: str):
    _require_event(event_id)
    return _load_roster(event_id, "participants")


@router.post("/events/{event_id}/participants", dependencies=[_organizer_only])
async def add_event_participant(event_id: str, entry: ParticipantEntry):
    _require_event(event_id)
    async with await _event_lock(event_id):
        roster = _load_roster(event_id, "participants")
        if any((p.get("email") or "").lower() == entry.email.lower() for p in roster):
            raise HTTPException(status_code=409, detail="A participant with this email already exists")
        roster.append({
            "id": str(uuid.uuid4()),
            "name": entry.name,
            "email": entry.email,
            "institution": entry.institution or "",
            "skills": entry.skills or [],
            "registration_status": "pending",
        })
        _save_roster(event_id, "participants", roster)
        return roster[-1]


@router.post("/events/{event_id}/participants/upload-csv", dependencies=[_organizer_only])
async def upload_event_participants_csv(event_id: str, file: UploadFile = File(...)):
    _require_event(event_id)
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    rows = parse_participant_csv(content)

    async with await _event_lock(event_id):
        roster = _load_roster(event_id, "participants")
        seen = {(p.get("email") or "").lower() for p in roster}
        added = 0
        for r in rows:
            email = (r.get("email") or "").lower()
            if not email or email in seen:
                continue
            seen.add(email)
            roster.append({
                "id": str(uuid.uuid4()),
                "name": r.get("name", ""),
                "email": r.get("email", ""),
                "institution": r.get("organization") or "",
                "skills": r.get("skills") or [],
                "registration_status": "pending",
            })
            added += 1

        _save_roster(event_id, "participants", roster)
        total = len(roster)
    return {
        "message": f"Imported {added} participant(s)"
        + (f", skipped {len(rows) - added} duplicate/invalid" if len(rows) - added > 0 else ""),
        "count": added,
        "total": total,
        "participants": roster,
    }


@router.get("/events/{event_id}/judges", dependencies=[_organizer_only])
async def list_event_judges(event_id: str):
    _require_event(event_id)
    return _load_roster(event_id, "judges")


@router.post("/events/{event_id}/judges", dependencies=[_organizer_only])
async def add_event_judge(event_id: str, entry: JudgeEntry):
    _require_event(event_id)
    async with await _event_lock(event_id):
        roster = _load_roster(event_id, "judges")
        if any((j.get("email") or "").lower() == entry.email.lower() for j in roster):
            raise HTTPException(status_code=409, detail="A judge with this email already exists")
        roster.append({
            "id": str(uuid.uuid4()),
            "name": entry.name,
            "email": entry.email,
            "institution": entry.institution or "",
            "expertise": entry.expertise or [],
            "rating": 5.0,
        })
        _save_roster(event_id, "judges", roster)
        return roster[-1]


@router.post("/events/{event_id}/judges/upload-csv", dependencies=[_organizer_only])
async def upload_event_judges_csv(event_id: str, file: UploadFile = File(...)):
    _require_event(event_id)
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    rows = parse_judge_csv(content)

    async with await _event_lock(event_id):
        roster = _load_roster(event_id, "judges")
        seen = {(j.get("email") or "").lower() for j in roster}
        added = 0
        for r in rows:
            email = (r.get("email") or "").lower()
            if not email or email in seen:
                continue
            seen.add(email)
            roster.append({
                "id": str(uuid.uuid4()),
                "name": r.get("name", ""),
                "email": r.get("email", ""),
                "institution": r.get("organization") or "",
                "expertise": r.get("expertise") or [],
                "rating": 5.0,
            })
            added += 1

        _save_roster(event_id, "judges", roster)
        total = len(roster)
    return {
        "message": f"Imported {added} judge(s)"
        + (f", skipped {len(rows) - added} duplicate/invalid" if len(rows) - added > 0 else ""),
        "count": added,
        "total": total,
        "judges": roster,
    }


@router.post("/save-config", dependencies=[_organizer_only])
async def save_config(request: SaveConfigRequest):
    config = request.event_config.copy()
    event_id = request.event_id or config.get("event_id") or ""
    if not _is_uuid(event_id):
        event_id = str(uuid.uuid4())
    config["event_id"] = event_id

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    config.setdefault("status", {})
    config["status"]["updated_at"] = now_iso
    config["status"].setdefault("created_at", now_iso)

    async with await _event_lock(event_id):
        filepath = _save_config(event_id, config)
    return {
        "success": True,
        "event_id": event_id,
        "file_path": filepath,
        "filename": f"event_{event_id}.json",
    }
