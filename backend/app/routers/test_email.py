from fastapi import APIRouter
from app.services.email_service import _send_via_resend

router = APIRouter(prefix="/test", tags=["Test"])


@router.get("/email")
async def test_email():
    """
    Sends a single test email to the configured address.
    Returns success=true if SMTP delivery succeeded, plus an error message if not.
    """
    try:
        await _send_via_resend(
            recipient="nehac6123@gmail.com",
            subject="EKAM Test Email",
            body="Testing SMTP from EKAM. If you received this, delivery is working.",
            email_type="test",
        )
        return {"success": True, "message": "Email sent successfully"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}