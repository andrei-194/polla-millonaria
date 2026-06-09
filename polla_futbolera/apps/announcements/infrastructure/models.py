from django.db import models
from django.utils import timezone


class Anuncio(models.Model):
    titulo = models.CharField(max_length=120)
    cuerpo = models.TextField(help_text="Texto visible para el jugador. HTML básico permitido.")
    emoji = models.CharField(max_length=10, blank=True, default="")
    cta_texto = models.CharField(max_length=60, blank=True, default="", verbose_name="Texto del botón")
    cta_url = models.CharField(max_length=200, blank=True, default="", verbose_name="URL del botón")
    activo = models.BooleanField(default=True)
    inicio = models.DateTimeField(null=True, blank=True, help_text="Dejar vacío para mostrar desde ya.")
    fin = models.DateTimeField(null=True, blank=True, help_text="Dejar vacío para no vencer nunca.")
    orden = models.PositiveSmallIntegerField(default=0, help_text="Menor número = aparece primero.")

    class Meta:
        ordering = ["orden", "-id"]
        verbose_name = "Anuncio"
        verbose_name_plural = "Anuncios"

    def __str__(self):
        return self.titulo

    @classmethod
    def activos_ahora(cls):
        now = timezone.now()
        return cls.objects.filter(
            activo=True,
        ).filter(
            models.Q(inicio__isnull=True) | models.Q(inicio__lte=now)
        ).filter(
            models.Q(fin__isnull=True) | models.Q(fin__gte=now)
        )
