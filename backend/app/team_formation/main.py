import httpx

import asyncio

import json

from optimizer import form_teams, compute_team_diversity_score

from rationale import generate_rationale

from fake_participants import get_fake_participants



BASE_URL = "http://localhost:8000"





async def run_team_formation(event_id: str, team_size: int = 3, use_fake: bool = False):

   

    # step 1: get participants

    if use_fake:

        print("Using fake participants for demo...")

        participants = get_fake_participants(event_id)

    else:

        async with httpx.AsyncClient() as client:

            response = await client.get(

                f"{BASE_URL}/participants/{event_id}",

                headers={"Authorization": "Bearer YOUR_TOKEN"}

            )

            if response.status_code != 200:

                raise Exception(f"Failed to fetch participants: {response.text}")

            participants = response.json()



    # filter only confirmed participants

    confirmed = [p for p in participants if p.get("status") == "confirmed"]

    print(f"Total confirmed participants: {len(confirmed)}")



    if len(confirmed) < team_size:

        raise ValueError(f"Need at least {team_size} confirmed participants")



    # step 2: CP-SAT team formation

    print("Running CP-SAT optimization...")

    raw_teams, leftover = form_teams(confirmed, team_size)

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

            "members": members,           # full data for display

            "rationale": rationale_data["rationale"],

            "strengths": rationale_data["strengths"],

            "watch_out_for": rationale_data["watch_out_for"],

            "diversity_score": diversity

        })



    # POST teams back

    if not use_fake:

        async with httpx.AsyncClient() as client:

            response = await client.post(

                f"{BASE_URL}/teams/{event_id}",

                json=result_teams,

                headers={"Authorization": "Bearer YOUR_TOKEN"}

            )

            if response.status_code not in (200, 201):

                raise Exception(f"Failed to post teams: {response.text}")

            print(f"Teams posted successfully")

    else:

        #  print for demo

        print("\n=== TEAMS FORMED ===")

        for t in result_teams:

            print(f"\n{t['name']} (diversity: {t['diversity_score']})")

            for m in t["members"]:

                print(f"  - {m['name']} | {m['institution']} | {m['skills']} | {m['domain']}")

            print(f"  Rationale: {t['rationale']}")



    return result_teams





if __name__ == "__main__":

    # demo mode —

    asyncio.run(run_team_formation(

        event_id="550e8400-e29b-41d4-a716-446655440000",

        team_size=3,

        use_fake=True   # flip to False when using real DB

    ))