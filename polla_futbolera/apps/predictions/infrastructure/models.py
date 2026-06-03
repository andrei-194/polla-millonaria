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

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.plazo_cierre and self.partido_id:
            from apps.tournaments.infrastructure.models import Match
            try:
                match_date = Match.objects.values_list("match_date", flat=True).get(pk=self.partido_id)
                if self.plazo_cierre >= match_date:
                    raise ValidationError({
                        "plazo_cierre": (
                            f"El plazo de cierre ({self.plazo_cierre:%d/%m/%Y %H:%M}) "
                            f"debe ser anterior al inicio del partido "
                            f"({match_date:%d/%m/%Y %H:%M})."
                        )
                    })
            except Match.DoesNotExist:
                pass

    def esta_abierto(self) -> bool:
        from django.utils import timezone
        # El partido en curso o finalizado cierra el evento aunque plazo_cierre sea futuro.
        # Esto previene que un admin descuidado extienda el plazo después de iniciado el partido.
        partido_activo = self.partido.status in ("in_progress", "finished")
        return (
            self.estado == self.Estado.ABIERTO
            and timezone.now() < self.plazo_cierre
            and not partido_activo
        )


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


