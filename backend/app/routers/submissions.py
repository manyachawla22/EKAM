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
from sqlalchemy.ext.asyncio import AsyncSession

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

router = APIRouter(
    prefix="/submissions",
    tags=["Submissions"],
)


# Where uploaded submission files live on the local machine.
SUBMISSIONS_DIR = os.path.join(settings.UPLOAD_DIR, "submissions")

# Accept only PDFs for now.
ALLOWED_CONTENT_TYPES = {"application/pdf"}
MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MB


def _public_base_url(request: Request) -> str:
    """
    Base URL used to build absolute links to uploaded files.

    Prefers settings.PUBLIC_BASE_URL (set to the ngrok URL so remote judges can
    open files); falls back to the host the request came in on.
    """
    configured = (settings.PUBLIC_BASE_URL or "").strip().rstrip("/")
    if configured:
        return configured
    return str(request.base_url).rstrip("/")


def _safe_name(filename: str) -> str:
    """Strip the filename down to a safe basename."""
    base = os.path.basename(filename or "file.pdf")
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", base).strip("_") or "file.pdf"
    if not cleaned.lower().endswith(".pdf"):
        cleaned += ".pdf"
    return cleaned


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
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed.",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    if len(contents) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (max 25 MB).",
        )

    os.makedirs(SUBMISSIONS_DIR, exist_ok=True)

    display_name = _safe_name(file.filename)
    # Unguessable stored name — the download endpoint is unauthenticated so a
    # link can be opened directly (e.g. by a judge via ngrok in a new tab).
    stored_name = f"{uuid.uuid4().hex}_{display_name}"
    stored_path = os.path.join(SUBMISSIONS_DIR, stored_name)

    with open(stored_path, "wb") as out:
        out.write(contents)

    url = (
        f"{_public_base_url(request)}"
        f"{settings.API_V1_STR}/submissions/files/{stored_name}"
    )

    return {"url": url, "filename": stored_name, "name": display_name}


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
