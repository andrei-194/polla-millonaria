from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import uuid


@dataclass
class Entity:
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class DomainException(Exception):
    pass


class ValidationError(DomainException):
    pass


class NotFoundError(DomainException):
    pass


class PermissionDeniedError(DomainException):
    pass
