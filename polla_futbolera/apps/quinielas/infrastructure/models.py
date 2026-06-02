from django.conf import settings
from django.db import models


class Quiniela(models.Model):
    STATUS_CHOICES = [("activa", "Activa"), ("finalizada", "Finalizada")]

    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, max_length=170)
    description = models.TextField(blank=True, default="")
    tournament = models.ForeignKey(
        "tournaments.Tournament", on_delete=models.CASCADE, related_name="quinielas"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="activa")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "quinielas_quiniela"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class Inscripcion(models.Model):
    jugador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="inscripciones",
    )
    quiniela = models.ForeignKey(
        Quiniela,
        on_delete=models.CASCADE,
        related_name="inscripciones",
    )
    activa = models.BooleanField(default=True)
    inscrito_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "quinielas_inscripcion"
        unique_together = ("jugador", "quiniela")

    def __str__(self):
        return f"{self.jugador.username} → {self.quiniela.name}"
