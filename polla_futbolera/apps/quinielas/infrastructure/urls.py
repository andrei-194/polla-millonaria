from django.urls import path

from . import views
from apps.predictions.infrastructure import views as pred_views
from apps.scoring.infrastructure import views as scoring_views

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

    # Rankings
    path("<slug:slug>/leaderboard/", scoring_views.leaderboard_acumulado_view, name="leaderboard"),
    path("<slug:slug>/fechas/<int:numero>/ranking/", scoring_views.ranking_fecha_view, name="ranking_fecha"),
    path("<slug:slug>/mi-historial/", scoring_views.mi_historial_view, name="mi_historial"),

    # Fechas y eventos (predicciones v3)
    path("<slug:slug>/fechas/", pred_views.fechas_list_view, name="fechas_list"),
    path("<slug:slug>/fechas/<int:numero>/", pred_views.fecha_detail_view, name="fecha_detail"),
    path("<slug:slug>/eventos/<int:evento_id>/pronosticar/", pred_views.pronosticar_evento_view, name="pronosticar_evento"),
    path("<slug:slug>/mis-pronosticos/", pred_views.mis_pronosticos_view, name="mis_pronosticos"),
    path("<slug:slug>/partidos/<int:match_id>/resultados/", pred_views.resultados_partido_view, name="resultados_partido"),
]
