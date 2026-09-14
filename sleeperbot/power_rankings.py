"""
Our own implementation of the well-known "two-step dominance" fantasy
power-ranking concept: an all-play dominance matrix (who would have beaten
whom, every week, regardless of actual schedule), followed by a second pass
that also credits a team for beating teams that themselves dominate many
others. This is not a port of any specific vendor's exact formula -- Sleeper's
API exposes no power rankings at all, unlike ESPN's, so this has to be
computed from scratch off of each team's actual weekly scores.
"""

DOMINANCE_WEIGHT = 0.80
POINTS_WEIGHT = 0.15
MARGIN_WEIGHT = 0.05


def compute_power_rankings(weekly_scores):
    """
    Parameters
    ----------
    weekly_scores : dict
        roster_id -> list of that team's actual scores, one per week played so far.

    Returns
    -------
    list of (roster_id, score) sorted descending by power ranking score.
    """
    teams = list(weekly_scores.keys())
    if not teams:
        return []

    num_weeks = min(len(scores) for scores in weekly_scores.values())
    if num_weeks == 0:
        return [(team, 0.0) for team in teams]

    dominance = _all_play_dominance(weekly_scores, teams, num_weeks)
    two_step = _two_step_dominance(dominance, teams)
    points_for = {team: sum(weekly_scores[team][:num_weeks]) for team in teams}
    margins = _average_margins(weekly_scores, teams, num_weeks)

    norm_dominance = _normalize(two_step)
    norm_points = _normalize(points_for)
    norm_margin = _normalize({team: max(value, 0.0) for team, value in margins.items()})

    final_scores = {
        team: (
            DOMINANCE_WEIGHT * norm_dominance[team]
            + POINTS_WEIGHT * norm_points[team]
            + MARGIN_WEIGHT * norm_margin[team]
        )
        for team in teams
    }
    return sorted(final_scores.items(), key=lambda item: item[1], reverse=True)


def _all_play_dominance(weekly_scores, teams, num_weeks):
    """dominance[i][j] = fraction of weeks team i's score beat team j's score."""
    dominance = {i: {} for i in teams}
    for i in teams:
        for j in teams:
            if i == j:
                continue
            wins = sum(1 for week in range(num_weeks) if weekly_scores[i][week] > weekly_scores[j][week])
            dominance[i][j] = wins / num_weeks
    return dominance


def _two_step_dominance(dominance, teams):
    two_step = {}
    other_count = max(len(teams) - 2, 1)
    for i in teams:
        total = 0.0
        for j in teams:
            if j == i:
                continue
            total += dominance[i][j]
            # Credit i for j's own dominance over everyone else, scaled by how
            # decisively i dominates j.
            total += sum(
                dominance[i][j] * dominance[j][k] for k in teams if k != i and k != j
            ) / other_count
        two_step[i] = total
    return two_step


def _average_margins(weekly_scores, teams, num_weeks):
    if len(teams) < 2:
        return {team: 0.0 for team in teams}
    margins = {}
    for i in teams:
        total = 0.0
        for week in range(num_weeks):
            league_avg_others = sum(weekly_scores[j][week] for j in teams if j != i) / (len(teams) - 1)
            total += weekly_scores[i][week] - league_avg_others
        margins[i] = total / num_weeks
    return margins


def _normalize(values):
    if not values:
        return {}
    max_value = max(values.values())
    if max_value == 0:
        return {team: 0.0 for team in values}
    return {team: 100.0 * value / max_value for team, value in values.items()}
