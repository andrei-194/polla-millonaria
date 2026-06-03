from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


DEMO_TEAMS = [
    ("DEMO-T1", "Atlético Demo"),
    ("DEMO-T2", "Real Demo FC"),
    ("DEMO-T3", "Demo United"),
    ("DEMO-T4", "Demo City"),
    ("DEMO-T5", "Demo Rovers"),
    ("DEMO-T6", "Deportivo Demo"),
    ("DEMO-T7", "Demo Athletic"),
    ("DEMO-T8", "Demo Wanderers"),
]

FECHA1_MATCHUPS = [(0, 1), (2, 3), (4, 5), (6, 7)]
FECHA2_MATCHUPS = [(0, 2), (1, 3), (4, 6), (5, 7)]


class Command(BaseCommand):
    help = "Seed demo Fechas, Matches y EventoPartido para el sistema de predicciones v3"

    def add_arguments(self, parser):
        parser.add_argument(
            "--slug",
            type=str,
            default=None,
            help="Slug de la quiniela a sembrar (por defecto: todas las activas)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Crear eventos incluso si ya existen fechas para el torneo",
        )

    def handle(self, *args, **options):
        from apps.predictions.infrastructure.models import EventoPartido, TipoEvento
        from apps.quinielas.infrastructure.models import Quiniela
        from apps.tournaments.infrastructure.models import Fecha, Match, Team

        slug = options["slug"]
        force = options["force"]

        quinielas = (
            Quiniela.objects.filter(slug=slug, status="activa")
            if slug
            else Quiniela.objects.filter(status="activa")
        )

        if not quinielas.exists():
            self.stdout.write(self.style.ERROR("No se encontraron quinielas activas."))
            return

        try:
            tipo_score = TipoEvento.objects.get(codigo="SCORE")
            tipo_winner = TipoEvento.objects.get(codigo="WINNER")
        except TipoEvento.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    "TipoEvento no encontrado. Ejecutá primero: python manage.py migrate"
                )
            )
            return

        for quiniela in quinielas:
            tournament = quiniela.tournament
            self.stdout.write(f"\nProcesando: {quiniela.name} (torneo: {tournament.name})")

            if Fecha.objects.filter(torneo=tournament).exists() and not force:
                self.stdout.write(
                    self.style.WARNING(
                        "  El torneo ya tiene fechas. Solo sembrando EventoPartido faltantes."
                    )
                )
                eventos_count = self._seed_eventos(quiniela, tournament, tipo_score, tipo_winner)
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ {eventos_count} EventoPartido nuevos para {quiniela.name}")
                )
                continue

            teams = self._get_or_create_teams(tournament)
            now = timezone.now()
            base = now.replace(hour=15, minute=0, second=0, microsecond=0) + timedelta(days=7)

            fecha1 = self._get_or_create_fecha(tournament, 1, "Fecha 1", base, base + timedelta(days=1))
            fecha2 = self._get_or_create_fecha(
                tournament, 2, "Fecha 2", base + timedelta(days=14), base + timedelta(days=15)
            )

            self._get_or_create_matches(tournament, fecha1, teams, FECHA1_MATCHUPS, base, "F1")
            self._get_or_create_matches(
                tournament, fecha2, teams, FECHA2_MATCHUPS, base + timedelta(days=14), "F2"
            )

            eventos_count = self._seed_eventos(quiniela, tournament, tipo_score, tipo_winner)
            self.stdout.write(
                self.style.SUCCESS(f"  ✓ {eventos_count} EventoPartido creados para {quiniela.name}")
            )

    def _get_or_create_teams(self, tournament):
        from apps.tournaments.infrastructure.models import Team

        teams = []
        for code, name in DEMO_TEAMS:
            team, created = Team.objects.get_or_create(
                external_code=code,
                defaults={"name": name, "logo_url": ""},
            )
            if created:
                self.stdout.write(f"  + Equipo creado: {name}")
            teams.append(team)
        return teams

    def _get_or_create_fecha(self, tournament, numero, nombre, fecha_inicio, fecha_fin):
        from apps.tournaments.infrastructure.models import Fecha

        fecha, created = Fecha.objects.get_or_create(
            torneo=tournament,
            numero=numero,
            defaults={
                "nombre": nombre,
                "fecha_inicio": fecha_inicio.date(),
                "fecha_fin": fecha_fin.date(),
            },
        )
        if created:
            self.stdout.write(f"  + Fecha creada: {nombre}")
        return fecha

    def _get_or_create_matches(self, tournament, fecha, teams, matchups, base_date, prefix):
        from apps.tournaments.infrastructure.models import Match

        matches = []
        for i, (home_idx, away_idx) in enumerate(matchups):
            ext_id = f"DEMO-{tournament.id}-{prefix}-M{i + 1}"
            match_time = base_date + timedelta(hours=i * 2)
            match, created = Match.objects.get_or_create(
                external_id=ext_id,
                defaults={
                    "tournament": tournament,
                    "home_team": teams[home_idx],
                    "away_team": teams[away_idx],
                    "phase": "group",
                    "match_date": match_time,
                    "status": "scheduled",
                    "fecha": fecha,
                },
            )
            if not created and match.fecha != fecha:
                match.fecha = fecha
                match.save(update_fields=["fecha"])
            matches.append(match)
        return matches

    def _seed_eventos(self, quiniela, tournament, tipo_score, tipo_winner):
        from apps.predictions.infrastructure.models import EventoPartido
        from apps.tournaments.infrastructure.models import Match

        matches = Match.objects.filter(tournament=tournament, fecha__isnull=False)
        count = 0
        for match in matches:
            for tipo in [tipo_score, tipo_winner]:
                _, created = EventoPartido.objects.get_or_create(
                    partido=match,
                    quiniela=quiniela,
                    tipo_evento=tipo,
                    defaults={
                        "estado": EventoPartido.Estado.ABIERTO,
                        "plazo_cierre": match.match_date - timedelta(hours=1),
                    },
                )
                if created:
                    count += 1
        return count
