from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decouple import config

from ..application.services import GroupService
from ..application.dtos import CreateGroupDTO, JoinGroupDTO
from ..domain.exceptions import (
    InvalidInvitationCodeError,
    AlreadyMemberError,
    NotGroupAdminError,
    CannotRemoveAdminError,
)
from .models import Group, GroupMembership
from .forms import CreateGroupForm, JoinGroupForm


@login_required
def group_list(request):
    memberships = GroupMembership.objects.filter(user=request.user).select_related("group")
    groups = [m.group for m in memberships]
    return render(request, "groups/list.html", {"groups": groups})


@login_required
def group_create(request):
    if request.method == "POST":
        form = CreateGroupForm(request.POST)
        if form.is_valid():
            service = GroupService()
            group = service.create_group(CreateGroupDTO(
                name=form.cleaned_data["name"],
                description=form.cleaned_data["description"],
                created_by_id=request.user.id,
            ))
            messages.success(request, f"Grupo '{group.name}' creado exitosamente")
            return redirect("groups:detail", slug=group.slug)
    else:
        form = CreateGroupForm()
    return render(request, "groups/create.html", {"form": form})


@login_required
def group_detail(request, slug):
    group = get_object_or_404(Group, slug=slug)
    membership = GroupMembership.objects.filter(user=request.user, group=group).first()
    if not membership:
        messages.error(request, "No tienes acceso a este grupo")
        return redirect("groups:list")
    members = GroupMembership.objects.filter(group=group).select_related("user")
    from apps.tournaments.infrastructure.models import GroupTournament
    group_tournaments = GroupTournament.objects.filter(group=group).select_related("tournament")
    return render(request, "groups/detail.html", {
        "group": group,
        "membership": membership,
        "members": members,
        "group_tournaments": group_tournaments,
    })


@login_required
def group_join(request):
    if request.method == "POST":
        form = JoinGroupForm(request.POST)
        if form.is_valid():
            service = GroupService()
            try:
                service.join_group(JoinGroupDTO(
                    invitation_code=form.cleaned_data["invitation_code"],
                    user_id=request.user.id,
                ))
                messages.success(request, "Te uniste al grupo exitosamente")
                return redirect("groups:list")
            except (InvalidInvitationCodeError, AlreadyMemberError) as e:
                messages.error(request, str(e))
    else:
        invitation_code = request.GET.get("code", "")
        form = JoinGroupForm(initial={"invitation_code": invitation_code})
    return render(request, "groups/join.html", {"form": form})


@login_required
def group_invite(request, slug):
    group = get_object_or_404(Group, slug=slug)
    membership = GroupMembership.objects.filter(user=request.user, group=group, role="admin").first()
    if not membership:
        messages.error(request, "No tienes permisos para esta acción")
        return redirect("groups:detail", slug=slug)
    if request.method == "POST":
        service = GroupService()
        try:
            group = service.regenerate_invitation_code(group, request.user.id)
            messages.success(request, "Código de invitación regenerado")
        except NotGroupAdminError as e:
            messages.error(request, str(e))
    base_url = config("INVITATION_LINK_BASE_URL", default="http://localhost:8000")
    invite_link = f"{base_url}/groups/join/?code={group.invitation_code}"
    return render(request, "groups/invite.html", {"group": group, "invite_link": invite_link})


@login_required
def member_remove(request, slug, user_id):
    group = get_object_or_404(Group, slug=slug)
    if request.method == "POST":
        service = GroupService()
        try:
            service.remove_member(group, user_id, request.user.id)
            messages.success(request, "Miembro expulsado")
        except (NotGroupAdminError, CannotRemoveAdminError) as e:
            messages.error(request, str(e))
    return redirect("groups:detail", slug=slug)
