"""Captcha verification for the public registration endpoints (Task 6).

Cloudflare Turnstile server-side verification. When no secret is configured
(`TURNSTILE_SECRET_KEY` empty), verification is treated as disabled and always
passes — so local/demo runs without keys still work. In production, set the
secret to enforce. Best-effort network call wrapped in a thread; a verification
*failure* (provider says invalid) returns False, but an *outage* (network error)
fails open with a logged warning so a captcha provider blip can't take down
registration.
"""

import asyncio

import requests

from app.core.config import settings


def _verify_sync(token: str, remote_ip: str | None) -> bool:
    data = {"secret": settings.TURNSTILE_SECRET_KEY, "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip
    try:
        resp = requests.post(settings.TURNSTILE_VERIFY_URL, data=data, timeout=8)
        resp.raise_for_status()
        body = resp.json()
        return bool(body.get("success"))
    except Exception as exc:  # provider outage → fail open (don't block registration)
        print(f"[captcha_service] verify call failed, allowing: {exc}")
        return True


async def verify(token: str | None, remote_ip: str | None = None) -> bool:
    """Return True if the captcha is valid (or disabled). False only when the
    provider explicitly rejects the token, or no token was supplied while enabled."""
    if not settings.TURNSTILE_SECRET_KEY:
        return True  # disabled
    if not token:
        return False
    return await asyncio.to_thread(_verify_sync, token, remote_ip)
