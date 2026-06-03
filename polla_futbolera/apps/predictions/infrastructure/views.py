from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from apps.quinielas.infrastructure.models import Quiniela, Inscripcion
from apps.quinielas.infrastructure.permissions import jugador_required
from apps.tournaments.infrastructure.models import Match, Fecha
from ..application.services import PredictionService
from ..application.dtos import CreatePredictionDTO, CrearPronosticoEventoDTO
from ..domain.exceptions import PredictionDeadlinePassedError, ValorInvalidoError, EventoCerradoError
from .forms import PredictionForm
from .models import Prediction, EventoPartido, PronosticoEvento


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


# --- V3 Views ---

@jugador_required
def fechas_list_view(request, slug):
    quiniela = get_object_or_404(Quiniela, slug=slug)
    get_object_or_404(Inscripcion, jugador=request.user, quiniela=quiniela, activa=True)

    fechas = Fecha.objects.filter(
        torneo=quiniela.tournament
    ).prefetch_related("partidos").order_by("numero")

    return render(request, "predictions/fechas_list.html", {
        "quiniela": quiniela,
        "fechas": fechas,
    })


@jugador_required
def fecha_detail_view(request, slug, numero):
    quiniela = get_object_or_404(Quiniela, slug=slug)
    get_object_or_404(Inscripcion, jugador=request.user, quiniela=quiniela, activa=True)
    fecha = get_object_or_404(Fecha, torneo=quiniela.tournament, numero=numero)

    partidos = fecha.partidos.select_related("home_team", "away_team").order_by("match_date")
    partidos_con_eventos = []
    for partido in partidos:
        eventos = list(
            EventoPartido.objects.filter(partido=partido, quiniela=quiniela)
            .select_related("tipo_evento")
        )
        ids_eventos = [e.id for e in eventos]
        pronos_map = {
            p.evento_partido_id: p.valor
            for p in PronosticoEvento.objects.filter(
                evento_partido_id__in=ids_eventos, usuario=request.user
            )
        }
        eventos_con_prono = [
            {"evento": e, "mi_pronostico": pronos_map.get(e.id)}
            for e in eventos
        ]
        partidos_con_eventos.append({"partido": partido, "eventos": eventos_con_prono})

    return render(request, "predictions/fecha_detail.html", {
        "quiniela": quiniela,
        "fecha": fecha,
        "partidos_con_eventos": partidos_con_eventos,
    })


@jugador_required
def pronosticar_evento_view(request, slug, evento_id):
    quiniela = get_object_or_404(Quiniela, slug=slug)
    get_object_or_404(Inscripcion, jugador=request.user, quiniela=quiniela, activa=True)
    evento = get_object_or_404(
        EventoPartido.objects.select_related("tipo_evento", "partido__home_team", "partido__away_team"),
        id=evento_id, quiniela=quiniela
    )

    pronostico_existente = PronosticoEvento.objects.filter(
        usuario=request.user, evento_partido=evento
    ).first()

    if request.method == "POST":
        if evento.tipo_evento.codigo == "SCORE":
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
            messages.success(request, "Pronóstico guardado")
            numero_fecha = evento.partido.fecha.numero if evento.partido.fecha else 1
            return redirect("quinielas:fecha_detail", slug=slug, numero=numero_fecha)
        except EventoCerradoError as e:
            messages.error(request, str(e))
        except ValorInvalidoError as e:
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
    get_object_or_404(Inscripcion, jugador=request.user, quiniela=quiniela, activa=True)

    pronosticos = (
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

    return render(request, "predictions/mis_pronosticos.html", {
        "quiniela": quiniela,
        "pronosticos": pronosticos,
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
