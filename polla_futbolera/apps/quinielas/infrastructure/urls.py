from django.urls import path
from . import views

app_name = "quinielas"

urlpatterns = [
    # Lista pública
    path("", views.quiniela_list, name="list"),

    # Panel del moderador — ANTES de <slug:slug>/ para evitar conflicto
    path("moderador/", views.moderador_dashboard, name="moderador_dashboard"),
    path("moderador/jugadores/", views.moderador_jugadores, name="moderador_jugadores"),
    path("moderador/jugadores/<int:user_id>/promover/", views.moderador_promover, name="moderador_promover"),
    path("moderador/jugadores/<int:user_id>/activar/", views.moderador_activar, name="moderador_activar"),
    path("moderador/jugadores/<int:user_id>/desactivar/", views.moderador_desactivar, name="moderador_desactivar"),
    path("moderador/jugadores/<int:user_id>/quitar-jugador/", views.moderador_quitar_jugador, name="moderador_quitar_jugador"),
    path("moderador/quinielas/<slug:slug>/inscripciones/", views.moderador_inscripciones, name="moderador_inscripciones"),
    path("moderador/quinielas/<slug:slug>/inscripciones/agregar/", views.moderador_inscribir, name="moderador_inscribir"),
    path("moderador/quinielas/<slug:slug>/inscripciones/<int:inscripcion_id>/baja/", views.moderador_dar_baja, name="moderador_dar_baja"),

    # Vistas por quiniela — DESPUÉS de las rutas fijas
    path("<slug:slug>/", views.quiniela_detail, name="detail"),
    path("<slug:slug>/leaderboard/", views.quiniela_leaderboard, name="leaderboard"),
]
