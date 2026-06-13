"""
EKAM in-process event bus (for Server-Sent Events).

A tiny async pub/sub used to push "something changed" signals to connected
clients over SSE (see ``app/routers/stream.py``). Subscribers are keyed by the
recipient's actor id (organizer User.id / Participant.id / Judge.id) — the same
id that appears as ``Notification.user_id`` and as the JWT ``sub`` — so a publish
reaches exactly the right person's open dashboards.

Design notes / boundaries:
- **In-memory, single-process.** Correct for the current single-uvicorn-worker
  deployment. If EKAM is ever run with multiple workers/processes, this must be
  swapped for a shared broker (e.g. Redis pub/sub). The publish/subscribe API
  here is deliberately small so that swap stays localized.
- We publish a *signal* (``{type, event_id, ...ids}``), never the authoritative
  payload. Clients refetch their own data through the existing authenticated
  REST endpoints, so nothing sensitive ever travels over the bus and payloads
  stay tiny.
- Per-subscriber queues are bounded; if a consumer is too slow we drop messages
  rather than grow unbounded (the 60s polling fallback still reconciles state).
"""

import asyncio
from collections import defaultdict
from typing import Dict, Iterable, Set


_QUEUE_MAXSIZE = 100


class EventBus:
    def __init__(self) -> None:
        self._subscribers: Dict[str, Set[asyncio.Queue]] = defaultdict(set)

    def subscribe(self, user_id: str) -> asyncio.Queue:
        """Register a new subscriber queue for ``user_id`` and return it."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
        self._subscribers[str(user_id)].add(queue)
        return queue

    def unsubscribe(self, user_id: str, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue; clean up empty user buckets."""
        key = str(user_id)
        subs = self._subscribers.get(key)
        if not subs:
            return
        subs.discard(queue)
        if not subs:
            self._subscribers.pop(key, None)

    async def publish(self, user_ids: Iterable, message: dict) -> None:
        """Deliver ``message`` to every queue of each (de-duplicated) user id."""
        seen: Set[str] = set()
        for raw in user_ids:
            if not raw:
                continue
            uid = str(raw)
            if uid in seen:
                continue
            seen.add(uid)
            for queue in list(self._subscribers.get(uid, ())):
                try:
                    queue.put_nowait(message)
                except asyncio.QueueFull:
                    # Slow consumer — drop this signal; polling fallback recovers.
                    pass


# Module-level singleton shared across the app.
bus = EventBus()


async def safe_publish(user_ids: Iterable, message: dict) -> None:
    """Publish without ever raising — call from best-effort side-effect paths.

    The bus must never break a request or a commit path, so any failure here is
    swallowed (the client's polling fallback will reconcile).
    """
    try:
        await bus.publish(user_ids, message)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[event_bus] publish failed: {type(exc).__name__}: {exc}")
