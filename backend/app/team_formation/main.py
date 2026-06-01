import asyncio
import json
import os

import httpx

from app.team_formation.fake_participants import get_fake_participants
from app.team_formation.optimizer import (
    compute_team_diversity_score,
    form_teams,
)
from app.team_formation.rationale import generate_rationale


BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


def _load_constraints(event_id: str) -> list:
    """Read team-matching constraints directly from saved event config if present."""
    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data",
    )
    config_path = os.path.join(data_dir, event_id, "event.json")

    if not os.path.exists(config_path):
        print(
            f"Warning: no event config found at {config_path}, "
            "running without constraints"
        )
        return []

    with open(config_path, encoding="utf-8") as file:
        config = json.load(file)

    constraints = (
        config
        .get("participants", {})
        .get("team_matching", {})
        .get("constraints", [])
    )

    print(f"Loaded {len(constraints)} team formation constraint(s) from event config")
    return constraints


async def _fetch_constraints_from_api(
    client: httpx.AsyncClient,
    event_id: str,
    headers: dict,
    default_team_size: int,
) -> tuple[list, int]:
    response = await client.get(
        f"{BASE_URL}{API_PREFIX}/ai/constraints/{event_id}",
        headers=headers,
    )

    if response.status_code != 200:
        print("No constraints found from API, trying local config")
        return _load_constraints(event_id), default_team_size

    data = response.json()
    constraints = data.get("constraints", [])
    team_size = data.get("team_size", default_team_size)

    print(f"Loaded {len(constraints)} CP-SAT constraints from event config")
    return constraints, team_size


async def run_team_formation(
    event_id: str,
    team_size: int = 3,
    use_fake: bool = False,
    token: str = "YOUR_TOKEN",
):
    headers = {"Authorization": f"Bearer {token}"}

    if use_fake:
        print("Using fake participants for demo...")
        participants = get_fake_participants(event_id)
        constraints = []
    else:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}{API_PREFIX}/participants/{event_id}",
                headers=headers,
            )

            if response.status_code != 200:
                raise Exception(f"Failed to fetch participants: {response.text}")

            participants = response.json()

            constraints, team_size = await _fetch_constraints_from_api(
                client=client,
                event_id=event_id,
                headers=headers,
                default_team_size=team_size,
            )

    confirmed = [
        participant
        for participant in participants
        if participant.get("status") == "confirmed"
    ]

    print(f"Total confirmed participants: {len(confirmed)}")

    if len(confirmed) < team_size:
        raise ValueError(f"Need at least {team_size} confirmed participants")

    print("Running CP-SAT optimization...")
    print(f"Constraints active: {[constraint.get('type') for constraint in constraints]}")

    raw_teams, leftover = form_teams(
        confirmed,
        team_size,
        constraints=constraints,
    )

    print(f"Formed {len(raw_teams)} teams. Leftover: {len(leftover)} participants")

    result_teams = []

    for team_idx, members in raw_teams.items():
        team_name = f"Team {team_idx + 1}"

        print(f"Generating rationale for {team_name}...")

        rationale_data = generate_rationale(members, team_name)
        diversity = compute_team_diversity_score(members)

        result_teams.append(
            {
                "event_id": event_id,
                "name": team_name,
                "member_ids": [participant["id"] for participant in members],
                "members": members,
                "rationale": rationale_data["rationale"],
                "strengths": rationale_data["strengths"],
                "watch_out_for": rationale_data["watch_out_for"],
                "diversity_score": diversity,
            }
        )

    if not use_fake:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/teams/{event_id}",
                json=result_teams,
                headers=headers,
            )

            if response.status_code not in (200, 201):
                raise Exception(f"Failed to post teams: {response.text}")

            print("Teams posted successfully")
    else:
        print("\n=== TEAMS FORMED ===")
        for team in result_teams:
            print(f"\n{team['name']} (diversity: {team['diversity_score']})")

            for member in team["members"]:
                print(
                    f"  - {member['name']} | "
                    f"{member['institution']} | "
                    f"{member['skills']} | "
                    f"{member.get('domain', '')}"
                )

            print(f"  Rationale: {team['rationale']}")

    return result_teams


if __name__ == "__main__":
    asyncio.run(
        run_team_formation(
            event_id="550e8400-e29b-41d4-a716-446655440000",
            team_size=3,
            use_fake=True,
        )
    )