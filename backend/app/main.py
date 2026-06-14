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
# spec — browsers refuse the response. Instead we whitelist concrete origins AND
# match a regex so participants/judges hitting the app from another device on the
# LAN (or via an ngrok tunnel) aren't blocked with a "No Access-Control-Allow-
# Origin" error. The regex covers localhost, loopback, private LAN ranges on any
# port, and ngrok hosts; each request still echoes back its own specific origin.
_CORS_ALLOW_ORIGIN_REGEX = (
    r"^https?://("
    r"localhost"
    r"|127\.0\.0\.1"
    r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r"|192\.168\.\d{1,3}\.\d{1,3}"
    r")(:\d+)?$"
    r"|^https://[a-z0-9-]+\.ngrok(-free)?\.(app|io)$"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://172.28.33.80:3000",
    ],
    allow_origin_regex=_CORS_ALLOW_ORIGIN_REGEX,
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

@app.on_event("startup")
async def start_deadline_scheduler():
    """Background timer that enforces time even when no request comes in.

    Every 60s it sweeps active events and disqualifies non-submitters whose
    current round's submission deadline has passed. Idempotent and best-effort —
    a single failed tick never stops the loop. Minimal by design (no Celery /
    APScheduler); swap to APScheduler if cron-precise timing is ever needed.
    """
    import asyncio

    async def _loop():
        from app.core.database import AsyncSessionLocal
        from app.services.time_enforcement import run_deadline_sweep_once

        while True:
            try:
                async with AsyncSessionLocal() as session:
                    await run_deadline_sweep_once(session)
            except Exception as exc:
                print(f"[scheduler] deadline sweep tick failed: {exc}")
            await asyncio.sleep(60)

    asyncio.create_task(_loop())
    print("[scheduler] deadline sweep started (60s interval)")


@app.get("/")
def root():
    return {"message": "Welcome to EKAM API"}
