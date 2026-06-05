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

    @admin.action(description="▶ Calcular puntos y recalcular rankings (async)")
    def calcular_puntos_y_ranking(self, request, queryset):
        """
        Encola el pipeline de scoring+ranking como tarea async en django-q2.
        Responde inmediatamente y redirige al admin del job para seguir el progreso.
        """
        from django_q.tasks import async_task
        from apps.scoring.infrastructure.models import CalculoJob

        job = CalculoJob.objects.create(iniciado_por=request.user)
        job.fechas.set(queryset)

        async_task(
            "apps.scoring.application.tasks.pipeline_ranking",
            job.id,
            task_name=f"ranking-job-{job.id}",
        )

        self.message_user(
            request,
            (
                f"⏳ Cálculo encolado (Job #{job.id}). Podés ver el progreso en "
                f"Admin → Scoring → Jobs de Cálculo."
            ),
            messages.INFO,
        )


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("__str__", "tournament", "fecha", "phase", "status", "match_date")
    list_filter = ("status", "tournament", "fecha")
    search_fields = ("home_team__name", "away_team__name")
