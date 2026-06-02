from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class UserProfile:
    user_id: uuid.UUID
    bio: str = ""
    avatar_url: str = ""
    total_points: int = 0
    total_predictions: int = 0
    correct_predictions: int = 0

    @property
    def accuracy_percentage(self) -> float:
        if self.total_predictions == 0:
            return 0.0
        return (self.correct_predictions / self.total_predictions) * 100
