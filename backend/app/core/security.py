import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

security = HTTPBearer()

if not settings.MOCK_AUTH and settings.FIREBASE_CREDENTIALS_PATH:
    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)

# Changes to be done here
# RBAC to be implemented
# but first check DataBase Schema 

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    if settings.MOCK_AUTH:
        # For mock auth, token format: mock_uid:mock_role:mock_email
        parts = token.split(":")
        if len(parts) >= 1:
            return {
                "uid": parts[0],
                "email": parts[2] if len(parts) > 2 else f"{parts[0]}@example.com",
                "role": parts[1] if len(parts) > 1 else "participant"
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid mock token format"
        )
    try:
        # Add clock skew tolerance of 10 seconds
        decoded_token = auth.verify_id_token(
            token,
            clock_skew_seconds=10  # ← Add this parameter
        )
        return decoded_token
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
