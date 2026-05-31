import httpx
import asyncio
import json

from app.team_formation.optimizer import form_teams, compute_team_diversity_score
from app.team_formation.rationale import generate_rationale
from app.team_formation.fake_participants import get_fake_participants

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


async def run_team_formation(
    event_id: str,
    team_size: int = 3,
    use_fake: bool = False,
    token: str = "YOUR_TOKEN"
):
    headers = {"Authorization": f"Bearer {token}"}

    # step 1: get participants
    if use_fake:
        print("Using fake participants for demo...")
        participants = get_fake_participants(event_id)
        constraints = []  # demo mode — no constraints from chatbot
    else:
        async with httpx.AsyncClient() as client:

            # fetch participants
            response = await client.get(
                f"{BASE_URL}{API_PREFIX}/participants/{event_id}",
                headers=headers
            )
            if response.status_code != 200:
                raise Exception(f"Failed to fetch participants: {response.text}")
            participants = response.json()

            # fetch CP-SAT constraints from Suhaani's chatbot config
            constraints_response = await client.get(
                f"{BASE_URL}{API_PREFIX}/ai/constraints/{event_id}",
                headers=headers
            )
            if constraints_response.status_code == 200:
                constraints_data = constraints_response.json()
                constraints = constraints_data.get("constraints", [])
                team_size = constraints_data.get("team_size", team_size)
                print(f"Loaded {len(constraints)} CP-SAT constraints from event config")
            else:
                print("No constraints found, running with defaults")
                constraints = []

    # filter only confirmed participants
    confirmed = [p for p in participants if p.get("status") == "confirmed"]
    print(f"Total confirmed participants: {len(confirmed)}")

    if len(confirmed) < team_size:
        raise ValueError(f"Need at least {team_size} confirmed participants")

    # step 2: CP-SAT team formation with constraints
    print("Running CP-SAT optimization...")
    print(f"Constraints active: {[c['type'] for c in constraints]}")
    raw_teams, leftover = form_teams(confirmed, team_size, constraints=constraints)
    print(f"Formed {len(raw_teams)} teams. Leftover: {len(leftover)} participants")

    # step 3: build output with rationales
    result_teams = []
    for team_idx, members in raw_teams.items():
        team_name = f"Team {team_idx + 1}"

        print(f"Generating rationale for {team_name}...")
        rationale_data = generate_rationale(members, team_name)
        diversity = compute_team_diversity_score(members)

        result_teams.append({
            "event_id": event_id,
            "name": team_name,
            "member_ids": [p["id"] for p in members],
            "members": members,
            "rationale": rationale_data["rationale"],
            "strengths": rationale_data["strengths"],
            "watch_out_for": rationale_data["watch_out_for"],
            "diversity_score": diversity
        })

    # step 4: POST teams back
    if not use_fake:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/teams/{event_id}",
                json=result_teams,
                headers=headers
            )
            if response.status_code not in (200, 201):
                raise Exception(f"Failed to post teams: {response.text}")
            print("Teams posted successfully")
    else:
        print("\n=== TEAMS FORMED ===")
        for t in result_teams:
            print(f"\n{t['name']} (diversity: {t['diversity_score']})")
            for m in t["members"]:
                print(f"  - {m['name']} | {m['institution']} | {m['skills']} | {m['domain']}")
            print(f"  Rationale: {t['rationale']}")

    return result_teams


if __name__ == "__main__":
    asyncio.run(run_team_formation(
        event_id="550e8400-e29b-41d4-a716-446655440000",
        team_size=3,
        use_fake=True
    ))