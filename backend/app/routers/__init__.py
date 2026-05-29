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
from .dashboard import router as dashboard_router
from .leaderboard import router as leaderboard_router
from .emails import router as email_router
from .assignments import router as assignments_router
from .approvals import router as approvals_router
from .notifications import router as notifications_router
from .anomalies import router as anomalies_router
from .pipeline import router as pipeline_router
from .test_email import router as test_email_router

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
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(leaderboard_router, prefix="/leaderboard", tags=["leaderboard"])
api_router.include_router(email_router, prefix="/email", tags=["email"])
api_router.include_router(assignments_router, prefix="/assignments", tags=["assignments"])
api_router.include_router(approvals_router, prefix="/approvals", tags=["approvals"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
api_router.include_router(anomalies_router, prefix="/anomalies", tags=["anomalies"])
api_router.include_router(pipeline_router, prefix="/pipeline", tags=["pipeline"])
api_router.include_router(test_email_router)

