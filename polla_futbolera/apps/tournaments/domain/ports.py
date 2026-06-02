from typing import Protocol
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class MatchDTO:
    external_id: str
    home_team_name: str
    away_team_name: str
    home_team_code: str
    away_team_code: str
    match_date: datetime
    phase: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: str = "scheduled"


@dataclass
class ResultDTO:
    external_id: str
    home_score: int
    away_score: int
    status: str


class FootballAPIPort(Protocol):
    def fetch_fixtures(self, tournament_code: str, season: str) -> list[MatchDTO]: ...
    def fetch_results(self, match_external_id: str) -> ResultDTO: ...
