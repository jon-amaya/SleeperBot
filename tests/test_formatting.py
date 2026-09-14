from sleeperbot import formatting
from sleeperbot.models import Matchup, Team


def make_team(roster_id, name, wins=0, losses=0):
    return Team(roster_id=roster_id, name=name, wins=wins, losses=losses)


class FakeLeague:
    def __init__(self, box_scores=None, teams=None, current_week=1, playoff_teams=0):
        self._box_scores = box_scores or []
        self._teams = teams or []
        self.current_week = current_week
        self.playoff_teams = playoff_teams
        self.roster_positions = ["QB", "RB", "WR", "TE", "FLEX", "BN"]

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


def test_build_trophies_high_low_and_luck():
    home = make_team(1, "Alpha")
    away = make_team(2, "Beta")
    matchup = Matchup(
        matchup_id=1, home=home, away=away,
        home_score=150.0, away_score=90.0,
        home_bench_points=10.0, away_bench_points=40.0,
    )
    text = formatting.build_trophies(FakeLeague(box_scores=[matchup]))
    assert "Alpha with 150.00 points" in text
    assert "Beta with 90.00 points" in text
    assert "Alpha blew out Beta by 60.00 points" in text
    assert "🍀 Lucky 🍀" in text


def test_build_standings_inserts_playoff_line():
    teams = [make_team(i, f"Team {i}", wins=12 - i) for i in range(1, 7)]
    text = formatting.build_standings(FakeLeague(teams=teams, playoff_teams=4))
    lines = text.splitlines()
    playoff_line = next(i for i, line in enumerate(lines) if "playoff line" in line)
    # Header + blank line, then 4 qualifying teams, then the divider.
    assert playoff_line == 2 + 4


def test_build_standings_without_playoff_setting_has_no_line():
    teams = [make_team(1, "Alpha", wins=1)]
    assert "playoff line" not in formatting.build_standings(FakeLeague(teams=teams))


def test_has_sendable_content_drops_sentinels():
    assert formatting.has_sendable_content("Score Update\n\nAlpha 100.00")
    assert not formatting.has_sendable_content(formatting.NO_MATCHUP_DATA)
    assert not formatting.has_sendable_content(formatting.NO_TROPHY_DATA)
    assert not formatting.has_sendable_content("")
    assert not formatting.has_sendable_content("   \n ")


def test_build_monitor_all_clear_when_nobody_hurt():
    class HealthyLeague(FakeLeague):
        def player_injury(self, pid):
            return None

    home, away = make_team(1, "Alpha"), make_team(2, "Beta")
    m = Matchup(
        matchup_id=1, home=home, away=away, home_score=1.0, away_score=2.0,
        home_entry={"starters": ["100"]}, away_entry={"starters": ["200"]},
    )
    text = formatting.build_monitor(HealthyLeague(box_scores=[m]))
    assert text == "No Players to Monitor this week. Good Luck!"


def test_build_monitor_sorts_out_before_questionable():
    class HurtLeague(FakeLeague):
        def player_injury(self, pid):
            return {"100": "Questionable", "200": "Out"}.get(pid)

        def player_position(self, pid):
            return {"100": "WR", "200": "RB"}[pid]

        def player_name(self, pid):
            return {"100": "Alpha Receiver", "200": "Beta Back"}[pid]

    home = make_team(1, "Alpha")
    away = make_team(2, "Beta")
    m = Matchup(
        matchup_id=1, home=home, away=away, home_score=1.0, away_score=2.0,
        home_entry={"starters": ["100", "200"]}, away_entry={"starters": []},
    )
    text = formatting.build_monitor(HurtLeague(box_scores=[m]))
    assert text.index("Beta Back - Out") < text.index("Alpha Receiver - Questionable")


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
