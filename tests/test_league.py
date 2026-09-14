from sleeperbot.league import SleeperLeague


class FakeClient:
    def __init__(self):
        self._players = {
            "100": {"full_name": "Justin Jefferson", "position": "WR"},
            "200": {"full_name": "Travis Kelce", "position": "TE"},
        }

    def get_league(self):
        return {"settings": {"waiver_type": 2, "waiver_budget": 100, "leg": 5}}

    def get_users(self):
        return [
            {"user_id": "u1", "display_name": "jon", "metadata": {"team_name": "Alpha Squad"}},
            {"user_id": "u2", "display_name": "sam", "metadata": {}},
        ]

    def get_rosters(self):
        return [
            {
                "roster_id": 1, "owner_id": "u1",
                "settings": {"wins": 3, "losses": 1, "fpts": 400, "fpts_against": 350},
            },
            {
                "roster_id": 2, "owner_id": "u2",
                "settings": {"wins": 1, "losses": 3, "fpts": 300, "fpts_against": 360},
            },
        ]

    def get_nfl_state(self):
        return {"week": 5}

    def get_matchups(self, week):
        return [
            {
                "roster_id": 1, "matchup_id": 1, "points": 120.5,
                "starters": ["100"], "players_points": {"100": 20.0, "200": 8.0},
            },
            {
                "roster_id": 2, "matchup_id": 1, "points": 99.0,
                "starters": ["200"], "players_points": {"200": 15.0},
            },
        ]

    def get_transactions(self, round_):
        return [
            {
                "status": "complete", "type": "waiver", "roster_ids": [1],
                "adds": {"100": 1}, "drops": {"200": 1},
                "settings": {"waiver_bid": 25}, "status_updated": 1234567890000,
            }
        ]

    def get_players(self):
        return self._players


def test_team_names_prefer_custom_team_name_then_display_name():
    league = SleeperLeague(FakeClient())
    assert league.team_name(1) == "Alpha Squad"
    assert league.team_name(2) == "sam"


def test_is_faab_reads_waiver_type():
    assert SleeperLeague(FakeClient()).is_faab is True


def test_current_week_prefers_league_leg_over_live_nfl_state():
    # FakeClient's get_nfl_state returns week=5, but this league's own settings.leg
    # is what should win -- a league from a past or paused season must not report
    # the live NFL week as its own.
    league = SleeperLeague(FakeClient())
    assert league.current_week == 5


def test_current_week_falls_back_to_nfl_state_when_leg_missing():
    class NoLegClient(FakeClient):
        def get_league(self):
            return {"settings": {"waiver_type": 2}}

        def get_nfl_state(self):
            return {"week": 7}

    league = SleeperLeague(NoLegClient())
    assert league.current_week == 7


def test_standings_sorted_by_wins_then_points():
    standings = SleeperLeague(FakeClient()).standings()
    assert [t.roster_id for t in standings] == [1, 2]


def test_box_scores_pairs_up_matchup_and_computes_bench_points():
    league = SleeperLeague(FakeClient())
    matchups = league.box_scores(week=5)
    assert len(matchups) == 1
    m = matchups[0]
    assert m.home.roster_id == 1 and m.home_score == 120.5
    assert m.away.roster_id == 2 and m.away_score == 99.0
    assert m.home_bench_points == 8.0  # "200" not in home's starters
    assert m.away_bench_points == 0.0  # "200" is away's only starter


def test_transactions_resolve_player_names_and_faab():
    league = SleeperLeague(FakeClient())
    items = league.transactions_for_week(5)
    assert len(items) == 1
    item = items[0]
    assert item.team_name == "Alpha Squad"
    assert item.adds == ["WR - Justin Jefferson"]
    assert item.drops == ["TE - Travis Kelce"]
    assert item.faab == 25
