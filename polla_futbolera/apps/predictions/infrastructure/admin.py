from django.contrib import admin
from django.contrib import messages

from ..application.services import PredictionService
from .models import Prediction, TipoEvento, EventoPartido, PronosticoEvento


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ("user", "match", "quiniela", "home_goals", "away_goals", "submitted_at")


@admin.register(TipoEvento)
class TipoEventoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo", "creado_en")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")
    readonly_fields = ("creado_en",)


@admin.register(EventoPartido)
class EventoPartidoAdmin(admin.ModelAdmin):
    list_display = ("partido", "quiniela", "tipo_evento", "estado", "resultado", "plazo_cierre")
    list_filter = ("estado", "quiniela", "tipo_evento")
    search_fields = ("partido__home_team__name", "partido__away_team__name")
    actions = ["calcular_puntos"]

    def calcular_puntos(self, request, queryset):
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
                    f"El evento {evento} no tiene resultado registrado",
                    level=messages.WARNING,
                )
        if ok:
            self.message_user(request, f"Puntos calculados para {ok} evento(s)")

    calcular_puntos.short_description = "Calcular puntos para los eventos seleccionados"


@admin.register(PronosticoEvento)
class PronosticoEventoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "evento_partido", "valor", "enviado_en")
    list_filter = ("evento_partido__quiniela",)
    search_fields = ("usuario__username",)
