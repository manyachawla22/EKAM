"""
EKAM Unified Token Verification

Supports two token types:
- Firebase ID tokens (for organizer/admin login)
- EKAM JWTs (for all actors after session creation)

The verify_token dependency auto-detects the token type.
"""

import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.jwt import verify_jwt

security = HTTPBearer()

# Initialize Firebase only if not mocking and credentials are available
if not settings.MOCK_AUTH and settings.FIREBASE_CREDENTIALS_PATH:
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
        except Exception:
            pass  # Firebase init may fail in dev; MOCK_AUTH handles it


def _verify_firebase_token(token: str) -> dict:
    """Verify a Firebase ID token and return decoded claims."""
    try:
        decoded_token = auth.verify_id_token(
            token,
            clock_skew_seconds=10
        )
        return {
            "uid": decoded_token.get("uid"),
            "email": decoded_token.get("email", ""),
            "name": decoded_token.get("name", ""),
            "token_source": "firebase",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _verify_ekam_jwt(token: str) -> dict:
    """Verify an EKAM-issued JWT and return payload."""
    payload = verify_jwt(token)  # raises HTTPException on failure
    payload["token_source"] = "ekam_jwt"
    return payload


def _verify_mock_token(token: str) -> dict:
    """
    Mock token format:  mock_uid:role:email
    For local development only.
    """
    parts = token.split(":")
    if len(parts) >= 1:
        return {
            "uid": parts[0],
            "email": parts[2] if len(parts) > 2 else f"{parts[0]}@example.com",
            "role": parts[1] if len(parts) > 1 else "participant",
            "token_source": "mock",
        }
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid mock token format",
    )


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """
    Unified token verification dependency.

    Detection order:
    1. MOCK_AUTH → mock token
    2. Token contains '.' dots → try EKAM JWT first, fallback to Firebase
    3. Otherwise → Firebase
    """
    token = credentials.credentials

    # ---- Mock auth ----
    if settings.MOCK_AUTH:
        return _verify_mock_token(token)

    # ---- Real auth: try EKAM JWT first (3-part dot-separated) ----
    dot_count = token.count(".")

    if dot_count == 2:
        # Could be EKAM JWT or Firebase ID token — both are JWTs.
        # Try EKAM first (cheaper, no network call).
        try:
            return _verify_ekam_jwt(token)
        except HTTPException:
            # Not an EKAM JWT → fall through to Firebase
            pass

    # ---- Fallback: Firebase ID token ----
    return _verify_firebase_token(token)


async def verify_firebase_only(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """Dependency that ONLY accepts Firebase tokens (organizer login)."""
    token = credentials.credentials

    if settings.MOCK_AUTH:
        return _verify_mock_token(token)

    return _verify_firebase_token(token)
