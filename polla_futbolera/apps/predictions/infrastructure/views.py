from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from apps.groups.infrastructure.models import Group, GroupMembership
from apps.tournaments.infrastructure.models import Match, GroupTournament
from ..application.services import PredictionService
from ..application.dtos import CreatePredictionDTO
from ..domain.exceptions import PredictionDeadlinePassedError
from .forms import PredictionForm
from .models import Prediction


@login_required
def predict_view(request, slug, tournament_id, match_id):
    group = get_object_or_404(Group, slug=slug)
    membership = get_object_or_404(GroupMembership, user=request.user, group=group)
    match = get_object_or_404(Match, id=match_id)
    gt = get_object_or_404(GroupTournament, group=group, tournament_id=tournament_id)

    existing = Prediction.objects.filter(
        user=request.user, match=match, group=group
    ).first()

    if request.method == "POST":
        form = PredictionForm(request.POST, instance=existing)
        if form.is_valid():
            service = PredictionService()
            try:
                service.create_or_update_prediction(CreatePredictionDTO(
                    user_id=request.user.id,
                    match_id=match.id,
                    group_id=group.id,
                    home_goals=form.cleaned_data["home_goals"],
                    away_goals=form.cleaned_data["away_goals"],
                ))
                messages.success(request, "Pronóstico guardado")
                return redirect(
                    "tournaments:detail", slug=slug, tournament_id=tournament_id
                )
            except PredictionDeadlinePassedError as e:
                messages.error(request, str(e))
    else:
        form = PredictionForm(instance=existing)

    return render(request, "predictions/predict.html", {
        "form": form,
        "match": match,
        "group": group,
        "tournament_id": tournament_id,
    })


@login_required
def group_predictions_view(request, slug, tournament_id):
    group = get_object_or_404(Group, slug=slug)
    get_object_or_404(GroupMembership, user=request.user, group=group)
    gt = get_object_or_404(GroupTournament, group=group, tournament_id=tournament_id)
    matches = Match.objects.filter(tournament=gt.tournament).prefetch_related(
        "predictions__user"
    ).order_by("match_date")
    return render(request, "predictions/group_predictions.html", {
        "group": group,
        "tournament": gt.tournament,
        "matches": matches,
    })
