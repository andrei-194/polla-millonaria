from django.core.paginator import Paginator
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404

from apps.quinielas.infrastructure.models import Quiniela, Inscripcion
from apps.quinielas.infrastructure.permissions import jugador_required
from apps.tournaments.infrastructure.models import Fecha
from ..application.services import RankingService
from .models import RankingAcumulado, RankingFecha


def leaderboard_acumulado_view(request, slug):
    quiniela = get_object_or_404(Quiniela, slug=slug)
    es_inscrito = False
    if request.user.is_authenticated:
        es_inscrito = Inscripcion.objects.filter(
            jugador=request.user, quiniela=quiniela, activa=True
        ).exists()

    qs = (
        RankingAcumulado.objects
        .filter(quiniela=quiniela)
        .select_related("usuario")
        .order_by("posicion")
    )

    ultimo_calculo = qs.aggregate(ts=Max("calculado_en"))["ts"]

    page_obj = None
    if es_inscrito:
        paginator = Paginator(qs, 25)
        page_obj = paginator.get_page(request.GET.get("page"))
        ranking = page_obj
    else:
        ranking = list(qs[:10])

    return render(request, "scoring/leaderboard_acumulado.html", {
        "quiniela": quiniela,
        "ranking": ranking,
        "page_obj": page_obj,
        "es_inscrito": es_inscrito,
        "ultimo_calculo": ultimo_calculo,
    })


def ranking_fecha_view(request, slug, numero):
    quiniela = get_object_or_404(Quiniela, slug=slug)
    fecha = get_object_or_404(Fecha, torneo=quiniela.tournament, numero=numero)

    es_inscrito = False
    if request.user.is_authenticated:
        es_inscrito = Inscripcion.objects.filter(
            jugador=request.user, quiniela=quiniela, activa=True
        ).exists()

    qs = (
        RankingFecha.objects
        .filter(quiniela=quiniela, fecha=fecha)
        .select_related("usuario")
        .order_by("posicion")
    )

    ultimo_calculo = qs.aggregate(ts=Max("calculado_en"))["ts"]

    page_obj = None
    if es_inscrito:
        paginator = Paginator(qs, 25)
        page_obj = paginator.get_page(request.GET.get("page"))
        ranking = page_obj
    else:
        ranking = list(qs[:10])

    return render(request, "scoring/ranking_fecha.html", {
        "quiniela": quiniela,
        "fecha": fecha,
        "ranking": ranking,
        "page_obj": page_obj,
        "es_inscrito": es_inscrito,
        "ultimo_calculo": ultimo_calculo,
    })


def ranking_acumulado_json(request, slug):
    quiniela = get_object_or_404(Quiniela, slug=slug)
    qs = RankingAcumulado.objects.filter(quiniela=quiniela).select_related("usuario")
    ultimo = qs.aggregate(ts=Max("calculado_en"))["ts"]
    return JsonResponse({
        "calculado_en": ultimo.isoformat() if ultimo else None,
        "count": qs.count(),
    })


def ranking_fecha_json(request, slug, numero):
    quiniela = get_object_or_404(Quiniela, slug=slug)
    fecha = get_object_or_404(Fecha, torneo=quiniela.tournament, numero=numero)
    qs = RankingFecha.objects.filter(quiniela=quiniela, fecha=fecha)
    ultimo = qs.aggregate(ts=Max("calculado_en"))["ts"]
    return JsonResponse({
        "calculado_en": ultimo.isoformat() if ultimo else None,
        "count": qs.count(),
    })


@jugador_required
def mi_historial_view(request, slug):
    quiniela = get_object_or_404(Quiniela, slug=slug)
    get_object_or_404(Inscripcion, jugador=request.user, quiniela=quiniela, activa=True)

    rankings_fecha = (
        RankingFecha.objects
        .filter(quiniela=quiniela, usuario=request.user)
        .select_related("fecha")
        .order_by("fecha__numero")
    )

    ranking_acumulado = RankingAcumulado.objects.filter(
        quiniela=quiniela, usuario=request.user
    ).first()

    return render(request, "scoring/mi_historial.html", {
        "quiniela": quiniela,
        "rankings_fecha": rankings_fecha,
        "ranking_acumulado": ranking_acumulado,
    })
