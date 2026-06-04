from dataclasses import dataclass


@dataclass
class RegisterUserDTO:
    username: str
    email: str
    password: str


@dataclass
class UserProfileDTO:
    username: str
    email: str
    bio: str
    avatar_url: str
    total_points: int
    accuracy_percentage: float


@dataclass
class CreateInvitationCodeDTO:
    created_by_id: int
    expires_at: object = None
    max_uses: object = None


@dataclass
class RegisterViaCodeDTO:
    code: str
    username: str
    email: str
    password: str
