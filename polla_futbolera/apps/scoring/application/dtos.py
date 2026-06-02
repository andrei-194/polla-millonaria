from dataclasses import dataclass


@dataclass
class LeaderboardEntryDTO:
    username: str
    user_id: int
    total_points: int
    exact_count: int
    winner_count: int
    miss_count: int
