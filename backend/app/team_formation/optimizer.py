from ortools.sat.python import cp_model
from collections import defaultdict
from app.team_formation.vectorizer import build_vector, compute_distance_matrix
import numpy as np


def form_teams(participants, team_size=3):
    n = len(participants)
    num_teams = n // team_size
    leftover = n % team_size  # participants who don't fit

    if num_teams == 0:
        raise ValueError(f"Not enough participants ({n}) to form teams of {team_size}")

    # only use participants that fit evenly
    # leftover participants flagged separately
    usable = participants[:num_teams * team_size]
    leftover_participants = participants[num_teams * team_size:]

    # distance matrix
    dist_matrix = compute_distance_matrix(usable)
    scale = 1000
    dist = (dist_matrix * scale).astype(int)

    model = cp_model.CpModel()

    # x[i][t] = 1 if participant i assigned to team t
    x = {}
    for i in range(len(usable)):
        for t in range(num_teams):
            x[i, t] = model.NewBoolVar(f"x_{i}_{t}")

    # constraint 1: each participant in exactly one team
    for i in range(len(usable)):
        model.AddExactlyOne(x[i, t] for t in range(num_teams))

    # constraint 2: each team has exactly team_size members
    for t in range(num_teams):
        model.Add(
            sum(x[i, t] for i in range(len(usable))) == team_size
        )

    # constraint 3: no same institution per team
    institution_groups = defaultdict(list)
    for i, p in enumerate(usable):
        inst = p.get("institution", "Unknown")
        institution_groups[inst].append(i)

    for inst, members in institution_groups.items():
        for t in range(num_teams):
            model.Add(sum(x[i, t] for i in members) <= 1)

    # pairwise diversity variables
    pair = {}
    for i in range(len(usable)):
        for j in range(i + 1, len(usable)):
            for t in range(num_teams):
                pair[i, j, t] = model.NewBoolVar(f"pair_{i}_{j}_{t}")
                model.AddMinEquality(
                    pair[i, j, t], [x[i, t], x[j, t]]
                )

    # objective: maximize total pairwise diversity
    model.Maximize(
        sum(
            dist[i][j] * pair[i, j, t]
            for i in range(len(usable))
            for j in range(i + 1, len(usable))
            for t in range(num_teams)
        )
    )

    # solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise Exception("CP-SAT could not find a valid team formation")

    # extract teams
    teams = defaultdict(list)
    for i in range(len(usable)):
        for t in range(num_teams):
            if solver.Value(x[i, t]) == 1:
                teams[t].append(usable[i])

    return dict(teams), leftover_participants


def compute_team_diversity_score(members):
    if len(members) < 2:
        return 0.0
    dist_matrix = compute_distance_matrix(members)
    n = len(members)
    total = sum(
        dist_matrix[i][j]
        for i in range(n)
        for j in range(i + 1, n)
    )
    pairs = n * (n - 1) / 2
    return round(float(total / pairs), 3)