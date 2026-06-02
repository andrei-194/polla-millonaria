from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class TournamentStatus(str, Enum):
    ACTIVE = "active"
    FINISHED = "finished"


class MatchStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    POSTPONED = "postponed"


@dataclass
class Tournament:
    name: str
    external_code: str
    season: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: TournamentStatus = TournamentStatus.ACTIVE


@dataclass
class Team:
    name: str
    external_code: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    logo_url: str = ""


@dataclass
class Match:
    tournament_id: uuid.UUID
    home_team_id: uuid.UUID
    away_team_id: uuid.UUID
    match_date: datetime
    external_id: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    phase: str = "group"
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: MatchStatus = MatchStatus.SCHEDULED

    def has_result(self) -> bool:
        return self.home_score is not None and self.away_score is not None
