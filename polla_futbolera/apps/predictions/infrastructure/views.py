from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from apps.quinielas.infrastructure.models import Quiniela, Inscripcion
from apps.quinielas.infrastructure.permissions import jugador_required
from apps.tournaments.infrastructure.models import Match
from ..application.services import PredictionService
from ..application.dtos import CreatePredictionDTO
from ..domain.exceptions import PredictionDeadlinePassedError
from .forms import PredictionForm
from .models import Prediction


@jugador_required
def predict_view(request, slug, match_id):
    quiniela = get_object_or_404(Quiniela, slug=slug)
    get_object_or_404(Inscripcion, jugador=request.user, quiniela=quiniela, activa=True)
    match = get_object_or_404(Match, id=match_id, tournament=quiniela.tournament)

    existing = Prediction.objects.filter(
        user=request.user, match=match, quiniela=quiniela
    ).first()

    if request.method == "POST":
        form = PredictionForm(request.POST, instance=existing)
        if form.is_valid():
            service = PredictionService()
            try:
                service.create_or_update_prediction(CreatePredictionDTO(
                    user_id=request.user.id,
                    match_id=match.id,
                    quiniela_id=quiniela.id,
                    home_goals=form.cleaned_data["home_goals"],
                    away_goals=form.cleaned_data["away_goals"],
                ))
                messages.success(request, "Pronóstico guardado")
                return redirect("quinielas:detail", slug=slug)
            except PredictionDeadlinePassedError as e:
                messages.error(request, str(e))
    else:
        form = PredictionForm(instance=existing)

    return render(request, "predictions/predict.html", {
        "form": form,
        "match": match,
        "quiniela": quiniela,
    })


@jugador_required
def quiniela_predictions_view(request, slug, match_id):
    quiniela = get_object_or_404(Quiniela, slug=slug)
    get_object_or_404(Inscripcion, jugador=request.user, quiniela=quiniela, activa=True)
    match = get_object_or_404(Match, id=match_id, tournament=quiniela.tournament)

    service = PredictionService()
    predictions = service.get_quiniela_predictions(match.id, quiniela.id, request.user.id)

    return render(request, "predictions/quiniela_predictions.html", {
        "quiniela": quiniela,
        "match": match,
        "predictions": predictions,
    })
