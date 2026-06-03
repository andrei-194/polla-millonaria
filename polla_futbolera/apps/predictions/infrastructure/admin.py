from django.contrib import admin
from django.contrib import messages

from ..application.services import PredictionService
from .models import TipoEvento, EventoPartido, PronosticoEvento


@admin.register(TipoEvento)
class TipoEventoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo", "creado_en")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")
    readonly_fields = ("creado_en",)


@admin.register(EventoPartido)
class EventoPartidoAdmin(admin.ModelAdmin):
    list_display = ("partido", "quiniela", "tipo_evento", "estado", "resultado", "plazo_cierre")
    list_editable = ("resultado", "estado")
    list_filter = ("estado", "quiniela", "tipo_evento", "partido__fecha")
    search_fields = ("partido__home_team__name", "partido__away_team__name")
    actions = ["calcular_puntos"]


    def calcular_puntos(self, request, queryset):
        """
        Calcula puntos solo para los EventoPartido seleccionados.
        Útil para recalcular eventos individuales o corregir un resultado.
        Para procesar una fecha completa de una vez, usar la acción en el admin de Fechas.
        """
        from apps.scoring.application.services import ScoringService
        from apps.scoring.domain.exceptions import EventoSinResultadoError
        service = ScoringService()
        ok = 0
        for evento in queryset:
            try:
                service.calcular_puntos_evento(evento.id)
                ok += 1
            except EventoSinResultadoError:
                self.message_user(
                    request,
                    f"El evento '{evento}' no tiene resultado — completalo antes de calcular.",
                    level=messages.WARNING,
                )
        if ok:
            self.message_user(
                request,
                f"✓ Puntos calculados para {ok} evento(s). "
                "Acordate de recalcular el ranking desde el admin de Fechas.",
                level=messages.SUCCESS,
            )

    calcular_puntos.short_description = "Calcular puntos para los eventos seleccionados"


@admin.register(PronosticoEvento)
class PronosticoEventoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "evento_partido", "valor", "enviado_en")
    list_filter = ("evento_partido__quiniela",)
    search_fields = ("usuario__username",)
