from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


GRUPOS = ["Jugador", "Moderador"]


class Command(BaseCommand):
    help = "Crea los datos mínimos de sistema necesarios para operar (idempotente)."

    def handle(self, *args, **options):
        created = []
        for nombre in GRUPOS:
            _, was_created = Group.objects.get_or_create(name=nombre)
            if was_created:
                created.append(nombre)

        if created:
            self.stdout.write(self.style.SUCCESS(f"Grupos creados: {', '.join(created)}"))
        else:
            self.stdout.write("Datos de sistema ya presentes, nada que hacer.")
