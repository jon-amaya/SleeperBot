import logging
from collections import defaultdict

from sleeperbot.models import Matchup, Team, TransactionItem

logger = logging.getLogger(__name__)


class SleeperLeague:
    """
    Adapts SleeperClient's raw REST responses into the Team/Matchup/TransactionItem
    shapes the rest of the bot works with, so formatting code never touches raw
    Sleeper JSON.
    """

    def __init__(self, client):
        self.client = client
        self._settings = client.get_league()
        self._users = client.get_users()
        self._rosters = client.get_rosters()
        self._players = None  # fetched lazily; large payload, only needed for waiver reports
        self._name_by_roster = self._build_team_names()

    @property
    def is_faab(self):
        return int((self._settings.get("settings") or {}).get("waiver_type", 0)) == 2

    @property
    def current_week(self):
        # settings.leg is this league's own current week, which is what we want --
        # state/nfl's "week" is the live NFL week across all of Sleeper, which is
        # wrong for a league that isn't in the current season (or hasn't started).
        leg = (self._settings.get("settings") or {}).get("leg")
        if leg:
            return int(leg)
        state = self.client.get_nfl_state()
        return int(state.get("week") or 1)

    def _build_team_names(self):
        user_by_id = {u["user_id"]: u for u in self._users}
        names = {}
        for roster in self._rosters:
            user = user_by_id.get(roster.get("owner_id"), {})
            metadata = user.get("metadata") or {}
            names[roster["roster_id"]] = (
                metadata.get("team_name") or user.get("display_name") or f"Team {roster['roster_id']}"
            )
        return names

    def team_name(self, roster_id):
        return self._name_by_roster.get(roster_id, f"Team {roster_id}")

    def teams(self):
        teams = []
        for roster in self._rosters:
            settings = roster.get("settings") or {}
            teams.append(
                Team(
                    roster_id=roster["roster_id"],
                    name=self.team_name(roster["roster_id"]),
                    wins=settings.get("wins", 0),
                    losses=settings.get("losses", 0),
                    ties=settings.get("ties", 0),
                    fpts=settings.get("fpts", 0) + settings.get("fpts_decimal", 0) / 100,
                    fpts_against=settings.get("fpts_against", 0) + settings.get("fpts_against_decimal", 0) / 100,
                )
            )
        return teams

    def standings(self):
        return sorted(self.teams(), key=lambda t: (-t.wins, -t.fpts))

    def players(self):
        if self._players is None:
            self._players = self.client.get_players()
        return self._players

    def player_name(self, player_id):
        player = self.players().get(str(player_id))
        if not player:
            return f"Unknown ({player_id})"
        full_name = player.get("full_name")
        if full_name:
            return full_name
        return f"{player.get('first_name', '')} {player.get('last_name', '')}".strip() or f"Unknown ({player_id})"

    def player_position(self, player_id):
        return (self.players().get(str(player_id)) or {}).get("position", "N/A")

    def box_scores(self, week=None):
        week = week or self.current_week
        raw = self.client.get_matchups(week)
        team_by_roster = {t.roster_id: t for t in self.teams()}

        by_matchup = defaultdict(list)
        for entry in raw:
            by_matchup[entry.get("matchup_id")].append(entry)

        matchups = []
        for entries in by_matchup.values():
            if len(entries) < 2:
                # A bye: Sleeper still returns a single roster entry with its own
                # matchup_id and no opponent.
                entry = entries[0]
                matchups.append(
                    Matchup(
                        matchup_id=entry.get("matchup_id"),
                        home=team_by_roster.get(entry["roster_id"]),
                        away=None,
                        home_score=entry.get("points") or 0.0,
                        away_score=0.0,
                        home_bench_points=self._bench_points(entry),
                    )
                )
                continue

            home_entry, away_entry = entries[0], entries[1]
            matchups.append(
                Matchup(
                    matchup_id=home_entry.get("matchup_id"),
                    home=team_by_roster.get(home_entry["roster_id"]),
                    away=team_by_roster.get(away_entry["roster_id"]),
                    home_score=home_entry.get("points") or 0.0,
                    away_score=away_entry.get("points") or 0.0,
                    home_bench_points=self._bench_points(home_entry),
                    away_bench_points=self._bench_points(away_entry),
                )
            )
        return matchups

    @staticmethod
    def _bench_points(entry):
        starters = set(entry.get("starters") or [])
        players_points = entry.get("players_points") or {}
        return sum(pts or 0.0 for player_id, pts in players_points.items() if player_id not in starters)

    def transactions_for_week(self, week):
        raw = self.client.get_transactions(week)
        team_by_roster = {t.roster_id: t for t in self.teams()}

        items = []
        for txn in raw:
            if txn.get("status") != "complete":
                continue
            roster_ids = txn.get("roster_ids") or []
            team = team_by_roster.get(roster_ids[0]) if roster_ids else None
            adds = txn.get("adds") or {}
            drops = txn.get("drops") or {}
            faab = None
            if txn.get("type") == "waiver":
                faab = (txn.get("settings") or {}).get("waiver_bid")

            items.append(
                TransactionItem(
                    team_name=team.name if team else "Unknown",
                    type=txn.get("type", "waiver"),
                    adds=[f"{self.player_position(pid)} - {self.player_name(pid)}" for pid in adds],
                    drops=[f"{self.player_position(pid)} - {self.player_name(pid)}" for pid in drops],
                    faab=faab,
                    status_updated=txn.get("status_updated"),
                )
            )
        return items
