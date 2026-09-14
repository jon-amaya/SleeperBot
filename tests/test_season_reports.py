import pytest

from sleeperbot import charts, formatting
from sleeperbot.models import Matchup, Team


def team(roster_id, name):
    return Team(roster_id=roster_id, name=name)


class SeasonLeague:
    """Two teams per week over a controllable number of weeks."""

    def __init__(self, weekly_scores, names=None, current_week=None):
        self.weekly_scores = weekly_scores  # {week: {roster_id: score}}
        self._names = names or {1: "Alpha", 2: "Beta"}
        self.current_week = current_week or (max(weekly_scores) + 1 if weekly_scores else 1)
        self.roster_positions = ["QB", "BN"]
        self.playoff_teams = 0

    def teams(self):
        return [team(rid, name) for rid, name in self._names.items()]

    def standings(self):
        return self.teams()

    def box_scores(self, week=None):
        scores = self.weekly_scores.get(week)
        if not scores:
            return []
        ids = sorted(scores)
        return [
            Matchup(
                matchup_id=1,
                home=team(ids[0], self._names[ids[0]]),
                away=team(ids[1], self._names[ids[1]]),
                home_score=scores[ids[0]],
                away_score=scores[ids[1]],
                home_bench_points=5.0,
                away_bench_points=10.0,
            )
        ]


def test_win_matrix_holds_until_two_weeks_complete():
    one_week = SeasonLeague({1: {1: 100.0, 2: 90.0}})
    assert formatting.build_win_matrix(one_week) == ""


def test_win_matrix_ranks_by_all_play_record():
    league = SeasonLeague({1: {1: 100.0, 2: 90.0}, 2: {1: 120.0, 2: 80.0}})
    text = formatting.build_win_matrix(league)
    assert "Alpha" in text
    assert text.index("Alpha") < text.index("Beta")


def test_trophy_case_holds_until_two_weeks_complete():
    assert formatting.build_trophy_case(SeasonLeague({1: {1: 100.0, 2: 90.0}})) == ""


def test_trophy_case_counts_high_scores():
    league = SeasonLeague({1: {1: 100.0, 2: 90.0}, 2: {1: 120.0, 2: 80.0}})
    text = formatting.build_trophy_case(league)
    # Alpha took the high score both weeks; its 👑 column should read 2.
    alpha_row = next(line for line in text.splitlines() if line.startswith("Alpha"))
    assert alpha_row.split()[1] == "2"


def test_fortune_index_rewards_winning_with_a_low_score():
    # Beta wins week 2 despite scoring less than Alpha did in week 1.
    league = SeasonLeague({1: {1: 100.0, 2: 90.0}, 2: {1: 80.0, 2: 85.0}})
    text = formatting.build_fortune_index(league)
    assert "Fortune Index" in text
    assert "Alpha" in text and "Beta" in text


def test_season_weeks_skips_weeks_with_no_games():
    league = SeasonLeague({1: {1: 100.0, 2: 90.0}, 2: {}, 3: {1: 95.0, 2: 99.0}})
    assert sorted(formatting.season_weeks(league, through=3)) == [1, 3]


@pytest.mark.parametrize(
    "names,expected",
    [
        ({1: "Chalupa Batman", 2: "Pardoned turkey"}, ["CHAL", "PARD"]),
        # Same first four letters must not collide.
        ({1: "Team Braindead", 2: "Team Braveheart"}, ["TEAM", "TEAMB"]),
    ],
)
def test_abbreviations_are_unique(names, expected):
    teams = [team(rid, name) for rid, name in names.items()]
    tags = [t.strip() for t in formatting.abbreviations(teams).values()]
    assert tags == expected
    assert len(set(tags)) == len(tags)


def test_abbreviations_pad_to_a_common_width():
    teams = [team(1, "Team Braindead"), team(2, "Team Braveheart")]
    tags = list(formatting.abbreviations(teams).values())
    assert len({len(t) for t in tags}) == 1


def test_charts_render_a_png():
    names = {1: "Alpha", 2: "Beta"}
    png = charts.weekly_scores_chart({1: {1: 100.0, 2: 90.0}, 2: {1: 110.0, 2: 95.0}}, names)
    assert png.startswith(b"\x89PNG")
    assert len(png) > 1000


def test_charts_return_none_without_data():
    assert charts.weekly_scores_chart({}, {}) is None
    assert charts.bad_management_chart({}, {}) is None
