import os
import json
import time
from google import genai
from google.genai.errors import ServerError

# Initialize client safely
try:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
except Exception:
    client = None

def get_local_fallback(team_members: list) -> dict:
    """Generates a rationale instantly without making any API calls."""
    skills = []
    domains = []
    experience_levels = []
    
    for p in team_members:
        if p.get("skills"):
            skills.extend(p.get("skills"))
        if p.get("domain"):
            domains.append(p.get("domain"))
        if p.get("experience_level"):
            experience_levels.append(p.get("experience_level"))
            
    unique_skills = list(set(skills))[:3]
    unique_domains = list(set(domains))
    
    return {
        "rationale": f"This team blends expertise across {', '.join(unique_domains)}. The diverse skill mix ensures solid ground for cross-functional performance during the hackathon.",
        "strengths": unique_skills if unique_skills else ["Cross-domain collaboration", "Technical adaptability"],
        "watch_out_for": "Ensuring effective alignment on project scope during the opening hours."
    }

def generate_rationale(team_members: list, team_name: str) -> dict:
    # If API key is missing entirely, skip to fallback
    if not os.environ.get("GEMINI_API_KEY") or not client:
        return get_local_fallback(team_members)

    simplified = [
        {
            "name": p.get("name", "Participant"),
            "institution": p.get("institution", "Unknown"),
            "skills": p.get("skills", []),
            "experience_level": p.get("experience_level", "Intermediate"),
            "domain": p.get("domain", "Unknown")
        }
        for p in team_members
    ]

    prompt = f"""
You are an event organizer reviewing team compositions for a hackathon.
Team name: {team_name}
Team members: {json.dumps(simplified)}

Return ONLY valid JSON:
{{
    "rationale": "3-4 sentence explanation of why this team works well",
    "strengths": ["strength 1", "strength 2", "strength 3"],
    "watch_out_for": "one potential challenge this team might face"
}}
"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Trying 2.5 Flash
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt
            )
            
            raw = response.text.strip()
            
            # Basic markdown stripping
            if raw.startswith("```"):
                if raw.startswith("```json"): raw = raw[7:]
                else: raw = raw[3:]
                if raw.endswith("```"): raw = raw[:-3]
                raw = raw.strip()

            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                start = raw.find("{")
                end = raw.rfind("}") + 1
                return json.loads(raw[start:end])

        except ServerError as e:
            # Safe checking against the SDK's internal code tracking
            error_code = getattr(e, 'code', None) or getattr(e, 'status_code', 503)
            if error_code == 503 and attempt < max_retries - 1:
                sleep_time = 3 * (attempt + 1)
                print(f"   [!] API busy for {team_name}. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
                continue
            else:
                print(f"   [!] API unavailable. Using local fallback for {team_name}.")
                return get_local_fallback(team_members)
        except Exception:
            print(f"   [!] Unexpected error. Using local fallback for {team_name}.")
            return get_local_fallback(team_members)

    return get_local_fallback(team_members)