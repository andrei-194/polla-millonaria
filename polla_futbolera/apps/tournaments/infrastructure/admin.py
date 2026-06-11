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

    @admin.action(description="▶ Calcular puntos y recalcular rankings")
    def calcular_puntos_y_ranking(self, request, queryset):
        import json
        from apps.scoring.infrastructure.models import CalculoJob
        from apps.scoring.application.tasks import pipeline_ranking

        job = CalculoJob.objects.create(iniciado_por=request.user)
        job.fechas.set(queryset)

        pipeline_ranking(job.id)

        job.refresh_from_db()
        if job.estado == "DONE":
            resumen = json.loads(job.resumen) if job.resumen else {}
            eventos_ok = resumen.get("eventos_ok", 0)
            sin_resultado = resumen.get("sin_resultado", 0)
            quinielas = resumen.get("quinielas_procesadas", 0)

            if eventos_ok == 0:
                self.message_user(
                    request,
                    f"⚠ Pipeline ejecutado pero sin puntuaciones (Job #{job.id}). "
                    f"{sin_resultado} evento(s) sin resultado registrado. "
                    f"Primero registra los resultados en Predictions → Eventos de partido, "
                    f"luego vuelve a correr esta acción.",
                    messages.WARNING,
                )
            else:
                self.message_user(
                    request,
                    f"✓ {eventos_ok} evento(s) puntuados en {quinielas} quiniela(s). "
                    f"{sin_resultado} evento(s) sin resultado (aún no jugados).",
                    messages.SUCCESS,
                )
        else:
            self.message_user(
                request,
                f"✗ Error en Job #{job.id}: {job.error_msg[:200]}",
                messages.ERROR,
            )


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("__str__", "tournament", "fecha", "phase", "status", "match_date")
    list_filter = ("status", "tournament", "fecha")
    search_fields = ("home_team__name", "away_team__name")
