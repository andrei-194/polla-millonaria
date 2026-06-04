from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from .dtos import RegisterUserDTO, UserProfileDTO, CreateInvitationCodeDTO, RegisterViaCodeDTO
from ..domain.exceptions import (
    UserAlreadyExistsError,
    InvalidInvitationCodeError,
    InvitationCodeExhaustedError,
    InvitationCodeInactiveError,
)

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


class InvitationCodeService:

    def create_code(self, dto: CreateInvitationCodeDTO):
        from ..infrastructure.models import InvitationCode
        InvitationCode.objects.filter(created_by_id=dto.created_by_id, is_active=True).update(is_active=False)
        return InvitationCode.objects.create(
            created_by_id=dto.created_by_id,
            expires_at=dto.expires_at,
            max_uses=dto.max_uses,
        )

    def get_active_code(self):
        from ..infrastructure.models import InvitationCode
        return InvitationCode.objects.filter(is_active=True).first()

    def get_valid_code(self, code_str: str):
        from ..infrastructure.models import InvitationCode
        try:
            code = InvitationCode.objects.get(code=code_str)
        except InvitationCode.DoesNotExist:
            raise InvalidInvitationCodeError("El link de invitación no es válido.")
        if not code.is_active:
            raise InvitationCodeInactiveError("Este link de invitación fue desactivado.")
        from django.utils import timezone
        if code.expires_at and timezone.now() >= code.expires_at:
            raise InvitationCodeInactiveError("Este link de invitación expiró.")
        if code.max_uses is not None and code.uses_count >= code.max_uses:
            raise InvitationCodeExhaustedError("Este link de invitación alcanzó el límite de usos.")
        return code

    def register_via_code(self, code, dto: RegisterViaCodeDTO):
        from ..infrastructure.models import UserProfile
        account_svc = AccountService()
        account_svc.register_user(RegisterUserDTO(
            username=dto.username,
            email=dto.email,
            password=dto.password,
        ))
        user = User.objects.get(username=dto.username)
        grupo_jugador, _ = Group.objects.get_or_create(name="Jugador")
        user.groups.add(grupo_jugador)
        UserProfile.objects.get_or_create(user=user)
        code.register_use()
        return user
