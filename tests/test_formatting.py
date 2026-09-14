from sleeperbot import formatting
from sleeperbot.models import Matchup, Team


def make_team(roster_id, name, wins=0, losses=0):
    return Team(roster_id=roster_id, name=name, wins=wins, losses=losses)


class FakeLeague:
    def __init__(self, box_scores=None, teams=None, current_week=1):
        self._box_scores = box_scores or []
        self._teams = teams or []
        self.current_week = current_week

    def box_scores(self, week=None):
        return self._box_scores

    def teams(self):
        return self._teams

    def standings(self):
        return sorted(self._teams, key=lambda t: (-t.wins, -t.fpts))


def test_build_standings_orders_by_wins():
    teams = [make_team(1, "Alpha", wins=3, losses=1), make_team(2, "Beta", wins=1, losses=3)]
    text = formatting.build_standings(FakeLeague(teams=teams))
    assert text.index("Alpha") < text.index("Beta")


def test_build_scoreboard_no_games():
    assert formatting.build_scoreboard(FakeLeague()) == formatting.NO_MATCHUP_DATA


def test_build_scoreboard_bye_is_excluded():
    home = make_team(1, "Alpha")
    bye = Matchup(matchup_id=1, home=home, away=None, home_score=100.0, away_score=0.0)
    assert formatting.build_scoreboard(FakeLeague(box_scores=[bye])) == formatting.NO_MATCHUP_DATA


def test_build_trophies_high_low_and_bench():
    home = make_team(1, "Alpha")
    away = make_team(2, "Beta")
    matchup = Matchup(
        matchup_id=1, home=home, away=away,
        home_score=150.0, away_score=90.0,
        home_bench_points=10.0, away_bench_points=40.0,
    )
    text = formatting.build_trophies(FakeLeague(box_scores=[matchup]))
    assert "Alpha (150.00)" in text  # most points
    assert "Beta (90.00)" in text  # least points
    assert "Most Points Left on Bench: Beta (40.00)" in text


def test_build_close_scores_filters_by_threshold():
    home = make_team(1, "Alpha")
    away = make_team(2, "Beta")
    close = Matchup(matchup_id=1, home=home, away=away, home_score=100.0, away_score=95.0)
    blowout = Matchup(matchup_id=2, home=home, away=away, home_score=150.0, away_score=50.0)
    text = formatting.build_close_scores(FakeLeague(box_scores=[close, blowout]), threshold=10.0)
    assert "100.00" in text
    assert "150.00" not in text


def test_build_waiver_report_empty_when_no_transactions_today():
    class NoTxnLeague(FakeLeague):
        def transactions_for_week(self, week):
            return []

    assert formatting.build_waiver_report(NoTxnLeague(current_week=1), today="2026-09-17") == ""
