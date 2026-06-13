from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = "Elimina métricas de performance más antiguas que OBSERVABILITY_RETENTION_DAYS."

    def handle(self, *args, **options):
        from apps.observability.infrastructure.models import PerformanceMetric

        dias = getattr(settings, "OBSERVABILITY_RETENTION_DAYS", 30)
        corte = timezone.now() - timedelta(days=dias)
        eliminadas, _ = PerformanceMetric.objects.filter(timestamp__lt=corte).delete()
        self.stdout.write(
            self.style.SUCCESS(f"Métricas eliminadas: {eliminadas} (anteriores a {corte:%Y-%m-%d})")
        )
