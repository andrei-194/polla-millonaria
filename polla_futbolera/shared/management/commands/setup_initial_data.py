from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


GRUPOS = ["Jugador", "Moderador"]


class Command(BaseCommand):
    help = "Crea los datos mínimos de sistema necesarios para operar (idempotente)."

    def handle(self, *args, **options):
        self._setup_grupos()
        self._setup_schedules()

    def _setup_grupos(self):
        created = []
        for nombre in GRUPOS:
            _, was_created = Group.objects.get_or_create(name=nombre)
            if was_created:
                created.append(nombre)

        if created:
            self.stdout.write(self.style.SUCCESS(f"Grupos creados: {', '.join(created)}"))
        else:
            self.stdout.write("Grupos ya presentes.")

    def _setup_schedules(self):
        try:
            from django_q.models import Schedule
        except ImportError:
            self.stdout.write("django-q no instalado — schedules omitidos.")
            return

        schedule, created = Schedule.objects.get_or_create(
            name="sync_match_results_auto",
            defaults={
                "func": "apps.tournaments.application.tasks.run_sync_match_results",
                "schedule_type": Schedule.CRON,
                "cron": "*/15 * * * *",
                "repeats": -1,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS("Schedule sync_match_results creado (cada 15 min)."))
        else:
            self.stdout.write("Schedule sync_match_results ya presente.")
