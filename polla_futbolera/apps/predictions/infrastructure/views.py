from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from apps.quinielas.infrastructure.models import Quiniela, Inscripcion
from apps.quinielas.infrastructure.permissions import jugador_required
from apps.tournaments.infrastructure.models import Match, Fecha
from apps.scoring.infrastructure.models import PuntuacionEvento
from ..application.services import PredictionService
from ..application.dtos import CrearPronosticoEventoDTO
from ..domain.exceptions import ValorInvalidoError, EventoCerradoError
from .models import EventoPartido, PronosticoEvento


def _tiene_eventos_abiertos(eventos: list) -> bool:
    return any(ev_item["evento"].esta_abierto() for ev_item in eventos)


def _build_valor_display(valor: str, evento) -> str:
    """Etiqueta legible del valor para actualizar el DOM tras un pronóstico AJAX."""
    codigo = evento.tipo_evento.codigo
    if codigo == "WINNER":
        if valor == "H":
            return evento.partido.home_team.name
        if valor == "D":
            return "Empate"
        if valor == "A":
            return evento.partido.away_team.name
    return valor


def _check_inscripcion(request, quiniela):
    """Superadmin pasa libre; jugadores deben tener inscripción activa."""
    if request.user.is_superuser:
        return
    get_object_or_404(Inscripcion, jugador=request.user, quiniela=quiniela, activa=True)


@jugador_required
def fechas_list_view(request, slug):
    quiniela = get_object_or_404(Quiniela, slug=slug)
    _check_inscripcion(request, quiniela)

    fechas = (
        Fecha.objects
        .filter(torneo=quiniela.tournament)
        .annotate(num_partidos=Count("partidos"))
        .order_by("numero")
    )

    return render(request, "predictions/fechas_list.html", {
        "quiniela": quiniela,
        "fechas": fechas,
    })


@jugador_required
def fecha_detail_view(request, slug, numero):
    quiniela = get_object_or_404(Quiniela, slug=slug)
    _check_inscripcion(request, quiniela)
    fecha = get_object_or_404(Fecha, torneo=quiniela.tournament, numero=numero)

    # Query 1: partidos de la fecha
    partidos = list(
        fecha.partidos
        .select_related("home_team", "away_team")
        .order_by("match_date")
    )
    partido_ids = [p.id for p in partidos]

    # Query 2: todos los eventos del bloque de partidos × quiniela
    eventos_by_partido: dict[int, list] = {}
    for evento in (
        EventoPartido.objects
        .filter(partido_id__in=partido_ids, quiniela=quiniela)
        .select_related("tipo_evento")
        .order_by("tipo_evento__codigo")
    ):
        eventos_by_partido.setdefault(evento.partido_id, []).append(evento)

    # Query 3: pronósticos del usuario para esos eventos
    evento_ids = [e.id for evs in eventos_by_partido.values() for e in evs]
    pronos_map = {
        p.evento_partido_id: p.valor
        for p in PronosticoEvento.objects.filter(
            evento_partido_id__in=evento_ids, usuario=request.user
        )
    }

    # Query 4: puntuaciones del usuario para feedback de exacto/acierto/fallo
    puntuaciones_map = {
        p.evento_partido_id: p
        for p in PuntuacionEvento.objects.filter(
            evento_partido_id__in=evento_ids,
            usuario=request.user,
            quiniela=quiniela,
        )
    }

    partidos_con_eventos = [
        {
            "partido": partido,
            "eventos": [
                {
                    "evento": e,
                    "mi_pronostico": pronos_map.get(e.id),
                    "mi_puntuacion": puntuaciones_map.get(e.id),
                }
                for e in eventos_by_partido.get(partido.id, [])
            ],
        }
        for partido in partidos
    ]

    partidos_abiertos = [p for p in partidos_con_eventos if _tiene_eventos_abiertos(p["eventos"])]
    partidos_cerrados = [p for p in partidos_con_eventos if not _tiene_eventos_abiertos(p["eventos"])]

    return render(request, "predictions/fecha_detail.html", {
        "quiniela": quiniela,
        "fecha": fecha,
        "partidos_con_eventos": partidos_con_eventos,
        "partidos_abiertos": partidos_abiertos,
        "partidos_cerrados": partidos_cerrados,
    })


@jugador_required
def pronosticar_evento_view(request, slug, evento_id):
    quiniela = get_object_or_404(Quiniela, slug=slug)
    _check_inscripcion(request, quiniela)
    evento = get_object_or_404(
        EventoPartido.objects.select_related("tipo_evento", "partido__home_team", "partido__away_team"),
        id=evento_id, quiniela=quiniela
    )

    pronostico_existente = PronosticoEvento.objects.filter(
        usuario=request.user, evento_partido=evento
    ).first()

    if request.method == "POST":
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        if is_ajax:
            # AJAX: el JS siempre envía el campo "valor" ya construido (incluido "home-away" para SCORE)
            valor = request.POST.get("valor", "").strip()[:50]
            if not valor:
                return JsonResponse(
                    {"ok": False, "error": "invalido", "mensaje": "Valor vacío."},
                    status=422,
                )
        elif evento.tipo_evento.codigo == "SCORE":
            home = request.POST.get("home", "").strip()
            away = request.POST.get("away", "").strip()
            valor = f"{home}-{away}"
        else:
            valor = request.POST.get("valor", "").strip()

        service = PredictionService()
        try:
            service.crear_pronostico_evento(CrearPronosticoEventoDTO(
                usuario_id=request.user.id,
                evento_partido_id=evento.id,
                valor=valor,
            ))
            if is_ajax:
                return JsonResponse({
                    "ok": True,
                    "valor": valor,
                    "valor_display": _build_valor_display(valor, evento),
                })
            messages.success(request, "Jugada guardada")
            numero_fecha = evento.partido.fecha.numero if evento.partido.fecha else 1
            return redirect("quinielas:fecha_detail", slug=slug, numero=numero_fecha)
        except EventoCerradoError as e:
            if is_ajax:
                return JsonResponse(
                    {"ok": False, "error": "cerrado", "mensaje": str(e)},
                    status=409,
                )
            messages.error(request, str(e))
        except ValorInvalidoError as e:
            if is_ajax:
                return JsonResponse(
                    {"ok": False, "error": "invalido", "mensaje": str(e)},
                    status=422,
                )
            messages.error(request, str(e))

    score_home = score_away = ""
    if pronostico_existente and evento.tipo_evento.codigo == "SCORE":
        partes = pronostico_existente.valor.split("-")
        if len(partes) == 2:
            score_home, score_away = partes

    return render(request, "predictions/pronosticar_evento.html", {
        "quiniela": quiniela,
        "evento": evento,
        "pronostico_existente": pronostico_existente,
        "score_home": score_home,
        "score_away": score_away,
    })


@jugador_required
def mis_pronosticos_view(request, slug):
    quiniela = get_object_or_404(Quiniela, slug=slug)
    _check_inscripcion(request, quiniela)

    qs = (
        PronosticoEvento.objects
        .filter(usuario=request.user, evento_partido__quiniela=quiniela)
        .select_related(
            "evento_partido__tipo_evento",
            "evento_partido__partido__home_team",
            "evento_partido__partido__away_team",
            "evento_partido__partido__fecha",
        )
        .order_by("evento_partido__partido__match_date")
    )

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "predictions/mis_pronosticos.html", {
        "quiniela": quiniela,
        "pronosticos": page_obj,
        "page_obj": page_obj,
    })


@jugador_required
def resultados_partido_view(request, slug, match_id):
    quiniela = get_object_or_404(Quiniela, slug=slug)
    inscripcion = Inscripcion.objects.filter(
        jugador=request.user, quiniela=quiniela, activa=True
    ).first()
    match = get_object_or_404(Match, id=match_id, tournament=quiniela.tournament)

    eventos = EventoPartido.objects.filter(
        partido=match, quiniela=quiniela
    ).select_related("tipo_evento").prefetch_related(
        "pronosticos__usuario",
        "puntuaciones__usuario",
    )

    return render(request, "predictions/resultados_partido.html", {
        "quiniela": quiniela,
        "match": match,
        "eventos": eventos,
        "es_inscrito": inscripcion is not None,
    })
