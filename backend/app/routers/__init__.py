from fastapi import APIRouter

from .auth import router as auth_router
from .events import router as events_router
from .rounds import router as rounds_router
from .participants import router as participants_router
from .teams import router as teams_router
from .submissions import router as submissions_router
from .judges import router as judges_router
from .evaluations import router as evaluations_router
from .reports import router as reports_router
from .ai import router as ai_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(events_router, prefix="/events", tags=["events"])
api_router.include_router(rounds_router, prefix="/rounds", tags=["rounds"])
api_router.include_router(participants_router, prefix="/participants", tags=["participants"])
api_router.include_router(teams_router, prefix="/teams", tags=["teams"])
api_router.include_router(submissions_router, prefix="/submissions", tags=["submissions"])
api_router.include_router(judges_router, prefix="/judges", tags=["judges"])
api_router.include_router(evaluations_router, prefix="/evaluations", tags=["evaluations"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(ai_router, prefix="/ai", tags=["ai"])
