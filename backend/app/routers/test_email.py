from fastapi import APIRouter
from app.services.email_service import _send_email_stub

router = APIRouter(prefix="/test", tags=["Test"])

@router.get("/email")
async def test_email():

    success = await _send_email_stub(
        recipient="nehac6123@gmail.com",
        subject="EKAM Test Email",
        body="Testing SMTP from EKAM",
        email_type="test"
    )

    return {
        "success": success
    }