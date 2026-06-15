"""
EKAM blueprint extraction eval harness.

The doc's own recommended test (possible.md, Failure Mode 1): feed a spread of
event descriptions through the AI extractor and print the resulting blueprint, so a
prompt edit can be checked for regressions BEFORE it ships. Covers the 7 known types
plus a couple of "unknown" formats (debate, scholarship, MUN) the agent must map onto
the primitives.

Run from the backend/ directory:

    python scripts/eval_blueprints.py

Needs an LLM key (GEMINI_API_KEY or GROQ_API_KEY) for real extraction; without one
it still runs and prints the deterministic structure (empty), so it never crashes.
This is a DEV tool — it makes no DB calls and creates nothing.
"""

import asyncio
import os
import sys

# Make `import app...` work when run as `python scripts/eval_blueprints.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The summary uses box-drawing/arrow glyphs; force UTF-8 so a cp1252 console
# (Windows default) doesn't crash on them.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.services import llm_client  # noqa: E402
from app.services.blueprint_synth import extract_blueprint_from_conversation  # noqa: E402
from app.services.event_validator import validate_blueprint_sync  # noqa: E402


# (label, description) — one per row. Mix of the 7 known types + unknown formats,
# and deliberately uses SYNONYMS (not the type name) to test semantic mapping.
CASES: list[tuple[str, str]] = [
    ("hackathon",
     "Run a 36-hour hackathon, teams of 4, two tracks AI and Health. Teams submit an "
     "idea deck, top 10 build a working demo judged by our 3 mentors. Opens now, closes "
     "in 5 days."),
    ("ideathon (individual)",
     "Solo idea competition: everyone submits a one-page concept, we screen them, then "
     "the best 8 pitch live to a panel."),
    ("case competition",
     "Business case competition for teams of 3. They submit a solution report, the top "
     "5 present live to the jury."),
    ("CTF (auto)",
     "Individual capture-the-flag, players submit flags, scored automatically on a "
     "leaderboard, top 15 go to the finals."),
    ("quiz (synonym: written test)",
     "An online aptitude test — I'll give a question paper bank, each participant gets "
     "20 random questions and uploads one answer sheet. We grade per question."),
    ("tournament (esports)",
     "Valorant 5v5 single-elimination knockout. Referees score each match and I'll "
     "upload the match links. Winner of the final takes it."),
    ("symposium (blind)",
     "Research symposium: authors submit abstracts, double-blind review by our "
     "committee, accepted abstracts present at the conference."),
    ("scholarship (unknown)",
     "A merit scholarship: students apply with an essay and transcript, a committee "
     "reviews and scores them, we award the top 3."),
    ("debate (unknown)",
     "An inter-college debate: teams of 2, knockout rounds judged live by adjudicators, "
     "best team wins."),
    ("MUN (unknown)",
     "Model UN: delegates register individually with their country preference, "
     "committees run live and chairs score participation, top delegates get awards."),
]


def _summary(bp_dict: dict) -> dict:
    stages = bp_dict.get("stages") or []
    def beh(t):
        out = []
        for s in stages:
            if s.get("type") == t:
                out += s.get("behaviors") or []
        return out
    has_live = False
    pending_sub = False
    for s in stages:
        if s.get("type") == "submission":
            pending_sub = True
        elif s.get("type") == "evaluation":
            if not pending_sub:
                has_live = True
            pending_sub = False
    return {
        "auto": any((s.get("scoring") or {}).get("method") == "auto"
                    for s in stages if s.get("type") == "evaluation"),
        "anonymous": "anonymous_review" in beh("evaluation"),
        "quiz": "quiz" in (beh("evaluation") + beh("submission")),
        "bracket": any(s.get("type") == "bracket" for s in stages),
        "live": has_live,
    }


async def main() -> None:
    print(f"LLM available: {llm_client.is_available()}  "
          f"(provider={os.getenv('LLM_PROVIDER', 'gemini')})\n")
    wrong = 0
    for label, desc in CASES:
        bp, judges = await extract_blueprint_from_conversation([desc])
        bpd = bp.to_dict()
        verdict = validate_blueprint_sync(bp)
        flags = _summary(bpd)
        flow = " → ".join(f"{s.get('type')}" for s in (bpd.get("stages") or []))
        roles = ", ".join(f"{r.get('kind')}:{r.get('label')}" for r in (bpd.get("roles") or []))
        ok = bool(bpd.get("event_name")) and bool(bpd.get("stages"))
        if not ok:
            wrong += 1
        print(f"── {label}")
        print(f"   name={bpd.get('event_name')!r}  format={bpd.get('format_label')!r}  "
              f"model={(bpd.get('participants') or {}).get('model')}")
        print(f"   flow: {flow}")
        print(f"   roles: {roles}")
        print(f"   flags: {flags}  judges={len(judges)}")
        print(f"   verdict: ready={verdict['ready']}  "
              f"missing={verdict['missing']}  contradictions={verdict['contradictions']}")
        print()
    print(f"Done. {len(CASES) - wrong}/{len(CASES)} produced a named, staged blueprint.")


if __name__ == "__main__":
    asyncio.run(main())
