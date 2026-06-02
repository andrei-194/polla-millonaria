from typing import Protocol
from .entities import Prediction
import uuid


class PredictionRepositoryPort(Protocol):
    def get(
        self, user_id: uuid.UUID, match_id: uuid.UUID, group_id: uuid.UUID
    ) -> Prediction | None: ...
    def save(self, prediction: Prediction) -> Prediction: ...
    def list_for_group_match(
        self, match_id: uuid.UUID, group_id: uuid.UUID
    ) -> list[Prediction]: ...
