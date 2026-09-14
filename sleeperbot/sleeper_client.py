import json
import os
import time

import requests

BASE_URL = "https://api.sleeper.app/v1"

# Sleeper's docs ask integrators to cache the full players/nfl dump (several MB)
# rather than refetch it on every call, so this is stored on disk with a long TTL.
PLAYERS_CACHE_PATH = os.environ.get("SLEEPER_PLAYERS_CACHE", "/tmp/sleeperbot_players.json")
PLAYERS_CACHE_TTL_SECONDS = 12 * 60 * 60


class SleeperClient:
    def __init__(self, league_id, session=None):
        self.league_id = league_id
        self.session = session or requests.Session()

    def _get(self, path):
        response = self.session.get(f"{BASE_URL}/{path}", timeout=10)
        response.raise_for_status()
        return response.json()

    def get_league(self):
        return self._get(f"league/{self.league_id}")

    def get_rosters(self):
        return self._get(f"league/{self.league_id}/rosters")

    def get_users(self):
        return self._get(f"league/{self.league_id}/users")

    def get_matchups(self, week):
        return self._get(f"league/{self.league_id}/matchups/{week}")

    def get_transactions(self, round_):
        return self._get(f"league/{self.league_id}/transactions/{round_}")

    def get_nfl_state(self):
        return self._get("state/nfl")

    def get_players(self):
        cached = self._read_players_cache()
        if cached is not None:
            return cached
        players = self._get("players/nfl")
        self._write_players_cache(players)
        return players

    def _read_players_cache(self):
        try:
            stat = os.stat(PLAYERS_CACHE_PATH)
        except OSError:
            return None
        if time.time() - stat.st_mtime > PLAYERS_CACHE_TTL_SECONDS:
            return None
        try:
            with open(PLAYERS_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def _write_players_cache(self, players):
        try:
            with open(PLAYERS_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(players, f)
        except OSError:
            # A failed cache write just means we re-fetch next time; not fatal.
            pass
