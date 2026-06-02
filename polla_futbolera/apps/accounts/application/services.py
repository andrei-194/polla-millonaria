from django.contrib.auth import get_user_model
from .dtos import RegisterUserDTO, UserProfileDTO
from ..domain.exceptions import UserAlreadyExistsError

User = get_user_model()


class AccountService:
    def register_user(self, dto: RegisterUserDTO) -> None:
        if User.objects.filter(username=dto.username).exists():
            raise UserAlreadyExistsError(f"Username '{dto.username}' already taken")
        if User.objects.filter(email=dto.email).exists():
            raise UserAlreadyExistsError(f"Email '{dto.email}' already registered")
        User.objects.create_user(
            username=dto.username,
            email=dto.email,
            password=dto.password,
        )

    def get_profile_dto(self, user) -> UserProfileDTO:
        profile = user.profile
        return UserProfileDTO(
            username=user.username,
            email=user.email,
            bio=profile.bio,
            avatar_url=profile.avatar.url if profile.avatar else "",
            total_points=profile.total_points,
            accuracy_percentage=profile.accuracy_percentage,
        )
