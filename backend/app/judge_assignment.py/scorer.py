def calculate_match_score(judge, team):

    score = 0

    judge_expertise = [
        e.lower()
        for e in judge.get("expertise", [])
    ]

    team_theme = (
        team.get("theme_name", "")
        .lower()
    )

    if team_theme in judge_expertise:
        score += 15

    team_skills = [
        s.lower()
        for s in team.get("required_skills", [])
    ]

    overlap = len(
        set(judge_expertise) &
        set(team_skills)
    )

    score += overlap * 5

    if (
        judge.get("institution")
        != team.get("institution")
    ):
        score += 5

    score += int(judge.get("rating", 5))

    return score