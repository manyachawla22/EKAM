from ortools.sat.python import cp_model
from collections import defaultdict
from app.team_formation.vectorizer import compute_distance_matrix
import numpy as np


EXPERIENCE_MAP = {
    "Beginner": 0,
    "Intermediate": 1,
    "Advanced": 2
}


def _has_skill(participant, skill):
    return skill in (participant.get("skills") or [])


def form_teams(participants, team_size=3, constraints=None):

    if constraints is None:
        constraints = []

    n = len(participants)

    num_teams = n // team_size

    leftover = n % team_size

    if num_teams == 0:
        raise ValueError(
            f"Not enough participants ({n}) to form teams of {team_size}"
        )

    usable = participants[:num_teams * team_size]

    leftover_participants = participants[num_teams * team_size:]

    dist_matrix = compute_distance_matrix(usable)

    scale = 1000

    dist = (dist_matrix * scale).astype(int)

    model = cp_model.CpModel()

    x = {}

    for i in range(len(usable)):
        for t in range(num_teams):
            x[i, t] = model.NewBoolVar(f"x_{i}_{t}")

    # each participant exactly one team

    for i in range(len(usable)):
        model.AddExactlyOne(
            x[i, t] for t in range(num_teams)
        )

    # exact team size

    for t in range(num_teams):
        model.Add(
            sum(x[i, t] for i in range(len(usable)))
            == team_size
        )

    # chatbot constraints

    for constraint in constraints:

        ctype = constraint.get("type")

        # avoid same college

        if ctype == "avoid_same_college":

            institution_groups = defaultdict(list)

            for i, p in enumerate(usable):

                inst = p.get("institution", "Unknown")

                institution_groups[inst].append(i)

            for _, members in institution_groups.items():

                if len(members) <= 1:
                    continue

                for t in range(num_teams):

                    model.Add(
                        sum(x[i, t] for i in members)
                        <= 1
                    )

        # at least X females per team

        elif ctype == "gender_diversity":

            min_per_team = constraint.get(
                "min_per_team",
                1
            )

            for t in range(num_teams):

                female_members = []

                for i, p in enumerate(usable):

                    gender = (
                        p.get("gender") or ""
                    ).lower()

                    if gender in [
                        "female",
                        "woman",
                        "f"
                    ]:
                        female_members.append(
                            x[i, t]
                        )

                if female_members:

                    model.Add(
                        sum(female_members)
                        >= min_per_team
                    )

        # balanced experience

        elif ctype == "balance_experience":

            for t in range(num_teams):

                exp_terms = []

                for i, p in enumerate(usable):

                    exp = EXPERIENCE_MAP.get(
                        p.get("experience_level"),
                        1
                    )

                    exp_terms.append(
                        exp * x[i, t]
                    )

                total_exp = sum(exp_terms)

                model.Add(total_exp >= 1)

                model.Add(
                    total_exp <= (
                        team_size * 2
                    )
                )

        # required skill

        elif ctype == "required_skill":

            skill = constraint.get("skill")

            min_count = constraint.get(
                "min_count",
                1
            )

            for t in range(num_teams):

                skilled_members = []

                for i, p in enumerate(usable):

                    if _has_skill(p, skill):

                        skilled_members.append(
                            x[i, t]
                        )

                if skilled_members:

                    model.Add(
                        sum(skilled_members)
                        >= min_count
                    )

    # pairwise diversity vars

    pair = {}

    for i in range(len(usable)):

        for j in range(i + 1, len(usable)):

            for t in range(num_teams):

                pair[i, j, t] = model.NewBoolVar(
                    f"pair_{i}_{j}_{t}"
                )

                model.AddMinEquality(
                    pair[i, j, t],
                    [x[i, t], x[j, t]]
                )

    # maximize diversity

    model.Maximize(

        sum(

            dist[i][j] * pair[i, j, t]

            for i in range(len(usable))

            for j in range(i + 1, len(usable))

            for t in range(num_teams)

        )

    )

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = 30

    status = solver.Solve(model)

    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE
    ):
        raise Exception(
            "CP-SAT could not find a valid team formation"
        )

    teams = defaultdict(list)

    for i in range(len(usable)):

        for t in range(num_teams):

            if solver.Value(x[i, t]) == 1:

                teams[t].append(
                    usable[i]
                )

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

    return round(
        float(total / pairs),
        3
    )
