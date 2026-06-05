from django.conf import settings
from django.db import models


class ReglaPuntuacion(models.Model):
    tipo_evento = models.ForeignKey(
        "predictions.TipoEvento", on_delete=models.CASCADE, related_name="reglas"
    )
    quiniela = models.ForeignKey(
        "quinielas.Quiniela", on_delete=models.CASCADE,
        null=True, blank=True, related_name="reglas_puntos"
    )
    codigo_acierto = models.CharField(max_length=20)
    puntos = models.SmallIntegerField()

    class Meta:
        db_table = "scoring_regla_puntuacion"
        unique_together = ("tipo_evento", "quiniela", "codigo_acierto")
        verbose_name = "Regla de Puntuación"

    def __str__(self):
        scope = f"[{self.quiniela}]" if self.quiniela else "[global]"
        return f"{self.tipo_evento.codigo} {scope} {self.codigo_acierto} → {self.puntos}pts"


class PuntuacionEvento(models.Model):
    usuario            = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="puntuaciones"
    )
    evento_partido     = models.ForeignKey(
        "predictions.EventoPartido", on_delete=models.CASCADE, related_name="puntuaciones"
    )
    quiniela           = models.ForeignKey(
        "quinielas.Quiniela", on_delete=models.CASCADE, related_name="puntuaciones"
    )
    valor_pronosticado = models.CharField(max_length=50)
    valor_resultado    = models.CharField(max_length=50)
    codigo_acierto     = models.CharField(max_length=20)
    puntos             = models.SmallIntegerField(default=0)
    calculado_en       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scoring_puntuacion_evento"
        unique_together = ("usuario", "evento_partido")
        verbose_name = "Puntuación de Evento"
        indexes = [
            models.Index(fields=["quiniela", "usuario"], name="idx_pun_quiniela_usuario"),
        ]

    def __str__(self):
        return f"{self.usuario.username}: {self.puntos}pts ({self.codigo_acierto})"


class RankingFecha(models.Model):
    quiniela  = models.ForeignKey(
        "quinielas.Quiniela", on_delete=models.CASCADE, related_name="rankings_fecha"
    )
    fecha     = models.ForeignKey(
        "tournaments.Fecha", on_delete=models.CASCADE, related_name="rankings"
    )
    usuario   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rankings_fecha"
    )
    puntos    = models.SmallIntegerField(default=0)
    posicion  = models.PositiveSmallIntegerField(default=0)
    calculado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scoring_ranking_fecha"
        unique_together = ("quiniela", "fecha", "usuario")
        ordering = ["posicion"]
        verbose_name = "Ranking por Fecha"
        indexes = [
            models.Index(fields=["quiniela", "fecha", "posicion"], name="idx_rf_quiniela_fecha_pos"),
        ]

    def __str__(self):
        return f"#{self.posicion} {self.usuario.username} — {self.fecha} ({self.puntos}pts)"


class RankingAcumulado(models.Model):
    quiniela  = models.ForeignKey(
        "quinielas.Quiniela", on_delete=models.CASCADE, related_name="ranking_acumulado"
    )
    usuario   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ranking_acumulado"
    )
    puntos_total    = models.SmallIntegerField(default=0)
    posicion        = models.PositiveSmallIntegerField(default=0)
    fechas_jugadas  = models.PositiveSmallIntegerField(default=0)
    exactos_total   = models.PositiveSmallIntegerField(default=0)
    aciertos_total  = models.PositiveSmallIntegerField(default=0)
    calculado_en    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scoring_ranking_acumulado"
        unique_together = ("quiniela", "usuario")
        ordering = ["posicion"]
        verbose_name = "Ranking Acumulado"
        indexes = [
            models.Index(fields=["quiniela", "posicion"], name="idx_ranking_acum_quiniela_pos"),
        ]

    def __str__(self):
        return f"#{self.posicion} {self.usuario.username} — {self.quiniela} ({self.puntos_total}pts)"


class CalculoJob(models.Model):
    ESTADO_CHOICES = [
        ("PENDING", "Pendiente"),
        ("RUNNING", "En proceso"),
        ("DONE", "Completado"),
        ("ERROR", "Error"),
    ]

    estado         = models.CharField(max_length=10, choices=ESTADO_CHOICES, default="PENDING")
    fechas         = models.ManyToManyField("tournaments.Fecha", blank=True)
    iniciado_por   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    creado_en      = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    resumen        = models.TextField(blank=True)
    error_msg      = models.TextField(blank=True)

    class Meta:
        db_table = "scoring_calculo_job"
        ordering = ["-creado_en"]
        verbose_name = "Job de Cálculo"
        verbose_name_plural = "Jobs de Cálculo"

    def __str__(self):
        return f"Job #{self.pk} [{self.estado}] — {self.creado_en:%Y-%m-%d %H:%M}"
