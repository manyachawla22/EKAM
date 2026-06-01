from typing import List, Dict, Any
from app.judge_assignment.optimizer import assign_judges

async def generate_assignments(
    judges: List[Dict[str, Any]],
    teams: List[Dict[str, Any]],
    judges_per_team: int = 2,
    max_teams_per_judge: int = 5
) -> List[Dict[str, Any]]:
    """
    Pure optimization service. No DB writes.
    Runs the CP-SAT judge assignment optimizer.
    """
    assignments = assign_judges(
        judges=judges,
        teams=teams,
        judges_per_team=judges_per_team,
        max_teams_per_judge=max_teams_per_judge
    )
    return assignments