from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings

from apps.groups.infrastructure.models import Group, GroupMembership
from ..application.services import TournamentService
from ..application.dtos import ActivateTournamentDTO
from .models import Tournament, GroupTournament, Match


@login_required
def tournament_list(request):
    tournaments = Tournament.objects.filter(status="active")
    return render(request, "tournaments/list.html", {"tournaments": tournaments})


@login_required
def activate_tournament(request, slug):
    group = get_object_or_404(Group, slug=slug)
    membership = GroupMembership.objects.filter(
        user=request.user, group=group, role="admin"
    ).first()
    if not membership:
        messages.error(request, "Solo el administrador puede activar torneos")
        return redirect("groups:detail", slug=slug)

    if request.method == "POST":
        tournament_id = request.POST.get("tournament_id")
        service = TournamentService()
        try:
            service.activate_tournament(ActivateTournamentDTO(
                group_id=group.id,
                tournament_id=int(tournament_id),
                activated_by_id=request.user.id,
            ))
            messages.success(request, "Torneo activado en el grupo")
        except Exception as e:
            messages.error(request, str(e))
        return redirect("groups:detail", slug=slug)

    tournaments = Tournament.objects.filter(status="active")
    return render(request, "tournaments/activate.html", {"group": group, "tournaments": tournaments})


@login_required
def tournament_detail(request, slug, tournament_id):
    group = get_object_or_404(Group, slug=slug)
    membership = get_object_or_404(GroupMembership, user=request.user, group=group)
    gt = get_object_or_404(GroupTournament, group=group, tournament_id=tournament_id)
    matches = Match.objects.filter(tournament=gt.tournament).select_related(
        "home_team", "away_team"
    )
    return render(request, "tournaments/detail.html", {
        "group": group,
        "tournament": gt.tournament,
        "matches": matches,
        "membership": membership,
    })


@login_required
def sync_tournament(request, slug, tournament_id):
    group = get_object_or_404(Group, slug=slug)
    membership = GroupMembership.objects.filter(
        user=request.user, group=group, role="admin"
    ).first()
    if not membership:
        messages.error(request, "Solo el administrador puede sincronizar")
        return redirect("tournaments:detail", slug=slug, tournament_id=tournament_id)

    if request.method == "POST":
        gt = get_object_or_404(GroupTournament, group=group, tournament_id=tournament_id)
        from ..infrastructure.adapters import StubFootballAPIAdapter, FootballDataOrgAdapter
        adapter = FootballDataOrgAdapter() if settings.FOOTBALL_API_KEY else StubFootballAPIAdapter()
        service = TournamentService(football_api=adapter)
        count = service.sync_fixtures(gt.tournament)
        messages.success(request, f"Sincronización completada: {count} partidos nuevos")

    return redirect("tournaments:detail", slug=slug, tournament_id=tournament_id)
