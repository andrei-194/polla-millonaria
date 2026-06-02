from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db.models import Sum, Count, Q

from ..application.services import QuinielaService
from ..application.dtos import InscribirJugadorDTO
from ..domain.exceptions import JugadorYaInscritoError, JugadorNoInscritoError
from .models import Quiniela, Inscripcion
from .forms import InscribirJugadorForm
from .permissions import jugador_required, moderador_required
from apps.scoring.infrastructure.models import Score

User = get_user_model()


def quiniela_list(request):
    quinielas = Quiniela.objects.filter(status="activa").select_related("tournament")
    total_jugadores = User.objects.filter(groups__name="Jugador").count()
    return render(request, "quinielas/list.html", {
        "quinielas": quinielas,
        "total_jugadores": total_jugadores,
    })


def quiniela_detail(request, slug):
    quiniela = get_object_or_404(Quiniela, slug=slug)
    es_inscrito = False
    if request.user.is_authenticated:
        es_inscrito = Inscripcion.objects.filter(
            jugador=request.user, quiniela=quiniela, activa=True
        ).exists()

    leaderboard = _build_leaderboard(quiniela.id, limit=None if es_inscrito else 10)
    matches = quiniela.tournament.matches.order_by("match_date")

    return render(request, "quinielas/detail.html", {
        "quiniela": quiniela,
        "es_inscrito": es_inscrito,
        "leaderboard": leaderboard,
        "matches": matches,
    })


@jugador_required
def quiniela_leaderboard(request, slug):
    quiniela = get_object_or_404(Quiniela, slug=slug)
    inscripcion = Inscripcion.objects.filter(
        jugador=request.user, quiniela=quiniela, activa=True
    ).first()
    if not inscripcion:
        messages.error(request, "No estás inscrito en esta quiniela")
        return redirect("quinielas:detail", slug=slug)

    leaderboard = _build_leaderboard(quiniela.id)
    return render(request, "quinielas/leaderboard.html", {
        "quiniela": quiniela,
        "leaderboard": leaderboard,
    })


def _build_leaderboard(quiniela_id: int, limit: int | None = None):
    qs = (
        Score.objects.filter(quiniela_id=quiniela_id)
        .values("user_id", "user__username")
        .annotate(
            total_points=Sum("points"),
            exactos=Count("id", filter=Q(hit_type="exact")),
            ganadores=Count("id", filter=Q(hit_type="winner")),
            fallos=Count("id", filter=Q(hit_type="miss")),
        )
        .order_by("-total_points")
    )
    if limit:
        qs = qs[:limit]
    return list(qs)


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
    users_con_rol = User.objects.filter(
        groups__name__in=["Jugador", "Moderador"]
    ).values_list("id", flat=True).distinct()
    publicos = User.objects.exclude(
        id__in=users_con_rol
    ).filter(is_staff=False, is_superuser=False).order_by("username")
    jugadores = User.objects.filter(groups__name="Jugador").order_by("username")
    return render(request, "moderador/jugadores.html", {
        "publicos": publicos,
        "jugadores": jugadores,
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
    messages.success(request, f"{usuario.username} ya no es Jugador y fue dado de baja de sus quinielas activas")
    return redirect("quinielas:moderador_jugadores")


@moderador_required
def moderador_inscripciones(request, slug):
    quiniela = get_object_or_404(Quiniela, slug=slug)
    inscripciones = (
        Inscripcion.objects.filter(quiniela=quiniela)
        .select_related("jugador")
        .order_by("jugador__username")
    )
    form = InscribirJugadorForm(quiniela=quiniela)

    users_con_rol = User.objects.filter(
        groups__name__in=["Jugador", "Moderador"]
    ).values_list("id", flat=True).distinct()
    publicos_pendientes = User.objects.exclude(
        id__in=users_con_rol
    ).filter(is_active=True, is_staff=False, is_superuser=False).count()

    return render(request, "moderador/inscripciones.html", {
        "quiniela": quiniela,
        "inscripciones": inscripciones,
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
            messages.success(request, f"{form.cleaned_data['jugador'].username} inscrito en {quiniela.name}")
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
        messages.success(request, "Jugador dado de baja de la quiniela")
    except JugadorNoInscritoError as e:
        messages.error(request, str(e))
    return redirect("quinielas:moderador_inscripciones", slug=slug)
