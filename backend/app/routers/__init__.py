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
# Each router defines its own prefix internally (e.g. APIRouter(prefix="/auth")).
# Including them with another prefix here would produce double-prefixed paths
# like /api/v1/auth/auth/login. Only `ai_router` has no internal prefix.
api_router.include_router(auth_router)
api_router.include_router(events_router)
api_router.include_router(rounds_router)
api_router.include_router(participants_router)
api_router.include_router(teams_router)
api_router.include_router(submissions_router)
api_router.include_router(judges_router)
api_router.include_router(evaluations_router)
api_router.include_router(reports_router)
api_router.include_router(ai_router, prefix="/ai", tags=["ai"])
api_router.include_router(dashboard_router)
api_router.include_router(leaderboard_router)
api_router.include_router(email_router)
api_router.include_router(assignments_router)
api_router.include_router(approvals_router)
api_router.include_router(notifications_router)
api_router.include_router(anomalies_router)
api_router.include_router(pipeline_router)
api_router.include_router(test_email_router)

