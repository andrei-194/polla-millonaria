from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class NotificationType(str, Enum):
    REMINDER = "reminder"
    RESULT = "result"
    INVITATION = "invitation"


@dataclass
class Notification:
    user_id: uuid.UUID
    notification_type: NotificationType
    message: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    read: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)
