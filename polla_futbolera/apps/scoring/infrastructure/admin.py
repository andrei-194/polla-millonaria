import json

from django.contrib import admin
from django.contrib import messages
from django.urls import path

from .models import ReglaPuntuacion, PuntuacionEvento, RankingFecha, RankingAcumulado, CalculoJob


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


@admin.register(CalculoJob)
class CalculoJobAdmin(admin.ModelAdmin):
    list_display = ("__str__", "estado", "iniciado_por", "creado_en", "actualizado_en")
    list_filter = ("estado",)
    readonly_fields = ("estado", "creado_en", "actualizado_en", "resumen", "error_msg", "iniciado_por")
    filter_horizontal = ("fechas",)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:job_id>/status/",
                self.admin_site.admin_view(self.status_view),
                name="scoring_calculojob_status",
            )
        ]
        return custom + urls

    def status_view(self, request, job_id):
        from django.http import JsonResponse
        job = CalculoJob.objects.get(id=job_id)
        return JsonResponse({
            "estado": job.estado,
            "resumen": json.loads(job.resumen) if job.resumen else None,
            "error": job.error_msg or None,
        })

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        job = self.get_object(request, object_id)
        if job and job.estado in ("PENDING", "RUNNING"):
            extra_context["polling_job_id"] = job.id
        return super().change_view(request, object_id, form_url, extra_context)

    class Media:
        js = ("scoring/js/calculo_job_polling.js",)
