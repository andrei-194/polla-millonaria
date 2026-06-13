from django.db import models


class PerformanceMetric(models.Model):
    """Registro de tiempo de ejecución de operaciones críticas del sistema."""

    label        = models.CharField(max_length=100, db_index=True)
    duration_ms  = models.FloatField()
    timestamp    = models.DateTimeField(auto_now_add=True, db_index=True)

    quiniela_id  = models.IntegerField(null=True, blank=True, db_index=True)
    fecha_id     = models.IntegerField(null=True, blank=True)
    match_id     = models.IntegerField(null=True, blank=True)
    extra        = models.JSONField(default=dict, blank=True)

    success      = models.BooleanField(default=True)
    error_msg    = models.TextField(blank=True)
    alerta_enviada = models.BooleanField(default=False)

    class Meta:
        db_table = "observability_performance_metric"
        ordering = ["-timestamp"]
        verbose_name = "Métrica de Performance"
        verbose_name_plural = "Métricas de Performance"
        indexes = [
            models.Index(fields=["label", "timestamp"], name="idx_pm_label_timestamp"),
            models.Index(fields=["timestamp"], name="idx_pm_timestamp"),
        ]

    def __str__(self):
        status = "OK" if self.success else "ERR"
        return f"{self.label} | {self.duration_ms:.0f}ms | {status} | {self.timestamp:%Y-%m-%d %H:%M}"
