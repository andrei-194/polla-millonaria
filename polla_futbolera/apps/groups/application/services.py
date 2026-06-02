import secrets
from django.utils.text import slugify

from .dtos import CreateGroupDTO, JoinGroupDTO
from ..domain.exceptions import (
    GroupNotFoundError,
    InvalidInvitationCodeError,
    AlreadyMemberError,
    NotGroupAdminError,
    CannotRemoveAdminError,
)
from ..infrastructure.models import Group, GroupMembership


class GroupService:
    def create_group(self, dto: CreateGroupDTO) -> Group:
        base_slug = slugify(dto.name)
        slug = base_slug
        counter = 1
        while Group.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        group = Group.objects.create(
            name=dto.name,
            description=dto.description,
            slug=slug,
            created_by_id=dto.created_by_id,
            invitation_code=secrets.token_urlsafe(8),
        )
        GroupMembership.objects.create(
            user_id=dto.created_by_id,
            group=group,
            role="admin",
        )
        return group

    def join_group(self, dto: JoinGroupDTO) -> GroupMembership:
        try:
            group = Group.objects.get(invitation_code=dto.invitation_code)
        except Group.DoesNotExist:
            raise InvalidInvitationCodeError("Código de invitación inválido")

        if GroupMembership.objects.filter(user_id=dto.user_id, group=group).exists():
            raise AlreadyMemberError("Ya eres miembro de este grupo")

        return GroupMembership.objects.create(
            user_id=dto.user_id,
            group=group,
            role="member",
        )

    def regenerate_invitation_code(self, group: Group, requesting_user_id: int) -> Group:
        membership = GroupMembership.objects.filter(
            user_id=requesting_user_id, group=group, role="admin"
        ).first()
        if not membership:
            raise NotGroupAdminError("Solo el administrador puede regenerar el código")
        group.invitation_code = secrets.token_urlsafe(8)
        group.save(update_fields=["invitation_code"])
        return group

    def remove_member(self, group: Group, member_id: int, requesting_user_id: int) -> None:
        admin_membership = GroupMembership.objects.filter(
            user_id=requesting_user_id, group=group, role="admin"
        ).first()
        if not admin_membership:
            raise NotGroupAdminError("Solo el administrador puede expulsar miembros")
        target = GroupMembership.objects.filter(user_id=member_id, group=group).first()
        if not target:
            raise GroupNotFoundError("El usuario no es miembro de este grupo")
        if target.role == "admin":
            raise CannotRemoveAdminError("No puedes expulsar al administrador")
        target.delete()
