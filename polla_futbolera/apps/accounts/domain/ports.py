from typing import Protocol
from .entities import UserProfile
import uuid


class UserProfileRepositoryPort(Protocol):
    def get_by_user_id(self, user_id: uuid.UUID) -> UserProfile | None: ...
    def save(self, profile: UserProfile) -> UserProfile: ...
