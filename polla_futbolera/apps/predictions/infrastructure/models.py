from django.conf import settings
from django.db import models


class TipoEvento(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    config = models.JSONField(default=dict)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "predictions_tipo_evento"
        verbose_name = "Tipo de Evento"

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"


class EventoPartido(models.Model):
    class Estado(models.TextChoices):
        ABIERTO   = "abierto",   "Abierto"
        CERRADO   = "cerrado",   "Cerrado"
        PUNTUADO  = "puntuado",  "Puntuado"
        CANCELADO = "cancelado", "Cancelado"

    partido     = models.ForeignKey(
        "tournaments.Match", on_delete=models.CASCADE, related_name="eventos"
    )
    quiniela    = models.ForeignKey(
        "quinielas.Quiniela", on_delete=models.CASCADE, related_name="eventos"
    )
    tipo_evento = models.ForeignKey(
        TipoEvento, on_delete=models.PROTECT, related_name="eventos"
    )
    estado      = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.ABIERTO
    )
    resultado   = models.CharField(max_length=50, blank=True, null=True)
    plazo_cierre = models.DateTimeField()

    class Meta:
        db_table = "predictions_evento_partido"
        unique_together = ("partido", "quiniela", "tipo_evento")
        verbose_name = "Evento de Partido"

    def __str__(self):
        return f"{self.partido} — {self.tipo_evento.codigo} [{self.estado}]"

    def esta_abierto(self) -> bool:
        from django.utils import timezone
        return self.estado == self.Estado.ABIERTO and timezone.now() < self.plazo_cierre


class PronosticoEvento(models.Model):
    usuario       = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="pronosticos_eventos"
    )
    evento_partido = models.ForeignKey(
        EventoPartido, on_delete=models.CASCADE, related_name="pronosticos"
    )
    valor         = models.CharField(max_length=50)
    enviado_en    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "predictions_pronostico_evento"
        unique_together = ("usuario", "evento_partido")
        verbose_name = "Pronóstico de Evento"

    def __str__(self):
        return f"{self.usuario.username}: {self.valor} → {self.evento_partido}"


class Prediction(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="predictions"
    )
    match = models.ForeignKey(
        "tournaments.Match", on_delete=models.CASCADE, related_name="predictions"
    )
    quiniela = models.ForeignKey(
        "quinielas.Quiniela", on_delete=models.CASCADE, related_name="predictions"
    )
    home_goals = models.PositiveSmallIntegerField()
    away_goals = models.PositiveSmallIntegerField()
    submitted_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "predictions_prediction"
        unique_together = ("user", "match", "quiniela")

    def __str__(self):
        return f"{self.user.username}: {self.home_goals}-{self.away_goals} ({self.match})"
