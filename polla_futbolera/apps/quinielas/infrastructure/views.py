from datetime import timedelta

from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone

from ..application.services import QuinielaService
from ..application.dtos import InscribirJugadorDTO
from ..domain.exceptions import JugadorYaInscritoError, JugadorNoInscritoError
from .models import Quiniela, Inscripcion
from .forms import InscribirJugadorForm
from .permissions import jugador_required, moderador_required
from apps.scoring.infrastructure.models import RankingAcumulado
from apps.tournaments.infrastructure.models import Fecha, Match

User = get_user_model()


def quiniela_list(request):
    quinielas_publicas = Quiniela.objects.filter(status="activa").select_related("tournament")
    total_jugadores = User.objects.filter(groups__name="Jugador").count()

    mis_quinielas = []
    proximos_partidos = []
    mis_total_pts = 0

    if request.user.is_authenticated:
        from apps.predictions.infrastructure.models import EventoPartido

        now = timezone.now()

        inscripciones = (
            Inscripcion.objects
            .filter(jugador=request.user, activa=True)
            .select_related("quiniela__tournament")
            .order_by("quiniela__name")
        )

        quiniela_ids = [i.quiniela_id for i in inscripciones]

        rankings_map = {
            r.quiniela_id: r
            for r in RankingAcumulado.objects.filter(
                quiniela_id__in=quiniela_ids, usuario=request.user
            )
        }

        mis_total_pts = sum(r.puntos_total for r in rankings_map.values())

        for insc in inscripciones:
            q = insc.quiniela
            ranking = rankings_map.get(q.id)

            eventos_pendientes = (
                EventoPartido.objects
                .filter(
                    quiniela=q,
                    estado='abierto',
                    plazo_cierre__gt=now,
                    partido__status__in=('scheduled', 'postponed'),
                )
                .exclude(pronosticos__usuario=request.user)
                .count()
            )

            proxima_fecha = (
                Fecha.objects
                .filter(
                    torneo=q.tournament,
                    partidos__eventos__quiniela=q,
                    partidos__eventos__estado='abierto',
                )
                .order_by('numero')
                .first()
            )

            mis_quinielas.append({
                "quiniela": q,
                "ranking": ranking,
                "eventos_pendientes": eventos_pendientes,
                "proxima_fecha_nombre": proxima_fecha.nombre if proxima_fecha else None,
            })

        if quiniela_ids:
            tournament_ids = list(set(i.quiniela.tournament_id for i in inscripciones))
            proximos_partidos = list(
                Match.objects
                .filter(
                    tournament_id__in=tournament_ids,
                    status='scheduled',
                    match_date__gte=now,
                    match_date__lte=now + timedelta(hours=48),
                )
                .select_related('home_team', 'away_team')
                .order_by('match_date')[:8]
            )

    _DIAS = ['lunes','martes','miércoles','jueves','viernes','sábado','domingo']
    _MESES = ['enero','febrero','marzo','abril','mayo','junio',
              'julio','agosto','septiembre','octubre','noviembre','diciembre']
    _now = timezone.localtime(timezone.now())
    today_str = f"{_DIAS[_now.weekday()]} {_now.day} de {_MESES[_now.month - 1]}"

    es_publico_sin_rol = (
        request.user.is_authenticated
        and not request.user.is_staff
        and not request.user.is_superuser
        and not request.user.groups.filter(name__in=["Jugador", "Moderador"]).exists()
    )

    return render(request, "quinielas/list.html", {
        "quinielas": quinielas_publicas,
        "total_jugadores": total_jugadores,
        "mis_quinielas": mis_quinielas,
        "proximos_partidos": proximos_partidos,
        "mis_total_pts": mis_total_pts,
        "today": today_str,
        "es_publico_sin_rol": es_publico_sin_rol,
    })


def quiniela_detail(request, slug):
    quiniela = get_object_or_404(Quiniela, slug=slug)
    es_inscrito = False
    if request.user.is_authenticated:
        es_inscrito = Inscripcion.objects.filter(
            jugador=request.user, quiniela=quiniela, activa=True
        ).exists()

    # Preview del leaderboard: top 10 público, top 25 para inscritos (la página completa tiene paginación)
    leaderboard = _build_leaderboard_v3(quiniela.id, limit=25 if es_inscrito else 10)
    fechas = Fecha.objects.filter(torneo=quiniela.tournament).order_by("numero")

    return render(request, "quinielas/detail.html", {
        "quiniela": quiniela,
        "es_inscrito": es_inscrito,
        "leaderboard": leaderboard,
        "fechas": fechas,
    })


def _build_leaderboard_v3(quiniela_id: int, limit: int | None = None):
    qs = (
        RankingAcumulado.objects
        .filter(quiniela_id=quiniela_id)
        .select_related("usuario")
        .order_by("posicion")
    )
    if limit:
        qs = qs[:limit]
    return [
        {
            "user__username": r.usuario.username,
            "total_points": r.puntos_total,
            "exactos": r.exactos_total,
            "ganadores": r.aciertos_total,
            "posicion": r.posicion,
        }
        for r in qs
    ]


# --- Vistas del Moderador ---

@moderador_required
def moderador_dashboard(request):
    quinielas = Quiniela.objects.select_related("tournament")
    jugadores = User.objects.filter(groups__name="Jugador").order_by("username")
    return render(request, "moderador/dashboard.html", {
        "quinielas": quinielas,
        "jugadores": jugadores,
    })


@moderador_required
def moderador_jugadores(request):
    q = request.GET.get("q", "").strip()

    users_con_rol = User.objects.filter(
        groups__name__in=["Jugador", "Moderador"]
    ).values_list("id", flat=True).distinct()

    publicos_qs = (
        User.objects
        .exclude(id__in=users_con_rol)
        .filter(is_staff=False, is_superuser=False)
        .order_by("username")
    )
    jugadores_qs = User.objects.filter(groups__name="Jugador").order_by("username")

    if q:
        publicos_qs = publicos_qs.filter(username__icontains=q)
        jugadores_qs = jugadores_qs.filter(username__icontains=q)

    pag_publicos = Paginator(publicos_qs, 20)
    pag_jugadores = Paginator(jugadores_qs, 20)

    page_publicos = pag_publicos.get_page(request.GET.get("page_p"))
    page_jugadores = pag_jugadores.get_page(request.GET.get("page_j"))

    return render(request, "moderador/jugadores.html", {
        "publicos": page_publicos,
        "jugadores": page_jugadores,
        "page_publicos": page_publicos,
        "page_jugadores": page_jugadores,
        "q": q,
    })


@moderador_required
def moderador_promover(request, user_id):
    if request.method != "POST":
        return redirect("quinielas:moderador_jugadores")
    from django.contrib.auth.models import Group
    usuario = get_object_or_404(User, id=user_id, is_staff=False, is_superuser=False)
    grupo_jugador = Group.objects.get(name="Jugador")
    usuario.groups.add(grupo_jugador)
    messages.success(request, f"{usuario.username} promovido a Jugador")
    return redirect("quinielas:moderador_jugadores")


@moderador_required
def moderador_activar(request, user_id):
    if request.method != "POST":
        return redirect("quinielas:moderador_jugadores")
    usuario = get_object_or_404(User, id=user_id, is_staff=False, is_superuser=False)
    usuario.is_active = True
    usuario.save(update_fields=["is_active"])
    messages.success(request, f"Cuenta de {usuario.username} activada")
    return redirect("quinielas:moderador_jugadores")


@moderador_required
def moderador_desactivar(request, user_id):
    if request.method != "POST":
        return redirect("quinielas:moderador_jugadores")
    usuario = get_object_or_404(User, id=user_id, is_staff=False, is_superuser=False)
    usuario.is_active = False
    usuario.save(update_fields=["is_active"])
    messages.success(request, f"Cuenta de {usuario.username} desactivada")
    return redirect("quinielas:moderador_jugadores")


@moderador_required
def moderador_quitar_jugador(request, user_id):
    if request.method != "POST":
        return redirect("quinielas:moderador_jugadores")
    from django.contrib.auth.models import Group
    usuario = get_object_or_404(User, id=user_id, is_staff=False, is_superuser=False)
    grupo_jugador = Group.objects.get(name="Jugador")
    usuario.groups.remove(grupo_jugador)
    Inscripcion.objects.filter(jugador=usuario, activa=True).update(activa=False)
    messages.success(request, f"{usuario.username} ya no es Jugador y fue dado de baja de sus retos activos")
    return redirect("quinielas:moderador_jugadores")


@moderador_required
def moderador_inscripciones(request, slug):
    quiniela = get_object_or_404(Quiniela, slug=slug)

    inscripciones_qs = (
        Inscripcion.objects
        .filter(quiniela=quiniela)
        .select_related("jugador")
        .order_by("jugador__username")
    )
    total_inscritos = inscripciones_qs.count()

    paginator = Paginator(inscripciones_qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    form = InscribirJugadorForm(quiniela=quiniela)

    users_con_rol = User.objects.filter(
        groups__name__in=["Jugador", "Moderador"]
    ).values_list("id", flat=True).distinct()
    publicos_pendientes = User.objects.exclude(
        id__in=users_con_rol
    ).filter(is_active=True, is_staff=False, is_superuser=False).count()

    return render(request, "moderador/inscripciones.html", {
        "quiniela": quiniela,
        "inscripciones": page_obj,
        "page_obj": page_obj,
        "total_inscritos": total_inscritos,
        "form": form,
        "publicos_pendientes": publicos_pendientes,
        "jugadores_disponibles": form.fields["jugador"].queryset.count(),
    })


@moderador_required
def moderador_inscribir(request, slug):
    if request.method != "POST":
        return redirect("quinielas:moderador_inscripciones", slug=slug)
    quiniela = get_object_or_404(Quiniela, slug=slug)
    form = InscribirJugadorForm(request.POST, quiniela=quiniela)
    if form.is_valid():
        service = QuinielaService()
        try:
            service.inscribir_jugador(InscribirJugadorDTO(
                jugador_id=form.cleaned_data["jugador"].id,
                quiniela_id=quiniela.id,
                moderador_id=request.user.id,
            ))
            messages.success(request, f"{form.cleaned_data['jugador'].username} unido a {quiniela.name}")
        except JugadorYaInscritoError as e:
            messages.error(request, str(e))
    return redirect("quinielas:moderador_inscripciones", slug=slug)


@moderador_required
def moderador_dar_baja(request, slug, inscripcion_id):
    if request.method != "POST":
        return redirect("quinielas:moderador_inscripciones", slug=slug)
    service = QuinielaService()
    try:
        service.dar_de_baja(inscripcion_id)
        messages.success(request, "Jugador dado de baja del reto")
    except JugadorNoInscritoError as e:
        messages.error(request, str(e))
    return redirect("quinielas:moderador_inscripciones", slug=slug)
