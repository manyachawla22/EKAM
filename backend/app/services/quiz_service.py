"""
EKAM Quiz / Question-Bank service (Task 3, feature #8).

Pipeline for a quiz/coding round:
  1. parse_question_bank(.md/.csv)  → list of question dicts
  2. ingest_bank(round)             → Question rows (the per-round bank)
  3. generate_papers(round, N)      → a QuestionPaper (N random questions) per team
  4. get_paper_for_team(round,team) → the team's questions (participant + judge view)
  5. ai_grade_submission(...)       → optional: AI scores the uploaded answer file
                                      against each question's answer.

All parsing is DETERMINISTIC (no LLM) so a bank always imports the same way; only
the optional auto-grade uses the LLM seam.
"""

from __future__ import annotations

import csv
import io
import random
import re
from typing import Any, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Round
from app.models.quiz import Question, QuestionPaper
from app.models.team import Team


# ── Parsing ───────────────────────────────────────────────────────────────────

def _clean(s: Any) -> str:
    return str(s or "").strip()


def _parse_csv_bank(text: str) -> List[dict]:
    """CSV columns (case-insensitive): question (required); option_a..option_d OR a
    single `options` column (split on | or ;); answer/correct_answer (optional);
    marks (optional)."""
    out: List[dict] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        row = {(_clean(k).lower()): _clean(v) for k, v in row.items() if k}
        q = row.get("question") or row.get("text") or row.get("q")
        if not q:
            continue
        options: List[str] = []
        if row.get("options"):
            options = [o.strip() for o in re.split(r"[|;]", row["options"]) if o.strip()]
        else:
            for key in ("option_a", "option_b", "option_c", "option_d", "option_e"):
                if row.get(key):
                    options.append(row[key])
        marks = 1.0
        try:
            marks = float(row.get("marks") or row.get("mark") or 1)
        except (TypeError, ValueError):
            marks = 1.0
        out.append({
            "text": q,
            "options": options or None,
            "correct_answer": row.get("answer") or row.get("correct_answer") or None,
            "marks": marks,
        })
    return out


_Q_START = re.compile(r"^\s*(?:\d+[\.\)]|Q\s*\d*[:\.\)]|#+)\s*", re.I)
_OPT = re.compile(r"^\s*(?:[a-eA-E][\.\)]|[-*])\s+(.*)$")
_ANS = re.compile(r"^\s*(?:answer|ans|correct)\s*[:\-]\s*(.*)$", re.I)
_MARKS = re.compile(r"^\s*(?:marks?|points?)\s*[:\-]\s*(.*)$", re.I)


def _parse_md_bank(text: str) -> List[dict]:
    """A tolerant Markdown/plain-text bank. A question starts on a numbered/`Q:`/`#`
    line (or the first non-empty line of a block); `a) … / - …` lines are options;
    `Answer:` and `Marks:` lines set those. Blank lines separate questions."""
    out: List[dict] = []
    cur: Optional[dict] = None

    def flush():
        nonlocal cur
        if cur and _clean(cur.get("text")):
            cur["options"] = cur["options"] or None
            out.append(cur)
        cur = None

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m_ans = _ANS.match(line)
        m_marks = _MARKS.match(line)
        m_opt = _OPT.match(line)
        if m_ans and cur:
            cur["correct_answer"] = m_ans.group(1).strip() or None
            continue
        if m_marks and cur:
            try:
                cur["marks"] = float(m_marks.group(1).strip())
            except (TypeError, ValueError):
                pass
            continue
        if m_opt and cur:
            cur["options"].append(m_opt.group(1).strip())
            continue
        if _Q_START.match(line):
            flush()
            cur = {"text": _Q_START.sub("", line).strip(), "options": [], "correct_answer": None, "marks": 1.0}
            continue
        # A non-empty line that's not an option/answer/marks and we have no current
        # question → start one; if we DO have one with no options yet, treat as a
        # continuation of the question text.
        if cur is None:
            cur = {"text": line.strip(), "options": [], "correct_answer": None, "marks": 1.0}
        elif not cur["options"] and not cur["correct_answer"]:
            cur["text"] = f"{cur['text']} {line.strip()}".strip()
        else:
            flush()
            cur = {"text": line.strip(), "options": [], "correct_answer": None, "marks": 1.0}
    flush()
    return out


def parse_question_bank(content: bytes, filename: str = "") -> List[dict]:
    """Parse an uploaded question bank into question dicts. Picks CSV vs Markdown by
    extension (defaults to Markdown). Never raises on a messy bank — returns what it
    could read."""
    text = content.decode("utf-8-sig", errors="replace")
    if (filename or "").lower().endswith(".csv"):
        return _parse_csv_bank(text)
    return _parse_md_bank(text)


# ── Ingest + generate ───────────────────────────────────────────────────────

async def ingest_bank(db: AsyncSession, round_id, questions: List[dict]) -> int:
    """Replace the round's question bank with `questions` (idempotent re-upload).
    Marks the round as a quiz round. Returns how many questions were stored."""
    await db.execute(delete(Question).where(Question.round_id == round_id))
    for i, q in enumerate(questions):
        if not _clean(q.get("text")):
            continue
        opts = q.get("options")
        db.add(Question(
            round_id=round_id,
            text=_clean(q["text"])[:2000],
            options=[str(o)[:500] for o in opts] if isinstance(opts, list) and opts else None,
            correct_answer=(_clean(q.get("correct_answer")) or None),
            marks=float(q.get("marks") or 1.0),
            position=i,
        ))
    rnd = (await db.execute(select(Round).where(Round.id == round_id))).scalars().first()
    if rnd is not None:
        rnd.is_quiz = True
        if not rnd.questions_per_paper:
            # default a paper to the whole bank until the organizer sets a count
            rnd.questions_per_paper = len([q for q in questions if _clean(q.get("text"))])
    await db.commit()
    return len([q for q in questions if _clean(q.get("text"))])


async def _active_team_ids(db: AsyncSession, round_id) -> List:
    rnd = (await db.execute(select(Round).where(Round.id == round_id))).scalars().first()
    if rnd is None:
        return []
    teams = list((await db.execute(
        select(Team.id).where(Team.event_id == rnd.event_id)
    )).scalars().all())
    if teams:
        return teams
    # Individual (team-less) event: treat each participant as a one-person team so
    # the quiz generates a paper PER PARTICIPANT. ensure_singleton_teams is
    # idempotent and only runs when the event has no teams at all (a real team
    # event keeps its teams untouched).
    from app.services.pipeline_service import ensure_singleton_teams
    await ensure_singleton_teams(db, rnd.event_id)
    return list((await db.execute(
        select(Team.id).where(Team.event_id == rnd.event_id)
    )).scalars().all())


async def generate_papers(db: AsyncSession, round_id, questions_per_paper: Optional[int] = None) -> int:
    """Create one QuestionPaper per team that doesn't have one yet — a random subset
    of `questions_per_paper` questions from the bank (so different participants get
    different papers). Idempotent. Returns how many papers were created."""
    bank = (await db.execute(
        select(Question.id).where(Question.round_id == round_id).order_by(Question.position)
    )).scalars().all()
    bank = [str(q) for q in bank]
    if not bank:
        return 0

    rnd = (await db.execute(select(Round).where(Round.id == round_id))).scalars().first()
    n = questions_per_paper or (rnd.questions_per_paper if rnd else 0) or len(bank)
    n = max(1, min(int(n), len(bank)))
    if rnd is not None and rnd.questions_per_paper != n:
        rnd.questions_per_paper = n

    existing = {
        str(t) for t in (await db.execute(
            select(QuestionPaper.team_id).where(QuestionPaper.round_id == round_id)
        )).scalars().all()
    }
    created = 0
    for tid in await _active_team_ids(db, round_id):
        if str(tid) in existing:
            continue
        picked = random.sample(bank, n)
        db.add(QuestionPaper(round_id=round_id, team_id=tid, question_ids=picked))
        created += 1
    await db.commit()
    return created


async def assign_all_judges(db: AsyncSession, round_id) -> int:
    """Quiz rounds are graded against an answer key, so there's no panel to
    optimise — every judge grades everyone. Assign each judge of the event to
    every team for this round (auto-creating singleton teams for an individual
    event first, mirroring generate_papers). Idempotent; returns rows created.

    Like the CP-SAT path (execute_judge_assignment), newly-assigned judges get
    their login email drafted for approval — bypassing CP-SAT must not mean
    bypassing the judge invite."""
    from app.models.event import Event
    from app.models.judge import Judge, JudgeAssignment

    rnd = (await db.execute(select(Round).where(Round.id == round_id))).scalars().first()
    if rnd is None:
        return 0
    team_ids = await _active_team_ids(db, round_id)
    judges = (await db.execute(
        select(Judge).where(Judge.event_id == rnd.event_id)
    )).scalars().all()
    if not team_ids or not judges:
        return 0

    existing = {
        (str(j), str(t)) for j, t in (await db.execute(
            select(JudgeAssignment.judge_id, JudgeAssignment.team_id)
            .where(JudgeAssignment.round_id == round_id)
        )).all()
    }
    created = 0
    newly_assigned: set = set()
    for j in judges:
        for tid in team_ids:
            if (str(j.id), str(tid)) in existing:
                continue
            db.add(JudgeAssignment(judge_id=j.id, team_id=tid, round_id=round_id))
            created += 1
            newly_assigned.add(j.id)
    if created:
        await db.commit()

    # Draft login emails for judges who got their FIRST assignment in this round
    # (non-fatal — mirrors execute_judge_assignment).
    if newly_assigned:
        try:
            event = (await db.execute(
                select(Event).where(Event.id == rnd.event_id)
            )).scalars().first()
            emails = [j.email for j in judges if j.id in newly_assigned and j.email]
            if event and emails:
                from app.services.email_service import draft_judge_login_emails
                await draft_judge_login_emails(
                    db=db,
                    event_id=str(event.id),
                    event_name=event.name,
                    event_hash=event.hash,
                    judge_emails=list(dict.fromkeys(emails)),
                    requested_by=str(event.organizer_id),
                )
        except Exception as e:
            print(f"[quiz_service] judge login email draft failed (non-fatal): {e}")

    return created


async def _questions_by_id(db: AsyncSession, ids: List[str]) -> dict:
    if not ids:
        return {}
    rows = (await db.execute(select(Question).where(Question.id.in_(ids)))).scalars().all()
    return {str(q.id): q for q in rows}


async def get_paper_for_team(db: AsyncSession, round_id, team_id, *, include_answers: bool = False) -> dict:
    """The team's question paper (ordered). `include_answers=True` adds the correct
    answer per question (judge/grading view only — never the participant view).
    Lazily generates the team's paper if the round has a bank but no paper yet."""
    paper = (await db.execute(
        select(QuestionPaper).where(
            QuestionPaper.round_id == round_id, QuestionPaper.team_id == team_id
        )
    )).scalars().first()
    if paper is None:
        await generate_papers(db, round_id)
        paper = (await db.execute(
            select(QuestionPaper).where(
                QuestionPaper.round_id == round_id, QuestionPaper.team_id == team_id
            )
        )).scalars().first()
    if paper is None:
        return {"questions": []}

    ids = [str(i) for i in (paper.question_ids or [])]
    qmap = await _questions_by_id(db, ids)
    questions = []
    for i, qid in enumerate(ids):
        q = qmap.get(qid)
        if not q:
            continue
        item = {
            "id": qid,
            "number": i + 1,
            "text": q.text,
            "options": q.options or [],
            "marks": q.marks,
        }
        if include_answers:
            item["correct_answer"] = q.correct_answer
        questions.append(item)
    return {"paper_id": str(paper.id), "questions": questions,
            "total_marks": sum(q.marks for q in qmap.values())}


async def ai_grade_submission(db: AsyncSession, round_id, team_id, submission) -> dict:
    """Optional AI auto-check: extract the answers from the uploaded answer file and
    score them against each question's correct answer. Best-effort — returns a
    per-question breakdown + total. Sets submission.final_score. Requires each
    question to have a correct_answer (open questions are left for a human)."""
    from app.services import llm_client
    from app.services.resume_service import extract_text
    from app.services.file_storage import read_pdf_bytes
    import io
    import json

    paper = await get_paper_for_team(db, round_id, team_id, include_answers=True)
    questions = [q for q in paper["questions"] if q.get("correct_answer")]
    if not questions:
        return {"graded": False, "reason": "No questions have answer keys to auto-check."}

    # Pull text out of the uploaded answer PDF (fetched from Supabase Storage;
    # non-PDF attachments like GitHub/demo links are skipped).
    answer_text = ""
    for att in (getattr(submission, "attachments", None) or []):
        if not isinstance(att, str) or not att.split("?")[0].lower().endswith(".pdf"):
            continue
        data = read_pdf_bytes(att)
        if data:
            answer_text += extract_text(io.BytesIO(data)) + "\n"
    if not answer_text.strip():
        return {"graded": False, "reason": "Could not read the answer file (PDF text not found)."}

    system = (
        "You are grading a quiz. For each question you are given the correct answer "
        "and the candidate's submitted answers (free text). Decide if the candidate "
        "answered each question correctly. Return ONLY JSON: "
        '{"results":[{"number":int,"correct":bool,"awarded":number}],"total":number}.'
    )
    qspec = [{"number": q["number"], "question": q["text"], "answer": q["correct_answer"], "marks": q["marks"]} for q in questions]
    user = f"QUESTIONS + ANSWER KEY:\n{json.dumps(qspec)}\n\nCANDIDATE SUBMISSION:\n{answer_text[:6000]}"
    try:
        out = await llm_client.complete_json(system, user, max_tokens=1200)
    except Exception as exc:
        return {"graded": False, "reason": f"Auto-grade failed: {exc}"}

    total = 0.0
    try:
        total = float(out.get("total") or 0)
    except (TypeError, ValueError):
        total = sum(float(r.get("awarded") or 0) for r in (out.get("results") or []))
    submission.final_score = round(total, 2)
    from app.models.submission import SubmissionStatus
    submission.status = SubmissionStatus.reviewed
    await db.commit()
    return {"graded": True, "total": submission.final_score, "results": out.get("results") or []}
