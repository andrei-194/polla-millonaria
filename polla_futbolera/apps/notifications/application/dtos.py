from dataclasses import dataclass
from datetime import datetime


@dataclass
class NotificationDTO:
    id: int
    notification_type: str
    message: str
    read: bool
    created_at: datetime
