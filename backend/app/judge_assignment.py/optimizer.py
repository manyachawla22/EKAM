from ortools.sat.python import cp_model
from app.judge_assignment.scorer import calculate_match_score


def assign_judges(
    judges,
    teams,
    judges_per_team=2,
    max_teams_per_judge=5
):
    model = cp_model.CpModel()
    num_judges = len(judges)
    num_teams = len(teams)

    x = {}
    for j in range(num_judges):
        for t in range(num_teams):
            x[j, t] = model.NewBoolVar(f"x_{j}_{t}")

    # constraint 1: every team gets exactly judges_per_team judges
    for t in range(num_teams):
        model.Add(
            sum(x[j, t] for j in range(num_judges)) == judges_per_team
        )

    # constraint 2: judge workload — max teams per judge
    for j in range(num_judges):
        model.Add(
            sum(x[j, t] for t in range(num_teams)) <= max_teams_per_judge
        )

    # constraint 3: min 1 team per judge
    for j in range(num_judges):
        model.Add(
            sum(x[j, t] for t in range(num_teams)) >= 1
        )

    # constraint 4: no judge from same institution as any team member
    for j in range(num_judges):
        for t in range(num_teams):
            team_institutions = set(
                m.get("institution", "")
                for m in teams[t].get("members", [])
            )
            if judges[j].get("institution", "") in team_institutions:
                model.Add(x[j, t] == 0)

    # score matrix
    scores = {}
    for j in range(num_judges):
        for t in range(num_teams):
            scores[j, t] = int(calculate_match_score(judges[j], teams[t]))

    # objective: maximize judge-theme fit
    model.Maximize(
        sum(
            scores[j, t] * x[j, t]
            for j in range(num_judges)
            for t in range(num_teams)
        )
    )

    # solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 20
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise Exception("No feasible judge assignment found")

    assignments = []
    for j in range(num_judges):
        for t in range(num_teams):
            if solver.Value(x[j, t]) == 1:
                assignments.append({
                    "judge_id": judges[j]["id"],
                    "team_id": teams[t]["id"],
                    "match_score": scores[j, t]
                })

    return assignments