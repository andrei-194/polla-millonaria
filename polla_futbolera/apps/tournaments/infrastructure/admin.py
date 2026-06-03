from django.contrib import admin, messages
from .models import Tournament, Team, Match, Fecha


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("name", "season", "status", "external_code")
    list_filter = ("status",)
    search_fields = ("name", "external_code")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "external_code")
    search_fields = ("name", "external_code")


@admin.register(Fecha)
class FechaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "torneo", "numero", "fecha_inicio", "fecha_fin")
    list_filter = ("torneo",)
    search_fields = ("nombre",)
    actions = ["calcular_puntos_y_ranking"]

    @admin.action(description="▶ Calcular puntos y recalcular rankings de las fechas seleccionadas")
    def calcular_puntos_y_ranking(self, request, queryset):
        """
        Pipeline completo para una fecha tras registrar los resultados:
          1. Calcula puntos por cada EventoPartido con resultado (todas las quinielas).
          2. Recalcula RankingFecha por cada quiniela × fecha procesada.
          3. Recalcula RankingAcumulado por cada quiniela afectada.

        Usar después de haber registrado el `resultado` en cada EventoPartido.
        """
        from apps.predictions.infrastructure.models import EventoPartido
        from apps.scoring.application.services import RankingService, ScoringService
        from apps.scoring.domain.exceptions import EventoSinResultadoError

        scoring_svc = ScoringService()
        ranking_svc = RankingService()

        eventos_ok = 0
        eventos_sin_resultado = 0
        fechas_quinielas = set()   # (quiniela_id, fecha_id)
        quinielas = set()

        for fecha in queryset:
            eventos = (
                EventoPartido.objects
                .filter(partido__fecha=fecha)
                .select_related("quiniela")
            )
            for evento in eventos:
                if not evento.resultado:
                    eventos_sin_resultado += 1
                    continue
                try:
                    scoring_svc.calcular_puntos_evento(evento.id)
                    eventos_ok += 1
                    fechas_quinielas.add((evento.quiniela_id, fecha.id))
                    quinielas.add(evento.quiniela_id)
                except EventoSinResultadoError:
                    eventos_sin_resultado += 1

        for quiniela_id, fecha_id in fechas_quinielas:
            ranking_svc.recalcular_ranking_fecha(quiniela_id, fecha_id)

        for quiniela_id in quinielas:
            ranking_svc.recalcular_ranking_acumulado(quiniela_id)

        if eventos_ok:
            self.message_user(
                request,
                (
                    f"✓ {eventos_ok} evento(s) calculados. "
                    f"Rankings actualizados: {len(fechas_quinielas)} fecha(s), "
                    f"{len(quinielas)} quiniela(s)."
                ),
                messages.SUCCESS,
            )
        if eventos_sin_resultado:
            self.message_user(
                request,
                f"⚠ {eventos_sin_resultado} evento(s) omitidos por no tener resultado registrado.",
                messages.WARNING,
            )
        if not eventos_ok and not eventos_sin_resultado:
            self.message_user(
                request,
                "No se encontraron EventoPartido para las fechas seleccionadas.",
                messages.WARNING,
            )


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("__str__", "tournament", "fecha", "phase", "status", "match_date")
    list_filter = ("status", "tournament", "fecha")
    search_fields = ("home_team__name", "away_team__name")
