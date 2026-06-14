"""
EKAM Server-Sent Events (SSE) endpoint.

`GET /stream?token=<jwt>` opens a long-lived `text/event-stream` connection and
pushes small JSON "something changed" signals to the authenticated user as the
backend creates notifications / approvals / anomalies / pipeline changes. The
frontend uses these to refetch instantly instead of waiting for a poll.

Why a query-param token: browsers can't attach an `Authorization` header to an
`EventSource`, so the same JWT already kept in `sessionStorage` is passed as
`?token=`. The connection is read-only and per-user scoped (we only ever push to
the authenticated actor's own queue), so this is acceptable for magic-link-grade
tokens. The token is validated identically to every other request.
"""

import asyncio
import json

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import (
    _verify_ekam_jwt,
    _verify_firebase_token,
    _verify_mock_token,
)
from app.middleware.auth import get_current_actor
from app.services.event_bus import bus

router = APIRouter()

# Seconds between keepalive comments. Must be well under typical idle-proxy
# timeouts (ngrok ~60s) so the connection isn't reaped.
_KEEPALIVE_SECONDS = 20


def _verify_raw_token(token: str) -> dict:
    """Validate a raw JWT string (EventSource can't send headers).

    Mirrors `app.core.security.verify_token` but takes the token directly rather
    than via the HTTPBearer dependency.
    """
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    if settings.MOCK_AUTH:
        return _verify_mock_token(token)

    if token.count(".") == 2:
        try:
            return _verify_ekam_jwt(token)
        except HTTPException:
            pass  # not an EKAM JWT — try Firebase

    return _verify_firebase_token(token)


async def _event_generator(request: Request, queue: asyncio.Queue, user_id: str):
    """Yield SSE frames from the subscriber queue until the client disconnects."""
    try:
        # Opening comment flushes headers and confirms the stream is live.
        yield ": connected\n\n"
        while True:
            if await request.is_disconnected():
                break
            try:
                message = await asyncio.wait_for(queue.get(), timeout=_KEEPALIVE_SECONDS)
                yield f"data: {json.dumps(message)}\n\n"
            except asyncio.TimeoutError:
                # No event in the window — send a keepalive comment.
                yield ": keepalive\n\n"
    finally:
        bus.unsubscribe(user_id, queue)


@router.get("/stream")
async def stream(
    request: Request,
    token: str = Query(..., description="EKAM JWT or Firebase ID token"),
):
    # Authenticate the same way every other endpoint does, then resolve the
    # actor so we subscribe under the exact id used as a publish target.
    #
    # IMPORTANT: do NOT use `Depends(get_db)` here. That session would stay open
    # for the entire lifetime of this long-lived SSE connection, pinning one
    # pooled DB connection per open EventSource and quickly exhausting the pool
    # (every other request then blocks waiting for a connection). The stream only
    # needs the DB for this initial auth — the generator below is pure in-memory
    # queue work — so we use a short-lived session and release its connection
    # back to the pool *before* streaming begins.
    token_data = _verify_raw_token(token)
    async with AsyncSessionLocal() as db:
        auth = await get_current_actor(token_data=token_data, db=db)
        user_id = str(auth.actor_id)

    queue = bus.subscribe(user_id)

    return StreamingResponse(
        _event_generator(request, queue, user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Disable proxy buffering (nginx / ngrok) so frames flush immediately.
            "X-Accel-Buffering": "no",
        },
    )
