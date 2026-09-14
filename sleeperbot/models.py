from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Team:
    roster_id: int
    name: str
    wins: int = 0
    losses: int = 0
    ties: int = 0
    fpts: float = 0.0
    fpts_against: float = 0.0

    @property
    def record(self):
        record = f"{self.wins}-{self.losses}"
        if self.ties:
            record += f"-{self.ties}"
        return record


@dataclass
class Matchup:
    matchup_id: Optional[int]
    home: Team
    away: Optional[Team]
    home_score: float
    away_score: float
    home_bench_points: float = 0.0
    away_bench_points: float = 0.0

    @property
    def is_bye(self):
        return self.away is None


@dataclass
class TransactionItem:
    team_name: str
    type: str = "waiver"
    adds: List[str] = field(default_factory=list)
    drops: List[str] = field(default_factory=list)
    faab: Optional[int] = None
    status_updated: Optional[int] = None
