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
        from apps.scoring.infrastructure.models import CalculoJob
        from apps.scoring.application.tasks import pipeline_ranking

        job = CalculoJob.objects.create(iniciado_por=request.user)
        job.fechas.set(queryset)

        pipeline_ranking(job.id)

        job.refresh_from_db()
        if job.estado == "DONE":
            self.message_user(
                request,
                f"✓ Pipeline completado (Job #{job.id}). {job.resumen}",
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
