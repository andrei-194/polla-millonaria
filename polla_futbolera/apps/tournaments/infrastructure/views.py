from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings

from ..application.services import TournamentService
from .models import Tournament, Match


@login_required
def tournament_list(request):
    tournaments = Tournament.objects.filter(status="active")
    return render(request, "tournaments/list.html", {"tournaments": tournaments})


@login_required
def tournament_matches(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    matches = Match.objects.filter(tournament=tournament).select_related(
        "home_team", "away_team"
    )
    return render(request, "tournaments/matches.html", {
        "tournament": tournament,
        "matches": matches,
    })


@login_required
def sync_tournament(request, tournament_id):
    from ..infrastructure.adapters import StubFootballAPIAdapter, FootballDataOrgAdapter
    if request.method == "POST" and (request.user.is_staff or request.user.is_superuser):
        tournament = get_object_or_404(Tournament, id=tournament_id)
        adapter = FootballDataOrgAdapter() if settings.FOOTBALL_API_KEY else StubFootballAPIAdapter()
        service = TournamentService(football_api=adapter)
        count = service.sync_fixtures(tournament)
        from django.contrib import messages
        messages.success(request, f"Sincronización completada: {count} partidos nuevos")
    return tournament_matches(request, tournament_id)
