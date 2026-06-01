"""Certificate generation and SMTP helpers for EKAM.

This module provides a simple, dependency-light certificate HTML generator
and an SMTP sender. It prefers Groq when available and configured, but
works with a fallback HTML template so the codebase doesn't break when
Groq SDK isn't installed in the environment.
"""
from datetime import datetime
import os
import smtplib
from typing import Dict, Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from app.core.config import settings


def _clean_groq_html(raw: str) -> str:
    if raw.startswith("```html"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    return raw.strip()


def generate_certificate_html(
    participant_name: str,
    competition_name: str,
    achievement: str = "Participation",
    date: Optional[str] = None,
) -> str:
    """Return certificate HTML as string.

    Attempts to call Groq if API key is present; otherwise returns a
    simple but printable HTML certificate.
    """
    if not date:
        date = datetime.now().strftime("%B %d, %Y")

    api_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
    if api_key:
        try:
            from groq import Groq

            client = Groq(api_key=api_key)
            prompt = f"""
Generate only the HTML for a printable certificate.
Recipient: {participant_name}
Competition: {competition_name}
Achievement: {achievement}
Date: {date}

Return only HTML with inline CSS.
"""
            resp = client.chat.completions.create(
                model=settings.GROQ_CERT_MODEL or "mixtral-8x7b-32768",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.25,
                max_tokens=1200,
            )
            raw = ""
            if getattr(resp, "choices", None) and resp.choices[0].message:
                raw = resp.choices[0].message.content or ""
            else:
                raw = str(resp)
            return _clean_groq_html(raw)
        except Exception:
            # fall through to local template on any failure
            pass

    # Fallback HTML
    html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Certificate</title>
  <style>
    body {{ font-family: 'Segoe UI', Roboto, Arial, sans-serif; background: #fff; color: #111; }}
    .cert {{ width: 1000px; height: 700px; padding: 40px; border: 10px solid #2b6cb0; margin: 40px auto; box-sizing: border-box; }}
    .title {{ font-size: 36px; text-align: center; margin-top: 30px; }}
    .recipient {{ font-size: 28px; text-align: center; margin: 40px 0; font-weight: 700; }}
    .meta {{ text-align: center; margin-top: 20px; color: #555; }}
    .footer {{ margin-top: 60px; display:flex; justify-content:space-between; padding: 0 60px; }}
  </style>
</head>
<body>
  <div class="cert">
    <div class="title">Certificate of {achievement}</div>
    <div class="recipient">{participant_name}</div>
    <div class="meta">for participating in <strong>{competition_name}</strong></div>
    <div class="meta">Date: {date}</div>
    <div class="footer">
      <div>_____________________<br/>Organizer</div>
      <div>_____________________<br/>Team EKAM</div>
    </div>
  </div>
</body>
</html>
"""
    return html


def send_email_smtp(
    recipient_email: str,
    subject: str,
    body_html: str,
    body_text: str,
    attachments: Optional[Dict[str, bytes]] = None,
) -> None:
    """Send a MIME email with optional attachments via configured SMTP."""
    smtp_server = settings.SMTP_SERVER or os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(settings.SMTP_PORT or os.environ.get("SMTP_PORT", "587"))
    smtp_username = settings.SMTP_USERNAME or os.environ.get("SMTP_USERNAME", "")
    smtp_password = settings.SMTP_PASSWORD or os.environ.get("SMTP_PASSWORD", "")
    sender_email = settings.SENDER_EMAIL or os.environ.get("SENDER_EMAIL", smtp_username)
    sender_name = settings.SENDER_NAME or os.environ.get("SENDER_NAME", "EKAM")

    if not smtp_username or not smtp_password or not sender_email:
        raise RuntimeError("SMTP credentials are not configured")

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = recipient_email

    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(body_text or "", "plain"))
    alternative.attach(MIMEText(body_html or "", "html"))
    msg.attach(alternative)

    if attachments:
        for filename, file_bytes in attachments.items():
            part = MIMEBase("application", "octet-stream")
            part.set_payload(file_bytes)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={filename}")
            msg.attach(part)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
"""Certificate generation and SMTP helpers for EKAM.

This module provides a simple, dependency-light certificate HTML generator
and an SMTP sender. It prefers Groq when available and configured, but
works with a fallback HTML template so the codebase doesn't break when
Groq SDK isn't installed in the environment.
"""
from datetime import datetime
import os
import smtplib
from typing import Dict, Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from app.core.config import settings


def _clean_groq_html(raw: str) -> str:
    if raw.startswith("```html"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    return raw.strip()


def generate_certificate_html(
    participant_name: str,
    competition_name: str,
    achievement: str = "Participation",
    date: Optional[str] = None,
) -> str:
    """Return certificate HTML as string.

    Attempts to call Groq if API key is present; otherwise returns a
    simple but printable HTML certificate.
    """
    if not date:
        date = datetime.now().strftime("%B %d, %Y")

    api_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
    if api_key:
        try:
            from groq import Groq

            client = Groq(api_key=api_key)
            prompt = f"""
Generate only the HTML for a printable certificate.
Recipient: {participant_name}
Competition: {competition_name}
Achievement: {achievement}
Date: {date}

Return only HTML with inline CSS.
"""
            resp = client.chat.completions.create(
                model=settings.GROQ_CERT_MODEL or "mixtral-8x7b-32768",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.25,
                max_tokens=1200,
            )
            raw = ""
            if getattr(resp, "choices", None) and resp.choices[0].message:
                raw = resp.choices[0].message.content or ""
            else:
                raw = str(resp)
            return _clean_groq_html(raw)
        except Exception:
            # fall through to local template on any failure
            pass

    # Fallback HTML
    html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Certificate</title>
  <style>
    body {{ font-family: 'Segoe UI', Roboto, Arial, sans-serif; background: #fff; color: #111; }}
    .cert {{ width: 1000px; height: 700px; padding: 40px; border: 10px solid #2b6cb0; margin: 40px auto; box-sizing: border-box; }}
    .title {{ font-size: 36px; text-align: center; margin-top: 30px; }}
    .recipient {{ font-size: 28px; text-align: center; margin: 40px 0; font-weight: 700; }}
    .meta {{ text-align: center; margin-top: 20px; color: #555; }}
    .footer {{ margin-top: 60px; display:flex; justify-content:space-between; padding: 0 60px; }}
  </style>
</head>
<body>
  <div class="cert">
    <div class="title">Certificate of {achievement}</div>
    <div class="recipient">{participant_name}</div>
    <div class="meta">for participating in <strong>{competition_name}</strong></div>
    <div class="meta">Date: {date}</div>
    <div class="footer">
      <div>_____________________<br/>Organizer</div>
      <div>_____________________<br/>Team EKAM</div>
    </div>
  </div>
</body>
</html>
"""
    return html


def send_email_smtp(
    recipient_email: str,
    subject: str,
    body_html: str,
    body_text: str,
    attachments: Optional[Dict[str, bytes]] = None,
) -> None:
    """Send a MIME email with optional attachments via configured SMTP."""
    smtp_server = settings.SMTP_SERVER or os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(settings.SMTP_PORT or os.environ.get("SMTP_PORT", "587"))
    smtp_username = settings.SMTP_USERNAME or os.environ.get("SMTP_USERNAME", "")
    smtp_password = settings.SMTP_PASSWORD or os.environ.get("SMTP_PASSWORD", "")
    sender_email = settings.SENDER_EMAIL or os.environ.get("SENDER_EMAIL", smtp_username)
    sender_name = settings.SENDER_NAME or os.environ.get("SENDER_NAME", "EKAM")

    if not smtp_username or not smtp_password or not sender_email:
        raise RuntimeError("SMTP credentials are not configured")

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = recipient_email

    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(body_text or "", "plain"))
    alternative.attach(MIMEText(body_html or "", "html"))
    msg.attach(alternative)

    if attachments:
        for filename, file_bytes in attachments.items():
            part = MIMEBase("application", "octet-stream")
            part.set_payload(file_bytes)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={filename}")
            msg.attach(part)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
