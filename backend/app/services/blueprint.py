"""
EKAM Universal Event Blueprint (Task 3 — Event OS).

A single, fixed schema that represents ANY structured competitive/selection
process as an ordered list of orchestration **primitives** (the "Event Grammar").
The AI proposes a Blueprint, a human reviews/edits it, and the generator builds
the event from it — the backend only ever knows the primitives, so a never-seen
format runs without a migration or a code change.

This module is intentionally PURE (no DB, no LLM, no FastAPI):
  - the Pydantic schema (validated, serializable),
  - `required_fields(bp)`  → what the blueprint still needs (missing-info engine),
  - `normalize(bp)`        → fill ids/defaults so downstream code is total,
  - small accessors used by the validator / generator / pipeline.

Design note (normalization decision): §3 of ai_event.md lists top-level
`evaluation_rules` / `progression_rules` / `approvals`. We fold those INTO the
stages that own them (an `evaluation` stage carries its `scoring`; a
`progression` stage carries its `rule`; an `approval` stage IS the gate). One
ordered `stages[]` is the single source of truth for the pipeline — no parallel
arrays to keep in sync. `communications[]` stays top-level (cross-cutting).
"""

from __future__ import annotations

import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ── The Event Grammar: the only stage types the engine understands ───────────
# Anything the AI can't map to a known primitive becomes `custom`/`manual` — an
# informational stage the organizer advances by hand, which is what lets an
# UNKNOWN format still run end-to-end.
STAGE_TYPES = {
    "registration",     # participant intake (public /register, Task 6)
    "team_formation",   # CP-SAT grouping (team events)
    "entry_formation",  # singleton "team of one" per participant (individual events)
    "theme_selection",  # teams pick a theme/track + team name (hackathon parity)
    "judge_assignment", # CP-SAT assigns judges/reviewers to teams/rounds
    "submission",       # collect an artifact (deck/abstract/code/flag/…)
    "evaluation",       # scored review by a judge-role (or auto)
    "progression",      # advance/cut by a rule (top_n/cutoff/all/winners)
    "approval",         # human gate at a transition
    "communication",    # notify a role at a touchpoint
    "bracket",          # single-elimination knockout (specialised progression)
    "custom",           # known-unknown phase → manual advance
    "manual",           # alias of custom
}

KNOWN_AUTOMATED_TYPES = {
    "registration", "team_formation", "entry_formation", "theme_selection",
    "judge_assignment", "submission", "evaluation", "progression", "approval",
    "communication", "bracket",
}

ROLE_KINDS = {"participant", "judge"}
ARTIFACT_KINDS = {"text", "file", "link", "number"}
SCORING_METHODS = {"average", "sum", "weighted", "auto"}
PROGRESSION_KINDS = {"top_n", "cutoff_score", "all", "winners", "manual"}

# Confidence at/under this forces clarification — never auto-confident-deploy.
CONFIDENCE_THRESHOLD = 0.8


def slugify(text: str, fallback: str = "stage") -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").strip().lower()).strip("_")
    return s or fallback


# ── Schema ───────────────────────────────────────────────────────────────────

# Schema fields that are conceptually enums are typed as plain `str` (not Literal)
# so a slightly-off LLM value never hard-fails parsing; `normalize()` coerces them
# to a valid member. This keeps the LLM seam robust.
class Role(BaseModel):
    id: str = ""
    kind: str = "judge"            # participant | judge
    label: str = "Judge"
    anonymous: bool = False  # blind review: hide this role's identity / what it sees

    @model_validator(mode="before")
    @classmethod
    def _accept_name_and_infer_kind(cls, data):
        # LLMs commonly emit a role's human label under "name" (not "label") and
        # omit "kind". Without this, every role's label collapses to the default
        # "Judge" and a participant role gets mis-typed as a judge. Map name→label
        # and infer kind from the id/label so Mentor/Investor/Reviewer survive and
        # the participant role is correctly typed.
        if not isinstance(data, dict):
            return data
        d = dict(data)
        if not d.get("label") and d.get("name"):
            d["label"] = d["name"]
        if not (d.get("kind") or "").strip():
            text = f"{d.get('id','')} {d.get('label','')}".lower()
            participant_words = (
                "participant", "author", "contestant", "competitor", "applicant",
                "candidate", "player", "team member", "teammate", "debater",
                "delegate", "founder", "speaker", "entrant",
            )
            d["kind"] = "participant" if any(w in text for w in participant_words) else "judge"
        return d


class TeamSize(BaseModel):
    min: int = 1
    max: int = 1


class Capacity(BaseModel):
    max_participants: Optional[int] = None
    max_teams: Optional[int] = None


class Participants(BaseModel):
    model: str = "individual"      # individual | team
    team_size: Optional[TeamSize] = None
    capacity: Optional[Capacity] = None


class Artifact(BaseModel):
    id: str = ""
    label: str = ""
    kind: str = "file"             # text | file | link | number
    required: bool = True


class Window(BaseModel):
    opens_at: Optional[str] = None   # ISO-8601 string (kept as text; tz handled downstream)
    closes_at: Optional[str] = None


class ScoringCriterion(BaseModel):
    name: str = ""
    weight: float = 0.0   # 0–100; should sum to 100 across a stage's criteria
    max_score: float = 100.0
    description: Optional[str] = None


class Scoring(BaseModel):
    criteria: List[ScoringCriterion] = Field(default_factory=list)
    method: str = "average"        # average | sum | weighted | auto


class ProgressionRule(BaseModel):
    kind: str = "top_n"            # top_n | cutoff_score | all | winners | manual
    n: Optional[int] = None          # top_n: how many advance
    cutoff: Optional[float] = None   # cutoff_score: minimum score to advance
    top_n: Optional[int] = None      # winners: how many to award (1..3)


class Stage(BaseModel):
    id: str = ""
    type: str = "custom"
    label: str = ""
    role: Optional[str] = None       # role id (evaluation / approval / communication)
    artifact: Optional[str] = None   # artifact id (submission)
    window: Optional[Window] = None
    scoring: Optional[Scoring] = None        # evaluation
    rule: Optional[ProgressionRule] = None   # progression / bracket
    behaviors: List[str] = Field(default_factory=list)  # e.g. ["anonymous_review"]


class Communication(BaseModel):
    trigger: str = ""      # a stage id, or a lifecycle event (e.g. "on_registration")
    to_role: str = "participant"
    channel: str = "both"          # email | in_app | both
    template: Optional[str] = None


# Public sign-up form field (KI-1): the AI proposes these per format so the
# registration page is tailored (esports → in-game name; symposium → paper title)
# instead of the fixed generic default. For team events these are PER-MEMBER.
REG_FIELD_TYPES = {"text", "email", "tel", "number", "url", "select", "textarea", "date"}


class RegistrationField(BaseModel):
    field_id: str = ""
    label: str = ""
    type: str = "text"             # text | email | tel | number | url | select | textarea | date
    required: bool = False
    options: List[str] = Field(default_factory=list)  # for type == "select"


class Blueprint(BaseModel):
    event_name: Optional[str] = None
    format_label: Optional[str] = None   # display only — never branches logic
    confidence: float = 0.0              # AI's self-assessed completeness (advisory)
    description: Optional[str] = None
    roles: List[Role] = Field(default_factory=list)
    participants: Participants = Field(default_factory=Participants)
    artifacts: List[Artifact] = Field(default_factory=list)
    stages: List[Stage] = Field(default_factory=list)
    communications: List[Communication] = Field(default_factory=list)
    # Public sign-up form, tailored to the format (KI-1). Empty ⇒ a deterministic
    # default is derived from format_label + participants.model at deploy time.
    registration_fields: List[RegistrationField] = Field(default_factory=list)
    # Team-event sign-up mode (KI-2): "preformed" = participants register their own
    # team (leader fills in every member); "organizer" / "auto" = the platform
    # forms teams later. Ignored for individual events.
    team_registration: str = "preformed"

    @field_validator("team_registration", mode="before")
    @classmethod
    def _coerce_team_registration(cls, v):
        # LLMs sometimes emit a dict/None here (e.g. {"method": "preformed"}); a
        # single off-shaped field must never reject the WHOLE blueprint. Extract a
        # string, else fall back to the default. normalize() validates the value.
        if v is None:
            return "preformed"
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            for key in ("method", "mode", "type", "value"):
                if isinstance(v.get(key), str):
                    return v[key]
            return "preformed"
        return str(v)

    # ── serialization helpers ────────────────────────────────────────────────
    @classmethod
    def from_dict(cls, data: dict | None) -> "Blueprint":
        """Lenient parse — unknown keys ignored, missing keys defaulted, so a
        partial LLM draft never raises."""
        return cls.model_validate(data or {})

    def to_dict(self) -> dict:
        return self.model_dump(mode="json", exclude_none=False)


# ── Normalization ─────────────────────────────────────────────────────────────

def normalize(bp: Blueprint) -> Blueprint:
    """Fill ids/labels/defaults so every downstream consumer is total (never has
    to guess an id or a label). Idempotent. Returns a new Blueprint."""
    data = bp.model_copy(deep=True)

    # Coerce conceptually-enum string fields to valid members (LLM tolerance).
    if (data.participants.model or "").strip().lower() not in ("individual", "team"):
        data.participants.model = "team" if "team" in (data.participants.model or "").lower() else "individual"
    else:
        data.participants.model = data.participants.model.strip().lower()

    # Roles: ensure a participant role exists; give every role an id + label.
    for r in data.roles:
        k = (r.kind or "").strip().lower()
        r.kind = "participant" if k.startswith("part") else ("judge" if k not in ("participant", "judge") else k)
    if not any(r.kind == "participant" for r in data.roles):
        data.roles.insert(0, Role(id="participant", kind="participant", label="Participant"))
    seen_role_ids: set[str] = set()
    for i, r in enumerate(data.roles):
        if not r.id:
            r.id = slugify(r.label, f"role_{i+1}")
        while r.id in seen_role_ids:
            r.id = f"{r.id}_{i+1}"
        seen_role_ids.add(r.id)
        if not r.label:
            r.label = "Judge" if r.kind == "judge" else "Participant"

    # Artifacts: id + label + kind coercion.
    seen_art: set[str] = set()
    for i, a in enumerate(data.artifacts):
        if (a.kind or "").strip().lower() not in ARTIFACT_KINDS:
            a.kind = "file"
        else:
            a.kind = a.kind.strip().lower()
        if not a.id:
            a.id = slugify(a.label, f"artifact_{i+1}")
        while a.id in seen_art:
            a.id = f"{a.id}_{i+1}"
        seen_art.add(a.id)
        if not a.label:
            a.label = a.id.replace("_", " ").title()

    # Stages: id (unique), label, type + scoring.method + rule.kind coercion.
    seen_stage: set[str] = set()
    for i, s in enumerate(data.stages):
        s.type = (s.type or "custom").strip().lower()
        if s.type not in STAGE_TYPES:
            s.type = "custom"
        if s.scoring is not None:
            m = (s.scoring.method or "").strip().lower()
            s.scoring.method = m if m in SCORING_METHODS else ("auto" if m == "auto" else "average")
            # A stage scored by a HUMAN evaluator role can't be "auto" (auto means
            # an autograder/scoreboard with no judges). Coerce to a human method so
            # the referee/judge is actually used.
            if s.scoring.method == "auto" and (s.role or "").strip():
                crits = s.scoring.criteria or []
                s.scoring.method = "weighted" if any((c.weight or 0) for c in crits) else "average"
            # Normalize criterion weights so they always either sum to 100 or are
            # all 0 (equal weighting). LLMs often emit fractions (0.5/0.5) or
            # inconsistent sums — coerce rather than fail the contradiction check.
            crits = s.scoring.criteria or []
            total = sum((c.weight or 0.0) for c in crits)
            if crits and total > 0:
                if 0.8 <= total <= 1.2:            # fractions → percentages
                    for c in crits:
                        c.weight = round((c.weight or 0.0) * 100.0 / total, 2)
                elif abs(total - 100.0) > 0.5:     # arbitrary sum → equal weighting
                    for c in crits:
                        c.weight = 0.0
        if s.rule is not None:
            k = (s.rule.kind or "").strip().lower()
            if k not in PROGRESSION_KINDS:
                s.rule.kind = "winners" if "win" in k else "top_n"
            else:
                s.rule.kind = k
        if not s.id:
            s.id = slugify(s.label or s.type, f"stage_{i+1}")
        while s.id in seen_stage:
            s.id = f"{s.id}_{i+1}"
        seen_stage.add(s.id)
        if not s.label:
            s.label = (s.type or "stage").replace("_", " ").title()

    # Submission stages must reference a defined artifact. LLMs often add a
    # submission stage but forget the artifact (or reference an undefined id). Auto-
    # create/link a default file artifact rather than leave the blueprint un-ready —
    # a runnable event shouldn't depend on the model remembering this (KI-4).
    art_index = {a.id: a for a in data.artifacts}
    for s in data.stages:
        if s.type != "submission":
            continue
        if s.artifact and s.artifact in art_index:
            continue
        new_id = s.artifact or "submission"
        base, k = new_id, 1
        while new_id in art_index:
            k += 1
            new_id = f"{base}_{k}"
        label = (s.label or "Submission").strip()
        for suf in (" submission", " upload"):
            if label.lower().endswith(suf):
                label = label[: -len(suf)].strip()
        art = Artifact(id=new_id, label=(label or "Submission"), kind="file", required=True)
        data.artifacts.append(art)
        art_index[new_id] = art
        s.artifact = new_id

    # Communications: drop blank-trigger touchpoints (LLMs emit empty ones) +
    # coerce channel.
    data.communications = [c for c in data.communications if (c.trigger or "").strip()]
    for c in data.communications:
        if (c.channel or "").strip().lower() not in ("email", "in_app", "both"):
            c.channel = "both"
        else:
            c.channel = c.channel.strip().lower()

    # Registration fields: id + type coercion; always guarantee name + email
    # (identity extraction, CSV import, team formation, and magic-links key off
    # those). Only enforced when the AI proposed a custom form — an empty list is
    # left empty so the deploy path can derive a smart default from the format.
    seen_field: set[str] = set()
    for i, f in enumerate(data.registration_fields):
        if (f.type or "").strip().lower() not in REG_FIELD_TYPES:
            f.type = "text"
        else:
            f.type = f.type.strip().lower()
        if not f.field_id:
            f.field_id = slugify(f.label, f"field_{i+1}")
        while f.field_id in seen_field:
            f.field_id = f"{f.field_id}_{i+1}"
        seen_field.add(f.field_id)
        if not f.label:
            f.label = f.field_id.replace("_", " ").title()
    if data.registration_fields:
        ids = {f.field_id for f in data.registration_fields}
        if "email" not in ids:
            data.registration_fields.insert(0, RegistrationField(
                field_id="email", label="Email", type="email", required=True))
        if "full_name" not in ids and "name" not in ids:
            data.registration_fields.insert(0, RegistrationField(
                field_id="full_name", label="Full Name", type="text", required=True))

    # When the event has exactly ONE judge role, every human-judged evaluation
    # stage is unambiguously judged by it — assign it when the LLM forgot, so
    # single-evaluator formats (referee / reviewer / adjudicator) are ready without
    # a needless follow-up. Multi-role events (e.g. Mentor + Investor) stay a
    # clarifying question, since which role judges which stage is genuinely unknown.
    judge_role_list = [r for r in data.roles if r.kind == "judge"]
    if len(judge_role_list) == 1:
        only_judge = judge_role_list[0].id
        for s in data.stages:
            if s.type == "evaluation" and not (s.role or "").strip():
                method = s.scoring.method if s.scoring else None
                if method != "auto":
                    s.role = only_judge

    # Team-registration mode coercion (KI-2).
    tr = (data.team_registration or "").strip().lower()
    data.team_registration = tr if tr in ("preformed", "organizer", "auto") else "preformed"

    # Participants: a team event needs a sane team_size.
    if data.participants.model == "team" and data.participants.team_size is None:
        data.participants.team_size = TeamSize(min=2, max=4)
    # A team event must allow at least 2 members (per the user's "min two members
    # compulsory" rule); clamp a stray min of 0/1.
    if data.participants.model == "team" and data.participants.team_size is not None:
        ts = data.participants.team_size
        if ts.min < 2:
            ts.min = 2
        if ts.max < ts.min:
            ts.max = ts.min

    return data


# ── Accessors used by validator / generator / pipeline ───────────────────────

def role_ids(bp: Blueprint) -> set[str]:
    return {r.id for r in bp.roles if r.id}


def judge_roles(bp: Blueprint) -> List[Role]:
    return [r for r in bp.roles if r.kind == "judge"]


def artifact_ids(bp: Blueprint) -> set[str]:
    return {a.id for a in bp.artifacts if a.id}


def is_individual(bp: Blueprint) -> bool:
    return (bp.participants.model or "individual") == "individual"


def has_intake(bp: Blueprint) -> bool:
    """A roster has to come from somewhere: a registration stage OR a submission
    stage (application-style formats start with an application submission)."""
    return any(s.type in ("registration", "submission") for s in bp.stages)


# ── Missing-information engine (computed FROM the proposed blueprint) ─────────

def required_fields(bp: Blueprint) -> List[str]:
    """What this blueprint still needs before it could be generated. Computed
    from the stages the AI actually proposed — NOT a fixed hackathon checklist.
    Returns human-readable, askable gaps (empty list ⇒ structurally complete)."""
    missing: List[str] = []

    if not (bp.event_name or "").strip():
        missing.append("the event's name")

    if not bp.stages:
        missing.append("at least one stage describing how the event runs")
        return missing  # nothing else is meaningful without stages

    if not has_intake(bp):
        missing.append("an intake stage (registration or an application submission)")

    if bp.participants.model == "team":
        ts = bp.participants.team_size
        if ts is None:
            missing.append("the allowed team size (min and max members)")

    arts = artifact_ids(bp)
    roles = role_ids(bp)

    for s in bp.stages:
        where = f"stage '{s.label or s.id}'"
        if s.type == "submission":
            if not s.artifact:
                missing.append(f"what gets submitted in {where} (an artifact)")
            elif s.artifact not in arts:
                missing.append(f"a definition for the artifact '{s.artifact}' used in {where}")
        elif s.type == "evaluation":
            method = s.scoring.method if s.scoring else None
            if method != "auto":
                if not s.scoring or not s.scoring.criteria:
                    missing.append(f"the scoring criteria for {where}")
                if not s.role:
                    missing.append(f"which role judges {where}")
                elif s.role not in roles:
                    missing.append(f"a definition for the role '{s.role}' that judges {where}")
        elif s.type in ("progression", "bracket"):
            if s.type == "progression" and s.rule is None:
                missing.append(f"the advancement rule for {where} (top-N, cutoff, or all)")
        elif s.type in ("approval", "communication"):
            if s.role and s.role not in roles:
                missing.append(f"a definition for the role '{s.role}' referenced by {where}")

    # De-dup while preserving order.
    seen: set[str] = set()
    out: List[str] = []
    for m in missing:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out
