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
