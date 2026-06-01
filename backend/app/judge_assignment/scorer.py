def calculate_match_score(judge, team):
    score = 0

    judge_expertise = [e.lower() for e in judge.get("expertise", [])]
    team_theme = team.get("theme_name", "").lower()

    # theme match — exact or partial
    for expertise in judge_expertise:
        if expertise in team_theme or team_theme in expertise:
            score += 15
            break

    # skill overlap
    team_skills = [s.lower() for s in team.get("required_skills", [])]
    overlap = len(set(judge_expertise) & set(team_skills))
    score += overlap * 5

    # different institution bonus
    team_institutions = set(
        m.get("institution", "")
        for m in team.get("members", [])
    )
    if judge.get("institution", "") not in team_institutions:
        score += 5

    # judge rating
    score += int(judge.get("rating", 5))

    return score