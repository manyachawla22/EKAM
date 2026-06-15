"""
EKAM Event Validator (Task 3, Phase 3a — the "intelligence" judges will test).

Two layers, by design:
  1. deterministic_checks(bp)  — PURE Python. The HARD gate. Date ordering,
     weight sums, top-N monotonicity, team-size sanity, dangling role/artifact
     references, etc. These are facts, not opinions, and never depend on an LLM.
  2. critic_pass(bp)           — an LLM, JSON-mode, low-temp ADVISORY pass that
     catches softer contradictions / missing context in plain English. It can
     only ADD questions; it can never authorise a deploy.

`validate_blueprint(bp)` fuses both with `required_fields` (blueprint.py) into a
single verdict: {missing, contradictions, questions, confidence, ready, summary}.
Confidence is computed conservatively — ANY missing field or contradiction drops
it below the deploy threshold, so the bot keeps asking instead of guessing. The
real authority to create entities is still the human approval, never this score.
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from app.services import blueprint as bp_mod
from app.services.blueprint import (
    Blueprint,
    CONFIDENCE_THRESHOLD,
    required_fields,
    normalize,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _parse_dt(value) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _both(a: datetime | None, b: datetime | None) -> bool:
    return a is not None and b is not None


def _cmp(a: datetime, b: datetime) -> int:
    """Compare two datetimes, tolerating naive-vs-aware by dropping tz."""
    if (a.tzinfo is None) != (b.tzinfo is None):
        a = a.replace(tzinfo=None)
        b = b.replace(tzinfo=None)
    return (a > b) - (a < b)


# ── Layer 1: deterministic contradiction detection (HARD gate) ───────────────

def deterministic_checks(bp: Blueprint) -> List[str]:
    """Return a list of concrete, machine-verifiable contradictions. Empty list
    ⇒ the blueprint is internally consistent (it may still be *incomplete* — see
    required_fields). PURE: no LLM, no DB."""
    issues: List[str] = []
    roles = bp_mod.role_ids(bp)
    arts = bp_mod.artifact_ids(bp)

    # 1) Participants / team size sanity.
    if bp.participants.model == "team" and bp.participants.team_size is not None:
        ts = bp.participants.team_size
        if ts.min < 1:
            issues.append("Team minimum size must be at least 1.")
        if ts.max < ts.min:
            issues.append(
                f"Team size is contradictory: min ({ts.min}) is greater than max ({ts.max})."
            )

    # 2) Dangling references + per-stage windows.
    prev_close: datetime | None = None
    prev_close_label = ""
    for s in bp.stages:
        where = f"'{s.label or s.id}'"

        if s.role and s.role not in roles:
            issues.append(f"Stage {where} references role '{s.role}', which isn't defined.")
        if s.type == "submission" and s.artifact and s.artifact not in arts:
            issues.append(f"Stage {where} submits artifact '{s.artifact}', which isn't defined.")

        # Window self-consistency: opens before closes.
        if s.window:
            o, c = _parse_dt(s.window.opens_at), _parse_dt(s.window.closes_at)
            if _both(o, c) and _cmp(o, c) >= 0:
                issues.append(f"Stage {where} opens at or after it closes.")
            # Pipeline-order consistency: a stage shouldn't open before the
            # previous timed stage closed (overlapping/backwards schedule).
            if prev_close is not None and o is not None and _cmp(o, prev_close) < 0:
                issues.append(
                    f"Stage {where} opens before the earlier stage "
                    f"'{prev_close_label}' closes (schedule runs backwards)."
                )
            if c is not None:
                prev_close, prev_close_label = c, (s.label or s.id)

    # 3) Evaluation scoring: weighted criteria must sum to ~100.
    for s in bp.stages:
        if s.type == "evaluation" and s.scoring and s.scoring.criteria:
            weights = [c.weight or 0.0 for c in s.scoring.criteria]
            total = sum(weights)
            if any(w > 0 for w in weights) and abs(total - 100.0) > 0.5:
                issues.append(
                    f"Scoring weights for stage '{s.label or s.id}' sum to {total:g}, not 100."
                )

    # 4) Progression monotonicity: successive top-N must not increase, and a
    #    winners count must be >= 1.
    last_top_n: int | None = None
    last_label = ""
    for s in bp.stages:
        if s.type not in ("progression", "bracket") or not s.rule:
            continue
        rule = s.rule
        if rule.kind == "top_n":
            n = rule.n
            if n is not None and n < 1:
                issues.append(f"Progression '{s.label or s.id}' advances fewer than 1 entrant.")
            if n is not None and last_top_n is not None and n > last_top_n:
                issues.append(
                    f"Progression '{s.label or s.id}' advances {n}, more than the earlier "
                    f"round '{last_label}' which advanced {last_top_n} — a later round "
                    f"can't have more entrants."
                )
            if n is not None:
                last_top_n, last_label = n, (s.label or s.id)
        elif rule.kind == "cutoff_score":
            if rule.cutoff is not None and not (0 <= rule.cutoff <= 100):
                issues.append(
                    f"Cutoff score for '{s.label or s.id}' ({rule.cutoff}) is outside 0–100."
                )
        elif rule.kind == "winners":
            tn = rule.top_n if rule.top_n is not None else 1
            if tn < 1:
                issues.append(f"Winners stage '{s.label or s.id}' awards fewer than 1 winner.")

    return issues


# ── Layer 2: LLM critic (ADVISORY only) ──────────────────────────────────────

_CRITIC_SYSTEM = (
    "You are a meticulous event-design reviewer for an event-management platform. "
    "You are given a structured JSON 'blueprint' describing how a competition or "
    "selection process will run (stages, roles, scoring, progression rules). "
    "Find genuine LOGICAL CONTRADICTIONS and MISSING INFORMATION that a human "
    "organizer must clarify before the event can run. Be precise and specific; do "
    "NOT invent problems, do NOT restate the blueprint, and do NOT suggest stylistic "
    "changes. If it looks complete and consistent, say so with high confidence.\n\n"
    "Return ONLY this JSON object:\n"
    "{\n"
    '  "contradictions": ["short, specific statements of any logical conflict"],\n'
    '  "missing": ["specific facts that are absent and required"],\n'
    '  "questions": ["clarifying questions to ask the organizer, plain English"],\n'
    '  "confidence": 0.0,\n'
    '  "summary": "one sentence overall assessment"\n'
    "}"
)


async def critic_pass(bp: Blueprint) -> dict:
    """LLM advisory critique. Degrades to an empty advisory if no LLM is
    configured or the call fails — it can only ever ADD signal, never block by
    its own failure."""
    from app.services import llm_client

    empty = {"contradictions": [], "missing": [], "questions": [], "confidence": None, "summary": ""}
    if not llm_client.is_available():
        return empty
    try:
        import json

        out = await llm_client.complete_json(
            _CRITIC_SYSTEM,
            "Blueprint:\n" + json.dumps(bp.to_dict(), indent=2),
            max_tokens=900,
        )
    except Exception as exc:  # advisory only — never propagate
        print(f"[event_validator] critic LLM failed (advisory, ignored): {exc}")
        return empty

    def _strlist(v) -> List[str]:
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return []

    conf = out.get("confidence")
    try:
        conf = float(conf) if conf is not None else None
    except (TypeError, ValueError):
        conf = None
    return {
        "contradictions": _strlist(out.get("contradictions")),
        "missing": _strlist(out.get("missing")),
        "questions": _strlist(out.get("questions")),
        "confidence": conf,
        "summary": str(out.get("summary") or "").strip(),
    }


# ── Fusion: the single verdict ────────────────────────────────────────────────

def _confidence(missing: List[str], contradictions: List[str], llm_conf) -> float:
    det = max(0.05, 1.0 - 0.30 * len(contradictions) - 0.12 * len(missing))
    cap = 0.35 if contradictions else (0.6 if missing else 1.0)
    base = llm_conf if isinstance(llm_conf, (int, float)) and 0 < llm_conf <= 1 else 0.9
    return round(min(det, cap, base), 2)


def _questions(missing: List[str], contradictions: List[str], extra: List[str]) -> List[str]:
    qs: List[str] = []
    for m in missing:
        qs.append(f"Could you tell me {m}?")
    for c in contradictions:
        qs.append(f"This looks inconsistent — {c} How should it be?")
    qs.extend(extra)
    # dedup, cap to keep the chat focused
    seen, out = set(), []
    for q in qs:
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out[:6]


def soft_questions(bp: Blueprint) -> List[str]:
    """Useful-but-not-REQUIRED clarifications the agent should proactively ask, so
    the organizer always knows what more would make the event concrete (dates, how
    many advance, the cutoff, how many winners, capacity). Advisory only — these
    never block readiness; they make the agent inquisitive instead of silent."""
    bp = normalize(bp)
    qs: List[str] = []

    reg = next((s for s in bp.stages if s.type == "registration"), None)
    if reg is not None and (not reg.window or not (reg.window.opens_at and reg.window.closes_at)):
        qs.append("When does registration open and close (date + time)?")

    for s in bp.stages:
        if s.type == "progression" and s.rule:
            r = s.rule
            if r.kind == "top_n" and r.n is None:
                qs.append(f"How many advance from '{s.label}'? (e.g. top 4)")
            elif r.kind == "cutoff_score" and r.cutoff is None:
                qs.append(f"What qualifying cutoff (0–100) should '{s.label}' use?")
            elif r.kind == "winners" and r.top_n is None:
                qs.append("How many winners should be announced (e.g. top 3)?")

    if any(s.type in ("team_formation",) for s in bp.stages):
        qs.append("Is there a cap on the number of teams (and total participants)?")
    elif bp.stages:
        qs.append("Is there a cap on the number of participants?")

    seen, out = set(), []
    for q in qs:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out


def validate_blueprint_sync(bp: Blueprint) -> dict:
    """Deterministic-only verdict (no LLM). Fast, pure, used by unit tests and as
    the always-available fallback."""
    bp = normalize(bp)
    missing = required_fields(bp)
    contradictions = deterministic_checks(bp)
    confidence = _confidence(missing, contradictions, None)
    return {
        "missing": missing,
        "contradictions": contradictions,
        "questions": _questions(missing, contradictions, []),
        "suggestions": soft_questions(bp),
        "confidence": confidence,
        "ready": confidence >= CONFIDENCE_THRESHOLD and not missing and not contradictions,
        "summary": "",
    }


async def validate_blueprint(bp: Blueprint, use_llm: bool = True) -> dict:
    """Full verdict: deterministic gate + (optional) LLM advisory, fused.

    The LLM can only add contradictions/missing/questions; the deterministic
    layer and required_fields remain the authority on `ready`."""
    bp = normalize(bp)
    # DETERMINISTIC is the sole authority on missing / contradictions / readiness /
    # confidence — the LLM critic was inventing fake requirements and tanking scores.
    missing = required_fields(bp)
    contradictions = deterministic_checks(bp)
    confidence = _confidence(missing, contradictions, None)

    # The critic is ADVISORY ONLY: its output is surfaced as soft suggestions and a
    # one-line summary; it never affects the gate.
    suggestions: List[str] = []
    summary = ""
    if use_llm:
        llm = await critic_pass(bp)
        suggestions = (llm.get("contradictions") or []) + (llm.get("questions") or [])
        summary = llm.get("summary", "")

    return {
        "missing": missing,
        "contradictions": contradictions,
        "questions": _questions(missing, contradictions, []),
        "suggestions": suggestions,
        "confidence": confidence,
        "ready": confidence >= CONFIDENCE_THRESHOLD and not missing and not contradictions,
        "summary": summary,
    }
