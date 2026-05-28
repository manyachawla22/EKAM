from fastapi import (
    APIRouter,
    Depends
)

from pydantic import BaseModel

from app.middleware.auth import require_role

from app.models.user import (
    User,
    UserRole
)

from app.services.email_service import (
    send_stage_update_email,
    send_selection_email
)

router = APIRouter(
    prefix="/email",
    tags=["Email"]
)


class StageEmailRequest(BaseModel):
    email: str
    event_name: str
    stage: str


class SelectionEmailRequest(BaseModel):
    email: str
    round_name: str


@router.post("/stage-update")
async def send_stage_update(
    request: StageEmailRequest,
    current_user: User = Depends(
        require_role([
            UserRole.organizer,
            UserRole.admin
        ])
    )
):
    await send_stage_update_email(
        request.email,
        request.event_name,
        request.stage
    )

    return {
        "message": "Stage update email sent"
    }


@router.post("/selection")
async def send_selection(
    request: SelectionEmailRequest,
    current_user: User = Depends(
        require_role([
            UserRole.organizer,
            UserRole.admin
        ])
    )
):
    await send_selection_email(
        request.email,
        request.round_name
    )

    return {
        "message": "Selection email sent"
    }