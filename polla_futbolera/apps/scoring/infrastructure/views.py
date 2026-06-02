from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

from apps.groups.infrastructure.models import Group, GroupMembership
from apps.tournaments.infrastructure.models import GroupTournament
from ..application.services import ScoringService


@login_required
def leaderboard_view(request, slug, tournament_id):
    group = get_object_or_404(Group, slug=slug)
    get_object_or_404(GroupMembership, user=request.user, group=group)
    gt = get_object_or_404(GroupTournament, group=group, tournament_id=tournament_id)
    service = ScoringService()
    leaderboard = service.get_leaderboard(group.id, tournament_id)
    return render(request, "scoring/leaderboard.html", {
        "group": group,
        "tournament": gt.tournament,
        "leaderboard": leaderboard,
    })
