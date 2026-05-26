import asyncio
import hashlib
import json
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import groq as _groq
from groq import Groq
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()

_MODELS = ["llama-3.3-70b-versatile", "meta-llama/llama-4-scout-17b-16e-instruct"]
_FALLBACK_MODELS = ["llama-3.1-8b-instant", "llama3-8b-8192"]
_counter = 0


def _next_model() -> str:
    global _counter
    m = _MODELS[_counter % len(_MODELS)]
    _counter += 1
    return m


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


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

DO NOT extract the event name/title — that is always asked separately.

OUTPUT SCHEMA (include only present fields):
{{
  "core": {{
    "theme": "2-4 keyword phrase only",
    "event_type": "hackathon|case_competition|quiz|ideathon|coding_contest",
    "mode": "online|offline|hybrid",
    "description": "1-2 sentence auto-generated summary",
    "tagline": "",
    "venue": {{"name":"","city":"","state":"","country":""}},
    "contact": {{"email":"","phone":""}}
  }},
  "timeline": {{
    "timezone": "Asia/Kolkata",
    "registration": {{"opens_at":"ISO8601+05:30","closes_at":"ISO8601+05:30"}},
    "key_dates": [{{"name":"Event Start","date":"ISO8601+05:30","description":""}}]
  }},
  "participants": {
  "model": "individual|teams",
  "individual_registration_allowed": true,
  "auto_team_matching_allowed": false,

  "team_matching": {
    "enabled": true,
    "constraints": [
      {
        "type": "gender_diversity",
        "min_per_team": 1
      },
      {
        "type": "avoid_same_college"
      },
      {
        "type": "balance_experience"
      }
    ]
  },

  "team": {"min_size":4,"max_size":4},
  "capacity": {"max_teams":50},
  "eligibility": {"open_to":["students"]}
}
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

Scoring weights MUST sum to 100. max_score = weight, min_score = 0.
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

You will be told which field is being answered. Extract ONLY that field and return
the matching JSON structure. For example:

Field: venue → reply "IIT Delhi, Delhi" → {{"core":{{"venue":{{"name":"IIT Delhi","city":"Delhi","state":"Delhi","country":"India"}}}}}}
Field: contact → reply "abc@gmail.com 9876543210" → {{"core":{{"contact":{{"email":"abc@gmail.com","phone":"9876543210"}}}}}}
Field: registration → reply "opens today closes in 7 days" → {{"timeline":{{"registration":{{"opens_at":"{today}T00:00:00+05:30","closes_at":"COMPUTED_DATE"}}}}}}
Field: teams → reply "50 teams 4 each" → {{"participants":{{"capacity":{{"max_teams":50}},"team":{{"min_size":4,"max_size":4}}}}}}
Field: rounds → extract full rounds array with scoring, deliverables, advancement.
Field: judges → extract judging_panel.judges array.
Field: prizes → extract full prizes object."""


# ── Skip detection ─────────────────────────────────────────────────────────────

_SKIP_PHRASES = {
    "no", "none", "n/a", "not needed", "skip", "na", "nope",
    "not applicable", "no thanks", "tbd", "later", "not sure",
    "dont know", "don't know", "idk",
}


def _is_skip(text: str) -> bool:
    return text.lower().strip().rstrip(".!,") in _SKIP_PHRASES


def _question_to_field_key(question: str) -> Optional[str]:
    q = question.lower()
    if "name of the event" in q:
        return "name"
    if "theme" in q:
        return "theme"
    if "online" in q or "offline" in q or "hybrid" in q:
        return "mode"
    if "venue" in q:
        return "venue"
    if "contact" in q:
        return "contact"
    if "registration" in q:
        return "registration"
    if "team" in q:
        return "teams"
    if "round" in q:
        return "rounds"
    if "judge" in q:
        return "judges"
    if "prize" in q:
        return "prizes"
    return None


# ── What's still needed ────────────────────────────────────────────────────────

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


def _next_question(cfg: dict) -> Tuple[str, bool]:
    core = cfg.get("core", {})
    tl = cfg.get("timeline", {})
    reg = tl.get("registration", {})
    skipped = set(cfg.get("_skipped", []))

    checks = [
        (not core.get("name"),
         "name", "What is the name of the event?"),
        (not core.get("theme"),
         "theme", "What is the theme or focus area of the event?"),
        (not core.get("mode"),
         "mode", "Will this be online, offline, or hybrid?"),
        (core.get("mode") in ("offline", "hybrid") and not core.get("venue", {}).get("city"),
         "venue", "What is the venue name and city?"),
        (not core.get("contact", {}).get("email") and not core.get("contact", {}).get("phone"),
         "contact", "What is the contact email or phone for the event?"),
        (not reg.get("opens_at") or not reg.get("closes_at"),
         "registration", "When does registration open and close?"),
        (not cfg.get("participants", {}).get("team", {}).get("min_size")
         and not cfg.get("participants", {}).get("capacity", {}).get("max_teams"),
         "teams", "How many teams can participate, and what is the team size?"),
        (not cfg.get("rounds"),
         "rounds", "Describe the rounds — names, types, and scoring criteria with weights."),
        (not _has_real_judges(cfg),
         "judges", "Tell me about the judges — names, companies, and areas of expertise."),
        (not cfg.get("prizes", {}).get("total_pool"),
         "prizes", "What is the prize pool and how is it distributed?"),
    ]

    for condition, field_key, question in checks:
        if condition and field_key not in skipped:
            return question, False

    return "All required fields are collected.", True


# ── File helpers ───────────────────────────────────────────────────────────────

def _data_dir() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data",
    )


_HASH_CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def _make_short_hash(event_id: str) -> str:
    """Derive a short EF-XXXXXX display hash from the event UUID."""
    digest = hashlib.sha256(event_id.encode()).digest()
    return "EF-" + "".join(_HASH_CHARSET[b % 36] for b in digest[:6])


def _load_index() -> list:
    path = os.path.join(_data_dir(), "index.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def _save_index(entries: list) -> None:
    os.makedirs(_data_dir(), exist_ok=True)
    path = os.path.join(_data_dir(), "index.json")
    with open(path, "w") as f:
        json.dump(entries, f, indent=2, default=str)


def _load_config(event_id: str) -> dict:
    path = os.path.join(_data_dir(), event_id, "event.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"event_id": event_id, "version": "1.0"}


def _save_config(event_id: str, config: dict) -> str:
    dirpath = os.path.join(_data_dir(), event_id)
    os.makedirs(dirpath, exist_ok=True)
    path = os.path.join(dirpath, "event.json")
    with open(path, "w") as f:
        json.dump(config, f, indent=2, default=str)
    return path


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
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+05:30")

    if not isinstance(config.get("core"), dict):
        config["core"] = {}
    core = config["core"]
    core.setdefault("tagline", "")
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

@router.post("/chat")
async def chat(request: ChatRequest):
    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")

    client = Groq(api_key=settings.GROQ_API_KEY)
    event_id = request.event_id or str(uuid.uuid4())
    config = _load_config(event_id)
    config.setdefault("_skipped", [])

    user_messages = [m for m in request.messages if m.role == "user"]
    user_reply = user_messages[-1].content.strip() if user_messages else ""

    # Python determines what is still missing BEFORE processing this turn
    next_q, _ = _next_question(config)

    models_used: List[str] = []
    updates: dict = {}

    # ── Detect first turn ─────────────────────────────────────────────────────
    is_initial = len(user_messages) == 1 and not config.get("core", {}).get("name")

    if is_initial:
        # Run 3 parallel section extractions
        updates, models_used = await _extract_initial_parallel(client, user_reply)

    elif _is_skip(user_reply):
        # User said "no" / "not needed" — mark field as skipped
        field_key = _question_to_field_key(next_q)
        if field_key and field_key not in config["_skipped"]:
            config["_skipped"].append(field_key)
        updates = {}

    else:
        # Targeted single-model extraction for the specific field being answered
        context = (
            f"FIELD BEING ANSWERED: {next_q}\n\n"
            f"CURRENT CONFIG:\n{json.dumps(_compact_config(config), default=str)}\n\n"
            f"USER REPLY: {user_reply}"
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

        # Python safety net for simple fields the AI might miss
        core = config.get("core", {})
        updates_core = updates.get("core", {})
        if not core.get("name") and not updates_core.get("name") and "name" in next_q.lower():
            updates = _deep_merge(updates, {"core": {"name": user_reply}})
        elif not core.get("theme") and not updates_core.get("theme") and "theme" in next_q.lower():
            updates = _deep_merge(updates, {"core": {"theme": user_reply}})
        elif not core.get("mode") and not updates_core.get("mode"):
            mv = user_reply.lower().strip()
            if mv in ("online", "offline", "hybrid"):
                updates = _deep_merge(updates, {"core": {"mode": mv}})

    # ── Merge updates into config ─────────────────────────────────────────────
    if updates:
        config = _deep_merge(config, updates)

    # Normalize theme: must be a short phrase, not a sentence
    theme = config.get("core", {}).get("theme", "")
    if isinstance(theme, str) and len(theme) > 50:
        config["core"]["theme"] = None

    config.setdefault("event_id", event_id)
    config.setdefault("version", "1.0")

    for key, val in _static_sections().items():
        config.setdefault(key, val)

    config = _enrich_config(config)
    _save_config(event_id, config)

    # Re-check after merge — Python is authoritative
    message, is_complete = _next_question(config)

    return {
        "message": message,
        "event_config": config,
        "is_complete": is_complete,
        "event_id": event_id,
        "_models_used": models_used,
    }


@router.post("/deploy")
async def deploy_event(request: SaveConfigRequest):
    config = request.event_config.copy()
    event_id = request.event_id or config.get("event_id") or str(uuid.uuid4())
    config["event_id"] = event_id

    short_hash = _make_short_hash(event_id)
    config["hash"] = short_hash

    now_iso = datetime.utcnow().isoformat() + "Z"
    config.setdefault("status", {})
    config["status"]["current_phase"] = "ready"
    config["status"]["updated_at"] = now_iso
    config["status"].setdefault("created_at", now_iso)

    filepath = _save_config(event_id, config)

    # Upsert into index (newest first)
    index = [e for e in _load_index() if e.get("event_id") != event_id]
    index.insert(0, {
        "event_id": event_id,
        "hash": short_hash,
        "name": config.get("core", {}).get("name", "Untitled Event"),
        "type": config.get("core", {}).get("event_type", "hackathon"),
        "mode": config.get("core", {}).get("mode", ""),
        "theme": config.get("core", {}).get("theme", ""),
        "description": config.get("core", {}).get("description", ""),
        "deployed_at": now_iso,
        "judges_count": len((config.get("judging_panel") or {}).get("judges") or []),
        "rounds_count": len(config.get("rounds") or []),
        "max_teams": (config.get("participants") or {}).get("capacity", {}).get("max_teams", 0),
        "max_participants": (config.get("participants") or {}).get("capacity", {}).get("max_participants", 0),
        "prize_pool": (config.get("prizes") or {}).get("total_pool", ""),
    })
    _save_index(index)

    return {"success": True, "event_id": event_id, "hash": short_hash, "file_path": filepath}


@router.get("/events")
async def list_deployed_events():
    return _load_index()


@router.get("/events/{hash}")
async def get_deployed_event(hash: str):
    index = _load_index()
    entry = next((e for e in index if e.get("hash") == hash), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Event not found")
    return _load_config(entry["event_id"])


@router.post("/save-config")
async def save_config(request: SaveConfigRequest):
    config = request.event_config.copy()
    event_id = request.event_id or config.get("event_id") or str(uuid.uuid4())
    config["event_id"] = event_id

    now_iso = datetime.utcnow().isoformat() + "Z"
    config.setdefault("status", {})
    config["status"]["updated_at"] = now_iso
    config["status"].setdefault("created_at", now_iso)

    filepath = _save_config(event_id, config)
    return {
        "success": True,
        "event_id": event_id,
        "file_path": filepath,
        "filename": f"event_{event_id}.json",
    }
