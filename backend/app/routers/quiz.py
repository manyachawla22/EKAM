"""
EKAM Quiz / Question-Bank router (Task 3, feature #8).

Organizer: upload/paste a bank, set questions-per-paper, generate papers, view bank.
Participant: fetch their team's paper (no answer key).
Judge/Organizer: fetch a team's paper WITH the answer key + AI auto-grade.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth_context import AuthContext
from app.middleware.auth import require_actor_type
from app.models.event import Round
from app.models.quiz import Question
from app.models.submission import Submission
from app.models.team import Team, TeamMember
from app.models.participant import Participant
from app.services import quiz_service

router = APIRouter(prefix="/quiz", tags=["Quiz"])


class BankTextBody(BaseModel):
    text: str
    filename: Optional[str] = None          # ".csv" → CSV parse, else Markdown
    questions_per_paper: Optional[int] = None


class ConfigBody(BaseModel):
    questions_per_paper: int


async def _round_or_404(db: AsyncSession, round_id: str) -> Round:
    rnd = (await db.execute(select(Round).where(Round.id == round_id))).scalars().first()
    if rnd is None:
        raise HTTPException(status_code=404, detail="Round not found")
    return rnd


def _require_event(auth: AuthContext, event_id) -> None:
    if not auth.can_access_event(str(event_id)):
        raise HTTPException(status_code=403, detail="No access to this event")


# ── Organizer: manage the bank ───────────────────────────────────────────────

@router.post("/rounds/{round_id}/bank", dependencies=[Depends(require_actor_type(["organizer"]))])
async def upload_bank(
    round_id: str,
    file: UploadFile = File(...),
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db),
):
    """Upload a question bank file (.md or .csv). Replaces the round's bank."""
    rnd = await _round_or_404(db, round_id)
    _require_event(auth, rnd.event_id)
    name = (file.filename or "").lower()
    if not (name.endswith(".csv") or name.endswith(".md") or name.endswith(".txt")):
        raise HTTPException(status_code=400, detail="Bank must be a .md, .txt, or .csv file")
    questions = quiz_service.parse_question_bank(await file.read(), file.filename or "")
    if not questions:
        raise HTTPException(status_code=400, detail="No questions found — check the file format.")
    count = await quiz_service.ingest_bank(db, round_id, questions)
    return {"message": f"Imported {count} question(s).", "count": count}


@router.post("/rounds/{round_id}/bank-text", dependencies=[Depends(require_actor_type(["organizer"]))])
async def upload_bank_text(
    round_id: str,
    body: BankTextBody,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db),
):
    """Ingest a bank pasted as text (the in-chat path). Replaces the round's bank."""
    rnd = await _round_or_404(db, round_id)
    _require_event(auth, rnd.event_id)
    questions = quiz_service.parse_question_bank(body.text.encode("utf-8"), body.filename or "")
    if not questions:
        raise HTTPException(status_code=400, detail="No questions found — check the format.")
    count = await quiz_service.ingest_bank(db, round_id, questions)
    if body.questions_per_paper:
        rnd.questions_per_paper = max(1, min(int(body.questions_per_paper), count))
        await db.commit()
    return {"message": f"Imported {count} question(s).", "count": count}


@router.patch("/rounds/{round_id}/config", dependencies=[Depends(require_actor_type(["organizer"]))])
async def set_config(
    round_id: str, body: ConfigBody,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db),
):
    """Set how many questions each generated paper has."""
    rnd = await _round_or_404(db, round_id)
    _require_event(auth, rnd.event_id)
    total = (await db.execute(select(Question).where(Question.round_id == round_id))).scalars().all()
    rnd.questions_per_paper = max(1, min(int(body.questions_per_paper), max(1, len(total))))
    rnd.is_quiz = True
    await db.commit()
    return {"questions_per_paper": rnd.questions_per_paper, "bank_size": len(total)}


@router.post("/rounds/{round_id}/generate", dependencies=[Depends(require_actor_type(["organizer"]))])
async def generate(
    round_id: str,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db),
):
    """Generate a paper for every participant (one-person teams for individual
    events) and auto-assign every judge to everyone for grading."""
    rnd = await _round_or_404(db, round_id)
    _require_event(auth, rnd.event_id)
    created = await quiz_service.generate_papers(db, round_id)
    assigned = await quiz_service.assign_all_judges(db, round_id)
    return {"created": created, "judges_assigned": assigned}


@router.get("/rounds/{round_id}/questions", dependencies=[Depends(require_actor_type(["organizer", "judge"]))])
async def list_questions(
    round_id: str,
    auth: AuthContext = Depends(require_actor_type(["organizer", "judge"])),
    db: AsyncSession = Depends(get_db),
):
    """The full bank for a round (organizer/judge bank management)."""
    rnd = await _round_or_404(db, round_id)
    _require_event(auth, rnd.event_id)
    qs = (await db.execute(
        select(Question).where(Question.round_id == round_id).order_by(Question.position)
    )).scalars().all()
    return {
        "is_quiz": rnd.is_quiz,
        "questions_per_paper": rnd.questions_per_paper,
        "bank_size": len(qs),
        "questions": [
            {"id": str(q.id), "text": q.text, "options": q.options or [],
             "correct_answer": q.correct_answer, "marks": q.marks}
            for q in qs
        ],
    }


# ── Participant: my paper ─────────────────────────────────────────────────────

@router.get("/rounds/{round_id}/my-paper", dependencies=[Depends(require_actor_type(["participant"]))])
async def my_paper(
    round_id: str,
    auth: AuthContext = Depends(require_actor_type(["participant"])),
    db: AsyncSession = Depends(get_db),
):
    """The calling participant's team's question paper (NO answer key)."""
    rnd = await _round_or_404(db, round_id)
    email = getattr(auth.entity, "email", None)
    if not email:
        return {"questions": []}
    team_id = (await db.execute(
        select(TeamMember.team_id)
        .join(Team, Team.id == TeamMember.team_id)
        .join(Participant, Participant.id == TeamMember.participant_id)
        .where(Team.event_id == rnd.event_id, Participant.email == email)
    )).scalars().first()
    if not team_id:
        return {"questions": []}
    return await quiz_service.get_paper_for_team(db, round_id, team_id, include_answers=False)


# ── Judge/Organizer: a team's paper (with answers) + auto-grade ──────────────

@router.get("/rounds/{round_id}/teams/{team_id}/paper",
            dependencies=[Depends(require_actor_type(["organizer", "judge"]))])
async def team_paper(
    round_id: str, team_id: str,
    auth: AuthContext = Depends(require_actor_type(["organizer", "judge"])),
    db: AsyncSession = Depends(get_db),
):
    """A team's paper WITH the answer key — for grading."""
    rnd = await _round_or_404(db, round_id)
    _require_event(auth, rnd.event_id)
    return await quiz_service.get_paper_for_team(db, round_id, team_id, include_answers=True)


@router.post("/submissions/{submission_id}/auto-grade",
             dependencies=[Depends(require_actor_type(["organizer", "judge"]))])
async def auto_grade(
    submission_id: str,
    auth: AuthContext = Depends(require_actor_type(["organizer", "judge"])),
    db: AsyncSession = Depends(get_db),
):
    """AI auto-check the uploaded answer file against the team's paper answer key."""
    sub = (await db.execute(select(Submission).where(Submission.id == submission_id))).scalars().first()
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    rnd = await _round_or_404(db, str(sub.round_id))
    _require_event(auth, rnd.event_id)
    return await quiz_service.ai_grade_submission(db, sub.round_id, sub.team_id, sub)
