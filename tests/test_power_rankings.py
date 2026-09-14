from sleeperbot.power_rankings import compute_power_rankings


def test_empty_input():
    assert compute_power_rankings({}) == []


def test_dominant_team_ranks_first_and_last_ranks_last():
    weekly_scores = {
        1: [120, 130, 110],  # always highest score
        2: [90, 95, 100],    # always lowest score
        3: [100, 105, 95],   # always middle
    }
    ranking = compute_power_rankings(weekly_scores)
    order = [roster_id for roster_id, _ in ranking]
    assert order[0] == 1
    assert order[-1] == 2


def test_ties_produce_equal_scores():
    weekly_scores = {1: [100, 100], 2: [100, 100]}
    ranking = dict(compute_power_rankings(weekly_scores))
    assert ranking[1] == ranking[2]
