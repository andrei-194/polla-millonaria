from django.contrib import admin, messages
from .models import Quiniela, Inscripcion


@admin.register(Quiniela)
class QuinielaAdmin(admin.ModelAdmin):
    list_display = ("name", "tournament", "status", "created_at")
    list_filter = ("status", "tournament")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
    actions = ["recalcular_ranking_acumulado"]

    @admin.action(description="▶ Recalcular ranking acumulado de las quinielas seleccionadas")
    def recalcular_ranking_acumulado(self, request, queryset):
        """Recalcula el RankingAcumulado a partir de las PuntuacionEvento existentes."""
        from apps.scoring.application.services import RankingService
        svc = RankingService()
        for quiniela in queryset:
            svc.recalcular_ranking_acumulado(quiniela.id)
        self.message_user(
            request,
            f"✓ Ranking acumulado recalculado para {queryset.count()} quiniela(s).",
            messages.SUCCESS,
        )


@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ("jugador", "quiniela", "activa", "inscrito_en")
    list_filter = ("activa", "quiniela")
    search_fields = ("jugador__username", "quiniela__name")
    raw_id_fields = ("jugador",)
