from dataclasses import dataclass, field
from enum import Enum
import uuid


class HitType(str, Enum):
    EXACT = "exact"
    GOAL_DIFF = "goal_diff"
    WINNER = "winner"
    MISS = "miss"


POINTS_MAP = {
    HitType.EXACT: 3,
    HitType.GOAL_DIFF: 2,
    HitType.WINNER: 1,
    HitType.MISS: 0,
}


@dataclass
class Score:
    user_id: uuid.UUID
    group_id: uuid.UUID
    tournament_id: uuid.UUID
    match_id: uuid.UUID
    points: int
    hit_type: HitType
    id: uuid.UUID = field(default_factory=uuid.uuid4)


def calculate_hit_type(
    predicted_home: int,
    predicted_away: int,
    result_home: int,
    result_away: int,
) -> HitType:
    if predicted_home == result_home and predicted_away == result_away:
        return HitType.EXACT

    def outcome(h, a):
        if h > a:
            return "home"
        if a > h:
            return "away"
        return "draw"

    predicted_diff = predicted_home - predicted_away
    result_diff = result_home - result_away

    if outcome(predicted_home, predicted_away) == outcome(result_home, result_away):
        if predicted_diff == result_diff:
            return HitType.GOAL_DIFF
        return HitType.WINNER

    return HitType.MISS
