import os
import uuid
import re
from uuid import UUID
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    status,
    UploadFile,
    File,
    Request,
    HTTPException,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.middleware.auth import get_current_actor, require_actor_type
from app.core.auth_context import AuthContext

from app.schemas.submission import (
    Submission,
    SubmissionCreate,
)

from app.services.submission_service import (
    create_submission_service,
    list_submissions_service,
    get_submission_service,
)
from app.services.file_storage import (
    SUBMISSIONS_DIR,
    store_pdf,
    validate_pdf,
    public_base_url,
)

router = APIRouter(
    prefix="/submissions",
    tags=["Submissions"],
)


def _public_base_url(request: Request) -> str:
    """Base URL used to build absolute links to uploaded files (see file_storage)."""
    return public_base_url(str(request.base_url))


@router.post(
    "/upload-file",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_actor_type(["participant"]))],
)
async def upload_submission_file(
    request: Request,
    file: UploadFile = File(...),
    auth: AuthContext = Depends(require_actor_type(["participant"])),
):
    """Upload a single PDF for a submission.

    The file is stored on the local machine and a public URL is returned. The
    participant then includes that URL (alongside any GitHub/demo links) in the
    submission's `attachments` via POST /submissions/upload.
    """
    contents = await file.read()
    validate_pdf(file.content_type, contents)
    stored = store_pdf(contents, file.filename, _public_base_url(request))
    return {"url": stored["url"], "filename": stored["filename"], "name": stored["name"]}


@router.get("/files/{stored_name}")
async def download_submission_file(stored_name: str):
    """Serve an uploaded submission PDF.

    Intentionally unauthenticated: links are opened in a new browser tab (which
    would not carry the auth header) and the filename is an unguessable UUID.
    """
    safe = os.path.basename(stored_name)
    path = os.path.join(SUBMISSIONS_DIR, safe)
    if safe != stored_name or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")

    # Drop the uuid prefix when suggesting a download name.
    download_name = safe.split("_", 1)[1] if "_" in safe else safe
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=download_name,
    )


@router.post(
    "/upload",
    response_model=Submission,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_actor_type(["participant"]))],
)
async def upload_submission(
    submission_in: SubmissionCreate,
    auth: AuthContext = Depends(require_actor_type(["participant"])),
    db: AsyncSession = Depends(get_db),
):
    """Participants upload a submission for their team."""
    return await create_submission_service(db, submission_in)


@router.get(
    "/by-id/{submission_id}",
    response_model=Submission,
    dependencies=[Depends(require_actor_type(["organizer", "judge", "participant"]))],
)
async def get_submission(
    submission_id: UUID,
    auth: AuthContext = Depends(get_current_actor),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single submission (with its attachments) by id."""
    return await get_submission_service(db, submission_id)


@router.get(
    "/{round_id}",
    response_model=List[Submission],
    dependencies=[Depends(require_actor_type(["organizer", "judge", "participant"]))],
)
async def list_submissions(
    round_id: UUID,
    auth: AuthContext = Depends(get_current_actor),
    db: AsyncSession = Depends(get_db),
):
    """List all submissions for a round."""
    return await list_submissions_service(db, round_id)


class AutoScoreBody(BaseModel):
    # map of submission_id OR team_id (string) → numeric score
    scores: dict[str, float]


@router.post(
    "/{round_id}/auto-score",
    dependencies=[Depends(require_actor_type(["organizer"]))],
)
async def auto_score_round(
    round_id: UUID,
    body: AutoScoreBody,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db),
):
    """Ingest externally-computed scores for an AUTO-scored round (autograder /
    CTF scoreboard / AI metric). Sets submission.final_score, updates the live
    leaderboard, and auto-proposes advancement (the organizer still approves).
    Organizer-only; must own the round's event."""
    from app.models.event import Round as RoundModel
    from app.services.auto_score_service import apply_auto_scores

    rnd = (await db.execute(select(RoundModel).where(RoundModel.id == round_id))).scalars().first()
    if rnd is None:
        raise HTTPException(status_code=404, detail="Round not found")
    if not auth.can_access_event(str(rnd.event_id)):
        raise HTTPException(status_code=403, detail="No access to this event")

    return await apply_auto_scores(db, str(round_id), body.scores)
