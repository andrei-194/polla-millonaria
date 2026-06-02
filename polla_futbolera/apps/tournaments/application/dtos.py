from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class MatchSummaryDTO:
    id: int
    home_team: str
    away_team: str
    match_date: datetime
    phase: str
    home_score: Optional[int]
    away_score: Optional[int]
    status: str
    external_id: str
