from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Genera y envía el reporte diario de performance por email."

    def handle(self, *args, **options):
        from apps.observability.application.services import ReporteService

        self.stdout.write("Generando reporte de performance...")
        ReporteService().generar_y_enviar()
        self.stdout.write(self.style.SUCCESS("Reporte enviado."))
