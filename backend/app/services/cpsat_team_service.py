from typing import List, Dict, Any
from app.team_formation.optimizer import form_teams

async def generate_teams(
    participants: List[Dict[str, Any]],
    constraints: List[Dict[str, Any]],
    team_size: int = 3
) -> tuple[Dict[int, List[Dict[str, Any]]], List[Dict[str, Any]]]:
    """
    Pure optimization service. No DB writes.
    Runs the CP-SAT team formation optimizer.
    """
    teams, leftover = form_teams(participants, team_size=team_size, constraints=constraints)
    return teams, leftover