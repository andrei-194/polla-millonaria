from typing import Protocol
from .entities import Score
import uuid


class ScoreRepositoryPort(Protocol):
    def save(self, score: Score) -> Score: ...
    def list_for_group_tournament(
        self, group_id: uuid.UUID, tournament_id: uuid.UUID
    ) -> list[Score]: ...
