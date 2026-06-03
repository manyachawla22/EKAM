"""Assessment-guide generation for judges.

Given a submission, build a structured judging guide tailored to the team's
challenge/theme and the round's rubric — "what to look for" per criterion plus
key questions to ask. The guide is generated on demand (no schema change, not
persisted). When the LLM is unavailable it falls back to a deterministic guide
derived straight from the rubric and theme so judges always get something.
"""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.submission import Submission
from app.models.event import Round, Event
from app.models.team import Team
from app.models.theme import Theme
from app.models.rubric import RubricCriterion
from app.services.llm_service import complete_json


def _fallback_guide(challenge: str, overview: str, criteria) -> dict:
    return {
        "challenge": challenge,
        "overview": overview
        or "Assess how well the submission solves the stated challenge, "
        "weighing each rubric criterion on its own merits.",
        "criteria_guides": [
            {
                "criterion": c.name,
                "max_score": c.max_score,
                "what_to_look_for": (
                    c.description
                    or f"Evidence that the team meets the '{c.name}' criterion."
                ),
                "scoring_tips": (
                    f"Award near {c.max_score:g} for clear, complete evidence; "
                    "lower scores for partial or unconvincing work."
                ),
            }
            for c in criteria
        ],
        "key_questions": [
            "Does the submission directly address the challenge?",
            "Is the approach feasible and well-justified?",
            "What is the strongest and weakest part of the work?",
        ],
        "generated_by": "rules",
    }


async def generate_assessment_guide(db: AsyncSession, submission_id) -> dict:
    submission = (
        await db.execute(select(Submission).where(Submission.id == submission_id))
    ).scalars().first()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )

    round_obj = (
        await db.execute(select(Round).where(Round.id == submission.round_id))
    ).scalars().first()

    event = None
    if round_obj:
        event = (
            await db.execute(select(Event).where(Event.id == round_obj.event_id))
        ).scalars().first()

    # The team's chosen challenge/theme, if any.
    theme = None
    team = (
        await db.execute(select(Team).where(Team.id == submission.team_id))
    ).scalars().first()
    if team and team.theme_id:
        theme = (
            await db.execute(select(Theme).where(Theme.id == team.theme_id))
        ).scalars().first()

    criteria = (
        (
            await db.execute(
                select(RubricCriterion)
                .where(RubricCriterion.round_id == submission.round_id)
                .order_by(RubricCriterion.position)
            )
        )
        .scalars()
        .all()
    )

    challenge = (
        theme.name if theme else (round_obj.name if round_obj else "Submission")
    )
    overview_src = theme.description if theme else ""

    fallback = _fallback_guide(challenge, overview_src, criteria)

    # Without a rubric there is nothing meaningful to guide on — return fallback.
    if not criteria:
        return fallback

    rubric_lines = "\n".join(
        f"- {c.name} (max {c.max_score:g}): {c.description or 'no description'}"
        for c in criteria
    )
    context = (
        f"Event: {event.name if event else 'Event'}\n"
        f"Round: {round_obj.name if round_obj else 'Round'}\n"
        f"Challenge/Theme: {challenge}\n"
        f"Theme description: {overview_src or 'n/a'}\n"
        f"Required skills: {', '.join(theme.required_skills) if theme and theme.required_skills else 'n/a'}\n"
        f"Rubric criteria:\n{rubric_lines}"
    )
    system = (
        "You are an experienced head judge writing an assessment guide that "
        "helps a panel judge a team's submission fairly and consistently. "
        "Return ONLY JSON of the shape "
        '{"challenge": str, "overview": str, "criteria_guides": '
        '[{"criterion": str, "max_score": number, "what_to_look_for": str, '
        '"scoring_tips": str}], "key_questions": [str]}. '
        "Use the exact criterion names provided and keep guidance concrete."
    )

    result = await complete_json(system, context, max_tokens=1400)
    if not isinstance(result, dict) or not result.get("criteria_guides"):
        return fallback

    result.setdefault("challenge", challenge)
    result["generated_by"] = "ai"
    return result
