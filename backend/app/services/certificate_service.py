import json
from groq import Groq
from app.core.config import settings


def generate_certificate_html(
    participant_name: str,
    event_name: str,
    achievement: str = "Participation",
    date: str = ""
) -> str:
    """
    Generate a certificate HTML using Groq LLM.
    
    Args:
        participant_name: Name of the participant
        event_name: Name of the event
        achievement: Type of achievement (Participation, Winner, Finalist, etc.)
        date: Date of the event
    
    Returns:
        HTML string for the certificate
    """
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not configured")
    
    client = Groq(api_key=settings.GROQ_API_KEY)
    
    prompt = f"""
You are a professional certificate designer. Generate ONLY an HTML certificate (no markdown, no backticks) for:
- Recipient: {participant_name}
- Event: {event_name}
- Achievement: {achievement}
- Date: {date}

Create professional, elegant HTML with inline CSS. The certificate should:
1. Be centered and well-formatted
2. Include decorative borders and elegant typography
3. Have the event name, participant name, and achievement prominently displayed
4. Include a signature line for the organizer
5. Use a professional color scheme (gold, navy, or similar)
6. Be print-ready

Return ONLY valid HTML that can be saved as .html file directly.
"""
    
    response = client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[
            {{"role": "system", "content": "You are a professional certificate designer. Generate only HTML code for certificates."}},
            {{"role": "user", "content": prompt}}
        ],
        temperature=0.7,
        max_tokens=2000
    )
    
    html = response.choices[0].message.content or ""
    
    # Clean up if wrapped in markdown code blocks
    if html.startswith("```html"):
        html = html[7:]
    if html.startswith("```"):
        html = html[3:]
    if html.endswith("```"):
        html = html[:-3]
    
    return html.strip()


def generate_certificate_data(
    participant_name: str,
    event_name: str,
    achievement: str = "Participation",
    date: str = ""
) -> dict:
    """
    Generate certificate metadata using Groq LLM for personalization.
    
    Args:
        participant_name: Name of the participant
        event_name: Name of the event
        achievement: Type of achievement
        date: Date of the event
    
    Returns:
        Dictionary with certificate metadata
    """
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not configured")
    
    client = Groq(api_key=settings.GROQ_API_KEY)
    
    prompt = f"""
Generate a personalized certificate data object for:
- Recipient: {participant_name}
- Event: {event_name}
- Achievement: {achievement}
- Date: {date}

Return ONLY valid JSON (no markdown, no backticks):
{{
    "certificate_number": "cert_XXXXXX",
    "congratulatory_message": "A personalized message praising the achievement",
    "competencies_earned": ["skill1", "skill2", "skill3"],
    "display_title": "Official title for the certificate"
}}
"""
    
    response = client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[
            {{"role": "system", "content": "You are a certificate metadata generator. Return only JSON."}},
            {{"role": "user", "content": prompt}}
        ],
        temperature=0.7,
        max_tokens=500
    )
    
    raw = response.choices[0].message.content or "{}"
    
    # Clean up markdown wrapping
    if raw.startswith("```"):
        raw = raw[raw.find("{"):]
    if raw.endswith("```"):
        raw = raw[:raw.rfind("}") + 1]
    
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "certificate_number": f"cert_{hash(participant_name) % 100000}",
            "congratulatory_message": f"Congratulations {participant_name} on your participation in {event_name}!",
            "competencies_earned": [],
            "display_title": achievement
        }
