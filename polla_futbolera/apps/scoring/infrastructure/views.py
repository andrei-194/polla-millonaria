from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

from apps.quinielas.infrastructure.models import Quiniela, Inscripcion
from ..application.services import ScoringService


@login_required
def leaderboard_view(request, slug):
    quiniela = get_object_or_404(Quiniela, slug=slug)
    es_inscrito = Inscripcion.objects.filter(
        jugador=request.user, quiniela=quiniela, activa=True
    ).exists()
    service = ScoringService()
    limit = None if es_inscrito else 10
    leaderboard = service.get_leaderboard(quiniela.id, limit=limit)
    return render(request, "scoring/leaderboard.html", {
        "quiniela": quiniela,
        "leaderboard": leaderboard,
        "es_inscrito": es_inscrito,
    })
