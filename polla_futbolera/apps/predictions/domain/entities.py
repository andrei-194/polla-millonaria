from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class Prediction:
    user_id: uuid.UUID
    match_id: uuid.UUID
    group_id: uuid.UUID
    home_goals: int
    away_goals: int
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    submitted_at: datetime = field(default_factory=datetime.utcnow)

    def is_exact(self, home_result: int, away_result: int) -> bool:
        return self.home_goals == home_result and self.away_goals == away_result

    def is_winner_correct(self, home_result: int, away_result: int) -> bool:
        def outcome(h, a):
            if h > a:
                return "home"
            if a > h:
                return "away"
            return "draw"

        return outcome(self.home_goals, self.away_goals) == outcome(home_result, away_result)
