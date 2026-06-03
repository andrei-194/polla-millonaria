from django.contrib import admin
from django.contrib import messages

from .models import Score, ReglaPuntuacion, PuntuacionEvento, RankingFecha, RankingAcumulado


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ("user", "match", "quiniela", "points", "hit_type", "calculated_at")


@admin.register(ReglaPuntuacion)
class ReglaPuntuacionAdmin(admin.ModelAdmin):
    list_display = ("tipo_evento", "quiniela", "codigo_acierto", "puntos")
    list_filter = ("tipo_evento", "quiniela")


@admin.register(PuntuacionEvento)
class PuntuacionEventoAdmin(admin.ModelAdmin):
    list_display = (
        "usuario", "evento_partido", "quiniela",
        "valor_pronosticado", "valor_resultado", "codigo_acierto", "puntos", "calculado_en"
    )
    list_filter = ("quiniela", "codigo_acierto")
    search_fields = ("usuario__username",)


@admin.register(RankingFecha)
class RankingFechaAdmin(admin.ModelAdmin):
    list_display = ("posicion", "usuario", "quiniela", "fecha", "puntos", "calculado_en")
    list_filter = ("quiniela", "fecha")
    actions = ["recalcular_ranking"]

    def recalcular_ranking(self, request, queryset):
        from apps.scoring.application.services import RankingService
        service = RankingService()
        pares = queryset.values("quiniela_id", "fecha_id").distinct()
        for par in pares:
            service.recalcular_ranking_fecha(par["quiniela_id"], par["fecha_id"])
        self.message_user(request, f"Ranking recalculado para {pares.count()} combinación(es)")

    recalcular_ranking.short_description = "Recalcular ranking de fecha"


@admin.register(RankingAcumulado)
class RankingAcumuladoAdmin(admin.ModelAdmin):
    list_display = (
        "posicion", "usuario", "quiniela",
        "puntos_total", "exactos_total", "aciertos_total", "fechas_jugadas", "calculado_en"
    )
    list_filter = ("quiniela",)
    actions = ["recalcular_ranking"]

    def recalcular_ranking(self, request, queryset):
        from apps.scoring.application.services import RankingService
        service = RankingService()
        quinielas = queryset.values_list("quiniela_id", flat=True).distinct()
        for q_id in quinielas:
            service.recalcular_ranking_acumulado(q_id)
        self.message_user(request, f"Ranking acumulado recalculado para {len(quinielas)} quiniela(s)")

    recalcular_ranking.short_description = "Recalcular ranking acumulado"
