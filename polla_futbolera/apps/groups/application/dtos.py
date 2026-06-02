from dataclasses import dataclass


@dataclass
class CreateGroupDTO:
    name: str
    description: str
    created_by_id: int


@dataclass
class JoinGroupDTO:
    invitation_code: str
    user_id: int
