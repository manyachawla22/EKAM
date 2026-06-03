"""
Certificate generation and SMTP helpers for EKAM.

This module provides:
1. Groq-powered certificate HTML generation
2. Fallback certificate HTML generation
3. SMTP email sending for certificate delivery
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
    """Remove markdown code fences from LLM output."""
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
    """
    Generate certificate HTML.

    Uses Groq when configured.
    Falls back to a built-in HTML template otherwise.
    """

    if not date:
        date = datetime.now().strftime("%B %d, %Y")

    api_key = getattr(settings, "GROQ_API_KEY", None) or os.environ.get(
        "GROQ_API_KEY"
    )

    if api_key:
        try:
            from groq import Groq

            client = Groq(api_key=api_key)

            prompt = f"""
Generate ONLY the HTML for a professional printable certificate.

Recipient: {participant_name}
Competition: {competition_name}
Achievement: {achievement}
Date: {date}

Requirements:
- Modern professional design
- Elegant gold accents on a light background
- Printable
- Inline CSS
- Return only HTML
- The recipient's name "{participant_name}" MUST appear prominently as the
  largest centered text on the certificate.
"""

            response = client.chat.completions.create(
                model=getattr(settings, "GROQ_CERT_MODEL", None)
                or "llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.25,
                max_tokens=1200,
            )

            raw = response.choices[0].message.content or ""

            if raw:
                return _clean_groq_html(raw)

        except Exception as exc:
            print(f"[certificate] Groq generation failed: {exc}")

    # ------------------------------------------------------------------
    # FALLBACK CERTIFICATE
    # ------------------------------------------------------------------

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Certificate</title>

<style>
body {{
    margin: 0;
    padding: 40px;
    background: #f5f7fa;
    font-family: "Segoe UI", Arial, sans-serif;
}}

.certificate {{
    width: 1000px;
    margin: auto;
    background: white;
    border: 12px solid #2563eb;
    padding: 60px;
    text-align: center;
    box-sizing: border-box;
}}

.title {{
    font-size: 42px;
    font-weight: bold;
    color: #1e3a8a;
    margin-bottom: 30px;
}}

.subtitle {{
    font-size: 20px;
    color: #555;
}}

.name {{
    font-size: 34px;
    font-weight: bold;
    margin: 40px 0;
    color: #111;
}}

.achievement {{
    font-size: 24px;
    color: #2563eb;
    margin-top: 20px;
}}

.date {{
    margin-top: 40px;
    color: #666;
}}

.footer {{
    display: flex;
    justify-content: space-between;
    margin-top: 80px;
}}

.signature {{
    width: 220px;
    text-align: center;
}}
</style>
</head>

<body>
<div class="certificate">

<div class="title">
Certificate of Achievement
</div>

<div class="subtitle">
This certificate is proudly presented to
</div>

<div class="name">
{participant_name}
</div>

<div class="subtitle">
for participating in
</div>

<div class="achievement">
{competition_name}
</div>

<div class="subtitle">
Achievement: {achievement}
</div>

<div class="date">
Issued on {date}
</div>

<div class="footer">
    <div class="signature">
        _____________________<br>
        Event Organizer
    </div>

    <div class="signature">
        _____________________<br>
        Team EKAM
    </div>
</div>

</div>
</body>
</html>
"""


def send_email_smtp(
    recipient_email: str,
    subject: str,
    body_html: str,
    body_text: str,
    attachments: Optional[Dict[str, bytes]] = None,
) -> None:
    """
    Send email through SMTP.
    """

    smtp_server = getattr(settings, "SMTP_SERVER", None) or os.environ.get(
        "SMTP_SERVER",
        "smtp.gmail.com",
    )

    smtp_port = int(
        getattr(settings, "SMTP_PORT", None)
        or os.environ.get("SMTP_PORT", "587")
    )

    smtp_username = getattr(settings, "SMTP_USERNAME", None) or os.environ.get(
        "SMTP_USERNAME",
        "",
    )

    smtp_password = getattr(settings, "SMTP_PASSWORD", None) or os.environ.get(
        "SMTP_PASSWORD",
        "",
    )

    sender_email = getattr(settings, "SENDER_EMAIL", None) or os.environ.get(
        "SENDER_EMAIL",
        smtp_username,
    )

    sender_name = getattr(settings, "SENDER_NAME", None) or os.environ.get(
        "SENDER_NAME",
        "EKAM",
    )

    if not smtp_username or not smtp_password:
        raise RuntimeError("SMTP credentials are not configured")

    msg = MIMEMultipart("mixed")

    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = recipient_email

    alt = MIMEMultipart("alternative")

    alt.attach(MIMEText(body_text or "", "plain"))
    alt.attach(MIMEText(body_html or "", "html"))

    msg.attach(alt)

    if attachments:
        for filename, file_bytes in attachments.items():
            part = MIMEBase("application", "octet-stream")
            part.set_payload(file_bytes)

            encoders.encode_base64(part)

            part.add_header(
                "Content-Disposition",
                f"attachment; filename={filename}",
            )

            msg.attach(part)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)