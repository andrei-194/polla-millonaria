from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class MemberRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"


@dataclass
class Group:
    name: str
    slug: str
    created_by_id: uuid.UUID
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    description: str = ""
    invitation_code: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GroupMembership:
    user_id: uuid.UUID
    group_id: uuid.UUID
    role: MemberRole
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    joined_at: datetime = field(default_factory=datetime.utcnow)

    def is_admin(self) -> bool:
        return self.role == MemberRole.ADMIN
