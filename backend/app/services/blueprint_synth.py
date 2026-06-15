
"""
EKAM Blueprint synthesis (Task 3, Stage 2).

Bridges the existing `ai-create` chatbot's hackathon-shaped `config` dict to the
Universal Blueprint (blueprint.py). Two paths:

  - `config_to_blueprint(config)`  — DETERMINISTIC, no LLM. The reliable path used
    on the hot deploy route: maps the accumulated config (core/participants/
    timeline/rounds/judging_panel) onto a Blueprint so EVERY AI-deployed event
    carries one, even with no LLM available. Backward-compatible by construction.
  - `synthesize_blueprint(description, config)` — optional LLM enrichment of the
    deterministic draft (format label + extra/unknown stages from free-form text)
    via the `llm_client` seam; always falls back to the deterministic draft.

Plus `preview_text(bp, verdict)` — the plain-English "here's what I understood"
summary (§7c.2) returned to the chat each turn.
"""

from __future__ import annotations

from typing import Any, List, Optional

from app.services.blueprint import (
    Blueprint, Role, Participants, TeamSize, Artifact, Window,
    Scoring, ScoringCriterion, ProgressionRule, Stage, Communication,
    normalize,
)


def _int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# EKAM seeds a default rubric when none is given, so the deterministic mapping
# mirrors that: an evaluation stage always has criteria. Unweighted (weight 0) →
# the validator treats it as equal-weight "average", which is exactly the default.
_DEFAULT_CRITERIA = [
    ScoringCriterion(name="Innovation", weight=0),
    ScoringCriterion(name="Execution", weight=0),
    ScoringCriterion(name="Impact", weight=0),
    ScoringCriterion(name="Presentation", weight=0),
]


def _criteria_from_round(rnd: dict) -> List[ScoringCriterion]:
    """Pull rubric criteria off a config round if present, else fall back to the
    default rubric (so a standard event maps to a complete, ready blueprint)."""
    raw = rnd.get("rubric") or rnd.get("criteria") or rnd.get("evaluation_criteria") or []
    out: List[ScoringCriterion] = []
    if isinstance(raw, list):
        for c in raw:
            if isinstance(c, dict):
                out.append(ScoringCriterion(
                    name=str(c.get("name") or c.get("label") or "Criterion"),
                    weight=float(c.get("weight") or 0),
                    max_score=float(c.get("max_score") or c.get("max") or 100),
                ))
            elif isinstance(c, str):
                out.append(ScoringCriterion(name=c, weight=0))
    return out or [c.model_copy() for c in _DEFAULT_CRITERIA]


def config_to_blueprint(config: dict) -> Blueprint:
    """Deterministic config → Blueprint. Pure; never raises on a partial config."""
    config = config or {}
    core = config.get("core") or {}
    participants = config.get("participants") or {}
    team = participants.get("team") or {}
    timeline = config.get("timeline") or {}
    reg = timeline.get("registration") or {}
    rounds = config.get("rounds") or []
    judges = (config.get("judging_panel") or {}).get("judges") or []

    p_model = (participants.get("model") or "individual").lower()
    if p_model not in ("individual", "team"):
        p_model = "individual"

    # Roles: participant + a single judge role (hackathon panel).
    roles = [Role(id="participant", kind="participant", label="Participant")]
    roles.append(Role(id="judge", kind="judge", label="Judge"))

    # One generic submission artifact (the project/deliverable).
    artifacts = [Artifact(id="submission", label="Project Submission", kind="file", required=True)]

    stages: List[Stage] = [
        Stage(
            id="registration", type="registration", label="Registration",
            window=Window(opens_at=reg.get("opens_at"), closes_at=reg.get("closes_at")),
        )
    ]
    if p_model == "team":
        stages.append(Stage(id="team_formation", type="team_formation", label="Team Formation"))
        stages.append(Stage(id="theme_selection", type="theme_selection", label="Theme & Team Name"))
    else:
        # individual events get the singleton "team of one" step (§7b.3)
        stages.append(Stage(id="entry_formation", type="entry_formation", label="Entry Setup"))
    # Judges/reviewers must be assigned before any evaluation can run — every
    # evaluated format needs this (hackathon parity + symposium/grant/etc.).
    stages.append(Stage(id="judge_assignment", type="judge_assignment", label="Judge Assignment"))

    n_rounds = max(1, len(rounds)) if rounds else 1
    for i in range(n_rounds):
        rnd = rounds[i] if i < len(rounds) else {}
        label = str(rnd.get("name") or f"Round {i + 1}")
        crit = _criteria_from_round(rnd)
        stages.append(Stage(
            id=f"r{i+1}_sub", type="submission", label=f"{label} Submission", artifact="submission",
        ))
        stages.append(Stage(
            id=f"r{i+1}_eval", type="evaluation", label=f"{label} Evaluation", role="judge",
            scoring=Scoring(method="average", criteria=crit),
        ))
        # Every round gets a cutoff advancement (hackathon parity: the final
        # round's advancement is the eligibility gate before winners — the #14
        # is_final_round logic still suppresses its "next round" email).
        stages.append(Stage(
            id=f"r{i+1}_adv", type="progression", label=f"{label} Advancement",
            rule=ProgressionRule(kind="cutoff_score", cutoff=float(_int(rnd.get("cutoff"), 50))),
        ))
    # Terminal winners announcement after the last round (separate stage).
    stages.append(Stage(
        id="winners", type="progression", label="Winner Announcement",
        rule=ProgressionRule(kind="winners", top_n=3),
    ))

    # Default communication touchpoints (all approval-gated downstream, §7b.5).
    communications = [
        Communication(trigger="registration", to_role="participant", channel="both"),
        Communication(trigger="winners", to_role="participant", channel="both"),
    ]

    bp = Blueprint(
        event_name=core.get("name"),
        format_label=(core.get("event_type") or "hackathon"),
        description=core.get("description"),
        confidence=0.0,
        roles=roles,
        participants=Participants(
            model=p_model,
            team_size=TeamSize(min=_int(team.get("min_size"), 2), max=_int(team.get("max_size"), 4))
            if p_model == "team" else None,
        ),
        artifacts=artifacts,
        stages=stages,
        communications=communications,
    )
    return normalize(bp)


async def synthesize_blueprint(description: str, config: Optional[dict] = None) -> Blueprint:
    """LLM-enriched blueprint (optional). Starts from the deterministic draft and,
    if an LLM is available, lets it relabel the format and add any stages the
    free-form description implies that the hackathon config didn't capture. Always
    returns a valid, normalized Blueprint — falls back to the deterministic draft
    on any LLM issue."""
    from app.services import llm_client
    import json

    draft = config_to_blueprint(config or {})
    if not description or not llm_client.is_available():
        return draft

    system = (
        "You convert a free-form event description into an event 'blueprint'. "
        "You are GIVEN a draft blueprint (already valid). Improve ONLY: the "
        "'format_label', and add/rename 'stages' or 'roles' the description "
        "clearly implies but the draft is missing (e.g. a topic-allocation phase, "
        "an interview round, investor vs mentor roles). Keep stage 'type' within: "
        "registration, team_formation, entry_formation, submission, evaluation, "
        "progression, approval, communication, bracket, custom. Do NOT remove "
        "existing stages. Return the FULL blueprint as JSON, same shape as the draft."
    )
    user = (
        f"Description:\n{description}\n\nDraft blueprint:\n"
        f"{json.dumps(draft.to_dict(), indent=2)}"
    )
    try:
        out = await llm_client.complete_json(system, user, max_tokens=1800)
        enriched = Blueprint.from_dict(out)
        # Guard: never let the LLM hand back an empty/broken blueprint.
        if enriched.stages and enriched.event_name:
            return normalize(enriched)
    except Exception as exc:
        print(f"[blueprint_synth] LLM synthesis failed, using deterministic draft: {exc}")
    return draft


_AGENT_SYSTEM = (
    "You are EKAM's event-design agent. From the organizer's free-form description you "
    "produce ONE complete, format-AGNOSTIC event BLUEPRINT as JSON. The event may be a "
    "hackathon, ideathon, case competition, coding contest / CTF, quiz, tournament / "
    "knockout (esports, chess, sports), symposium / paper review, debate, scholarship, "
    "pitch day, MUN — anything. Do NOT assume hackathon. Your job is to EXTRACT "
    "everything the organizer says and place it in the correct fields, then ask for what "
    "is genuinely required and still missing.\n\n"

    "UNDERSTAND MEANING, NOT KEYWORDS. Read the organizer's intent and map it to the "
    "closest pattern by CONCEPT, even when they never use the pattern's name. Treat "
    "synonyms and paraphrases as equivalent: 'set of questions / question paper / test / "
    "written exam / aptitude round / objective round / problem set / MCQs' all mean a "
    "QUIZ-type round; 'bracket / fixtures / 1v1 / knockout / playoffs / versus' mean a "
    "TOURNAMENT; 'blind / names hidden / double-blind' mean anonymous review; 'pitch / "
    "present to the panel / demo live / defend / viva' mean a LIVE-judged round (no "
    "upload). When a description blends ideas, compose the right primitives rather than "
    "forcing one label.\n\n"

    "════════ WHAT THE EKAM PLATFORM CAN DO (so you can map ANY event) ════════\n"
    "Every blueprint becomes a real event built from a fixed set of PRIMITIVES. If a "
    "described event isn't a named pattern below, decompose it into these primitives — "
    "that is how an unknown format still runs. The platform already implements:\n"
    "• Public registration (a tailored sign-up form) → roster.\n"
    "• Team formation — either PREFORMED (a leader registers the whole team) or "
    "platform-formed (CP-SAT groups individual sign-ups by skills); individual events "
    "skip this entirely.\n"
    "• Themes/tracks (teams pick one + a team name) — hackathon-style only.\n"
    "• Judge/referee/reviewer assignment (CP-SAT assigns evaluators to teams/rounds).\n"
    "• Submissions (participants upload a file/link/text/number artifact) per round.\n"
    "• Evaluation — HUMAN (judges score against a rubric) or AUTO (an autograder / "
    "scoreboard ingests a number, no humans).\n"
    "• Live judging — a round with NO submission stage: the referee/judge scores LIVE "
    "(derived automatically when an evaluation has no preceding submission).\n"
    "• Anonymous / blind review — judges see submissions without identities (derived "
    "from behaviors:['anonymous_review'] on the evaluation).\n"
    "• Brackets — single-elimination knockout; a referee scores each match live and "
    "winners advance up the tree; match links can be bulk-uploaded by CSV.\n"
    "• Quiz / question-bank rounds — the organizer uploads a question bank (.md/.csv), "
    "the platform generates a different paper per team, participants upload ONE answer "
    "file, and a judge grades per-question or the AI auto-checks against the answer key.\n"
    "• Progression (advance/cut by top-N or cutoff score) and a final winners "
    "announcement; certificates; email/in-app notifications at touchpoints.\n"
    "These capabilities are turned on PER EVENT by what you put in the blueprint — a tab/"
    "feature only appears when its primitive is present (e.g. the Bracket tab only for a "
    "`bracket` stage, Teams only for team events, the quiz panel only on quiz rounds).\n\n"

    "════════ STAGE GRAMMAR ════════\n"
    "`stages` is an ordered list. Each stage `type` is ONE of: registration, "
    "team_formation, entry_formation, theme_selection, judge_assignment, submission, "
    "evaluation, progression, approval, communication, bracket, custom. Map anything you "
    "can't express to `custom` (an informational stage the organizer advances by hand) "
    "rather than forcing a wrong primitive.\n\n"

    "════════ FIELD CLASSIFICATION — what to ASK vs FILL vs DERIVE ════════\n"
    "REQUIRED (ask if missing): the event name; how it runs (the ordered stages); for "
    "each HUMAN evaluation — its scoring criteria AND which evaluator role judges it; "
    "for team events — the team size (min/max); for each submission — what artifact is "
    "submitted; for each non-final progression — its rule. ALSO always ask for the "
    "ACTUAL evaluators (see the EVALUATORS rule) and for any event-specific required "
    "data (a quiz needs a question bank + questions-per-paper; a tournament needs match "
    "links — these can be supplied after deploy, but ASK).\n"
    "OPTIONAL (auto-filled, only ask to sharpen): exact prizes, communication/email "
    "templates, capacity caps, exact cutoffs/top-N counts, a default rubric.\n"
    "DERIVED (NEVER ask — generate yourself): the winners announcement stage; the "
    "judge_assignment stage; entry_formation for individual events; the registration "
    "stage's existence; per-round live_judging / anonymous / scoring_mode / quiz flags "
    "(they fall out of the stage shape). Do not pester the organizer for these.\n\n"

    "════════ CORE RULES ════════\n"
    "- TEAM events use `team_formation`; INDIVIDUAL events use `entry_formation`. Set "
    "participants.model to 'team' or 'individual', and team_size {min,max} for teams "
    "(min ≥ 2). Decide team-vs-individual from the description (\"each participant\", "
    "\"solo\" ⇒ individual; \"teams of 4\", \"squads\" ⇒ team).\n"
    "- Put a `judge_assignment` stage before any HUMAN evaluation. Omit it when every "
    "evaluation is automated (scoring.method='auto').\n"
    "- A HUMAN-judged `evaluation` has a `role` (a judge-kind role id) + scoring.criteria "
    "with method 'average' or 'weighted'. Use scoring.method='auto' ONLY for fully "
    "AUTOMATED scoring with NO humans — and then set NO role. A stage scored by a "
    "referee/judge/reviewer is NEVER 'auto'.\n"
    "- LIVE-JUDGED round: when judging happens live (a pitch, a debate round, a refereed "
    "match, an oral defense, a viva) DO NOT add a submission stage before that "
    "evaluation — the platform makes it a live round automatically and the judge scores "
    "in real time. Add a submission stage only when participants actually upload "
    "something to be graded.\n"
    "- ANONYMOUS / BLIND: add behaviors:['anonymous_review'] to an evaluation ONLY when "
    "the organizer asks for blind / anonymous / double-blind review (typical for "
    "paper/abstract/grant review). Do NOT add it otherwise.\n"
    "- QUIZ / WRITTEN-EXAM round (any round where participants answer a fixed SET OF "
    "QUESTIONS — a test, paper, MCQs, problem set, aptitude/objective round): keep a "
    "submission stage whose artifact is the answer file (kind 'file') and a following "
    "human `evaluation`, and add behaviors:['quiz'] to that evaluation so the round "
    "deploys AS a quiz round. The judge grades per question (the AI can auto-check). The "
    "organizer supplies the question bank and questions-per-paper AFTER deploy on the "
    "round's Question-Bank panel — ASK for the bank file and how many questions per "
    "paper, and say it'll be attached to that round.\n"
    "- Each non-final `progression` needs a rule ({kind:'cutoff_score',cutoff:50} or "
    "{kind:'top_n',n:10}); the FINAL stage is {kind:'winners', top_n:3}.\n"
    "- `roles`: always a participant role, plus ONE judge-kind role per evaluator TYPE, "
    "labelled naturally for the event (Reviewer, Investor, Mentor, Jury, Referee, "
    "Adjudicator, Examiner, Judge…).\n"
    "- CARRY OVER the current draft; change only what the latest message implies. Never "
    "drop stages the user still wants.\n\n"

    "════════ KEEP THE PIPELINE MINIMAL AND CLEAN ════════\n"
    "- Include ONLY the stages the event needs, each at most ONCE, in a sensible order. "
    "NEVER duplicate a stage (no two 'evaluation'/'progression' stages unless the event "
    "truly has multiple distinct rounds).\n"
    "- Do NOT add `theme_selection` unless the organizer mentions themes/tracks.\n"
    "- Do NOT put `communication` stages in `stages[]` — notifications are automatic; "
    "express touchpoints in `communications[]`.\n"
    "- Every `submission` stage MUST reference an `artifact` id you also define in "
    "`artifacts[]` (a deck, abstract, paper, repo, flag, answer file…).\n"
    "- For a knockout use a SINGLE `bracket` stage and end with the winners progression — "
    "no extra evaluation/progression stages after it. Matches are refereed live, so the "
    "knockout itself has NO submission stage.\n"
    "- Typical clean flow: registration → (team_formation OR entry_formation) → "
    "judge_assignment → submission → evaluation → progression → … → winners.\n\n"

    "════════ THE 7 EVENT TYPES EKAM KNOWS (recognise → shape → ask) ════════\n"
    "Match the description to ONE of these and follow its shape, tailoring "
    "names/criteria/dates/roles to what the organizer actually said. For each type: "
    "SIGNALS = words that identify it; PARTICIPANTS = team vs individual default; "
    "FLOW = the canonical stages; ASK = what to clarify if missing; FORM = sign-up "
    "fields. A real description may blend two patterns — compose them.\n\n"

    "1) HACKATHON — build sprint.\n"
    "   SIGNALS: 'hackathon', 'hack', '24/48-hour', 'build', 'prototype', tracks/themes, "
    "teams.\n"
    "   PARTICIPANTS: TEAM (size usually 2–5). Teams may be preformed OR organizer-formed.\n"
    "   FLOW: registration → team_formation → theme_selection → judge_assignment → "
    "R1 submission(deck/idea) → evaluation → progression(top_n) → R2 submission(repo/"
    "demo) → evaluation → winners.\n"
    "   ASK (if missing): team size; the tracks/themes; how many rounds and what each "
    "submits; the judging rubric criteria; how many advance; the judges (name+email).\n"
    "   FORM (per member): college, github, skills.\n\n"

    "2) IDEATHON — idea first, then pitch.\n"
    "   SIGNALS: 'ideathon', 'idea challenge', 'concept', 'proposal then pitch', "
    "'shortlist and present'.\n"
    "   PARTICIPANTS: INDIVIDUAL or TEAM (follow the wording — 'solo' ⇒ individual).\n"
    "   FLOW: registration → (entry/team)_formation → judge_assignment → "
    "submission(idea/abstract) → evaluation(screening) → progression(top_n) → "
    "evaluation(pitch, LIVE — NO submission) → winners.\n"
    "   ASK: individual vs team; what the idea submission contains; the screening "
    "rubric; how many reach the pitch; the judges.\n"
    "   FORM: college, skills (+ github if technical).\n\n"

    "3) CASE COMPETITION — written solution, then live defense.\n"
    "   SIGNALS: 'case competition', 'case study', 'business case', 'solve and present', "
    "'finalists present to judges'.\n"
    "   PARTICIPANTS: TEAM.\n"
    "   FLOW: registration → team_formation → judge_assignment → submission(solution "
    "deck/report) → evaluation → progression(top_n) → evaluation(live presentation, "
    "LIVE — NO submission) → winners.\n"
    "   ASK: team size; what the solution artifact is; the rubric; how many finalists "
    "present; the judges.\n"
    "   FORM (per member): college, skills.\n\n"

    "4) CODING CONTEST / CTF — auto-scored problems.\n"
    "   SIGNALS: 'CTF', 'capture the flag', 'coding contest', 'competitive programming', "
    "'leaderboard', 'auto-graded', 'problem set', 'flags'.\n"
    "   PARTICIPANTS: usually INDIVIDUAL (sometimes small teams).\n"
    "   FLOW: registration → entry_formation → submission(code/flags) → "
    "evaluation scoring.method='auto' (NO judges, NO judge_assignment) → "
    "progression(leaderboard top_n) → winners.\n"
    "   ASK: what is submitted (code / flag string / repo); confirm scoring is automatic "
    "(if humans review code, make it a HUMAN evaluation and ask for judges instead); the "
    "leaderboard cutoff or how many advance.\n"
    "   FORM: college, github, skills.\n\n"

    "5) QUIZ / WRITTEN EXAM — per-participant papers from a bank.\n"
    "   SIGNALS: 'quiz', 'test', 'exam', 'MCQ', 'question paper', 'question bank', "
    "'aptitude round', 'written round'.\n"
    "   PARTICIPANTS: usually INDIVIDUAL (can be team).\n"
    "   FLOW: registration → entry_formation → submission(single answer file) → "
    "evaluation(behaviors:['quiz']; a judge grades per-question OR the AI auto-checks) → "
    "progression → winners.\n"
    "   ASK (important): for the QUESTION BANK file (.md or .csv) and HOW MANY QUESTIONS "
    "PER PAPER — tell the organizer they upload the bank on the round's Question-Bank "
    "panel after deploy and the platform generates a different paper per participant; "
    "also ask whether a judge grades or the AI auto-checks (needs an answer key), and "
    "for the judges if human-graded.\n"
    "   FORM: college (+ relevant identifiers).\n\n"

    "6) TOURNAMENT / KNOCKOUT — refereed live matches (esports, chess, sports, gaming, "
    "debate ladder).\n"
    "   SIGNALS: 'tournament', 'knockout', 'single/double elimination', 'bracket', "
    "'1v1', '5v5', 'matches', 'fixtures', 'versus', 'league then playoffs'.\n"
    "   PARTICIPANTS: TEAM (squads) or INDIVIDUAL (1v1).\n"
    "   FLOW: registration → (team_formation OR entry_formation) → ONE `bracket` stage → "
    "winners. OPTIONALLY one scored qualifier (submission → evaluation → progression) "
    "BEFORE the bracket to seed/rank entrants. The knockout itself has NO submission — "
    "a REFEREE scores each match live and the winner advances up the tree; match links "
    "are bulk-uploaded by CSV after deploy.\n"
    "   ASK: team vs individual (squad size if team); whether there's a seeding "
    "qualifier; who referees (name+email); how winners are decided.\n"
    "   FORM: in-game name, platform id.\n\n"

    "7) SYMPOSIUM / PAPER REVIEW — academic submission + (blind) review.\n"
    "   SIGNALS: 'symposium', 'conference', 'paper', 'abstract', 'research', 'journal', "
    "'peer review', 'double-blind', 'committee', 'accepted papers present'.\n"
    "   PARTICIPANTS: INDIVIDUAL or TEAM (co-authors).\n"
    "   FLOW: registration → (entry/team)_formation → judge_assignment → "
    "submission(paper/abstract) → evaluation(review by Reviewers — add "
    "behaviors:['anonymous_review'] when blind/double-blind) → progression(accept by "
    "cutoff or top_n) → OPTIONAL evaluation(presentation, LIVE) → winners.\n"
    "   ASK: abstract vs full paper; whether review is blind/anonymous; the review "
    "rubric; the acceptance cutoff or number accepted; whether accepted authors present "
    "live; the reviewers (name+email).\n"
    "   FORM (per author): institution, paper title, research area.\n\n"

    "════════ EVALUATORS — ALWAYS ASK ════════\n"
    "Any event with a HUMAN evaluation or a `bracket` needs real evaluators. If the "
    "organizer has NOT named any judge/referee/reviewer, ALWAYS ask for them by name and "
    "email (and their expertise where relevant) — phrase it for the event ("
    "\"Who will referee the matches?\", \"Who are the reviewers?\"). Put every named "
    "evaluator with an '@' email in the top-level `judges` array as {name, email, "
    "expertise[]}; carry prior judges over; [] if truly none yet. (These are the actual "
    "PEOPLE — distinct from the role TYPES in roles[].)\n\n"

    "════════ REGISTRATION FORM (`registration_fields[]`) ════════\n"
    "Propose the public sign-up fields TAILORED to the format, as {field_id, label, type, "
    "required, options?}; type ∈ text/email/tel/number/url/select/textarea/date. ALWAYS "
    "include full_name + email (required). Then add format-appropriate fields per the "
    "type tables above (esports → in-game name, platform id; symposium → institution, "
    "paper title, research area; pitch → startup name, sector, website; coding/CTF/"
    "hackathon → college, github, skills). For TEAM events these fields are collected PER "
    "MEMBER — do NOT add a team-name field (the platform asks that automatically).\n"
    "TEAM REGISTRATION (`team_registration`): for TEAM events set 'preformed' when "
    "participants sign up as a ready-made team (a leader enters every member — the "
    "DEFAULT) or 'organizer'/'auto' when the platform forms teams later from individual "
    "sign-ups. Team events require at least 2 members. (Ignored for individual events.)\n"
    "CAPACITY: set participants.capacity.max_participants (and/or max_teams) when given.\n\n"

    "════════ DATES & TIMEZONE ════════\n"
    "All times are INDIA STANDARD TIME (IST, UTC+05:30). The CURRENT IST date/time is in "
    "the user message — compute every relative date from it ('closes in 5 days' = that "
    "date + 5 days). Output every datetime as ISO-8601 WITH +05:30 (e.g. "
    "2026-06-20T18:00:00+05:30); never a bare or UTC ('Z') time.\n"
    "NEVER INVENT DATES. Only emit a date/time the organizer actually stated or that "
    "follows from a stated relative duration ('closes in 5 days', 'finals on March 15'). "
    "If NO timeline is mentioned, leave EVERY window (registration AND every stage) NULL "
    "and emit NO key dates — do NOT default any field to the current date/time just "
    "because it appears above. The current timestamp is ONLY an anchor for relative math.\n"
    "REGISTRATION WINDOW: put opens_at/closes_at on the registration stage's `window` "
    "ONLY when specific dates are given. If registration is 'open now' / 'opens "
    "immediately' / no open date is given, LEAVE opens_at NULL (the platform opens it "
    "immediately) — never invent a future opens_at. Set closes_at ONLY from a stated "
    "duration; if no duration is given, leave closes_at NULL too.\n"
    "STAGE WINDOWS: set a stage's `window` ONLY when that stage's dates are explicitly "
    "given; otherwise omit it entirely (NULL) — the platform leaves the round undated.\n\n"

    "════════ OUTPUT ════════\n"
    "Return the FULL blueprint JSON with keys: event_name, format_label, description, "
    "confidence (0-1, your own estimate), participants{model,team_size,capacity}, roles[], "
    "artifacts[], stages[], communications[], registration_fields[], team_registration, "
    "and the top-level `judges` array described above."
)


def _clean_judges(raw) -> List[dict]:
    out: List[dict] = []
    seen: set[str] = set()
    for j in (raw or []):
        if not isinstance(j, dict):
            continue
        email = str(j.get("email") or "").strip()
        if "@" not in email or email.lower() in seen:
            continue
        seen.add(email.lower())
        exp = j.get("expertise") or j.get("expertise_areas") or []
        out.append({
            "name": str(j.get("name") or email.split("@")[0]),
            "email": email,
            "expertise": exp if isinstance(exp, list) else [str(exp)],
        })
    return out


async def extract_blueprint_from_conversation(
    user_messages: List[str], prior: Optional[dict] = None, prior_judges: Optional[list] = None
) -> tuple[Blueprint, List[dict]]:
    """LLM-build/update a Blueprint from the whole conversation (format-agnostic),
    AND extract the named evaluators (judges/referees/reviewers) the organizer gave.
    Returns (blueprint, judges). Falls back to the prior values on any failure."""
    from app.services import llm_client
    import json

    prior = prior or {}
    prior_judges = _clean_judges(prior_judges)
    if not llm_client.is_available():
        bp = normalize(Blueprint.from_dict(prior)) if prior else Blueprint()
        return bp, prior_judges

    from datetime import datetime, timezone, timedelta
    now_ist = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30)))

    convo = "\n".join(f"- {m}" for m in user_messages if m and m.strip())
    user = (
        f"CURRENT DATE/TIME (IST, UTC+05:30): {now_ist.strftime('%Y-%m-%dT%H:%M:%S+05:30')} "
        f"({now_ist.strftime('%A, %d %B %Y')}). Compute all relative dates from this.\n\n"
        f"CURRENT DRAFT BLUEPRINT:\n{json.dumps(prior, indent=2)}\n\n"
        f"KNOWN JUDGES SO FAR:\n{json.dumps(prior_judges, indent=2)}\n\n"
        f"ORGANIZER (full conversation, latest last):\n{convo}"
    )
    try:
        out = await llm_client.complete_json(_AGENT_SYSTEM, user, max_tokens=4000)
        bp = Blueprint.from_dict(out)
        judges = _clean_judges(out.get("judges")) or prior_judges
        if bp.event_name or bp.stages:
            return normalize(bp), judges
    except Exception as exc:
        print(f"[blueprint_synth] conversational extraction failed: {exc}")
    bp = normalize(Blueprint.from_dict(prior)) if prior else Blueprint()
    return bp, prior_judges


def preview_text(bp: Blueprint, verdict: dict) -> str:
    """Plain-English 'here's what I understood' summary (§7c.2) for the chat."""
    lines: List[str] = []
    name = bp.event_name or "(unnamed event)"
    fmt = bp.format_label or "event"
    lines.append(f"**{name}** — understood as a *{fmt}* ({bp.participants.model}).")
    if bp.stages:
        flow = " → ".join(s.label for s in bp.stages)
        lines.append(f"Flow: {flow}")
    judge_roles = [r.label for r in bp.roles if r.kind == "judge"]
    if judge_roles:
        lines.append(f"Evaluator roles: {', '.join(judge_roles)}")
    conf = verdict.get("confidence")
    if conf is not None:
        lines.append(f"Confidence: {int(conf * 100)}%")
    if verdict.get("contradictions"):
        lines.append("⚠ Issues to resolve: " + "; ".join(verdict["contradictions"][:3]))
    if verdict.get("missing"):
        lines.append("Still need: " + "; ".join(verdict["missing"][:3]))
    return "\n".join(lines)
