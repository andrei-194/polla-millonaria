from django.contrib import admin

from .infrastructure.models import PerformanceMetric


@admin.register(PerformanceMetric)
class PerformanceMetricAdmin(admin.ModelAdmin):
    list_display = ("label", "duration_ms_display", "success", "alerta_enviada", "quiniela_id", "timestamp")
    list_filter = ("label", "success", "alerta_enviada")
    search_fields = ("label", "error_msg")
    readonly_fields = ("label", "duration_ms", "timestamp", "quiniela_id", "fecha_id", "match_id", "extra", "success", "error_msg", "alerta_enviada")
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)

    @admin.display(description="Duración")
    def duration_ms_display(self, obj):
        return f"{obj.duration_ms:.0f} ms"
