from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS configuration
# Note: when allow_credentials=True, allow_origins cannot be "*" per the CORS
# spec — browsers refuse the response. List concrete dev origins here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://172.28.33.80:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)

from app.routers import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_db_client():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"[startup] DB unavailable, skipping table creation: {e}")
        return

    # One-time backfill: recompute every submission's panel_average/final_score
    # from its evaluations. The write path is correct now (flush fix), but rows
    # scored before the fix can hold a stale average that shows on dashboards.
    try:
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.models.submission import Submission
        from app.services.submission_service import recompute_panel_averages

        async with AsyncSessionLocal() as session:
            submissions = (await session.execute(select(Submission))).scalars().all()
            changed = await recompute_panel_averages(session, submissions)
            if changed:
                print("[startup] backfilled stale submission panel averages")
    except Exception as e:
        print(f"[startup] panel-average backfill skipped: {e}")

@app.get("/")
def root():
    return {"message": "Welcome to EKAM API"}
