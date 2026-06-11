import time
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger("scoring.pipeline")


class Command(BaseCommand):
    help = "Sincroniza resultados de partidos finalizados desde football-data.org y dispara el pipeline de scoring."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra qué partidos se procesarían sin modificar la BD.",
        )
        parser.add_argument(
            "--window-minutes",
            type=int,
            default=240,
            help="Busca partidos cuya match_date esté entre ahora-window_minutes y ahora-90min. Default: 240.",
        )
        parser.add_argument(
            "--match-id",
            type=int,
            help="Procesa un único partido por ID interno.",
        )

    def handle(self, *args, **options):
        api_key = getattr(settings, "FOOTBALL_API_KEY", "")
        if not api_key:
            self.stdout.write(
                self.style.WARNING(
                    "FOOTBALL_API_KEY no configurada — nada que hacer. "
                    "Los resultados se propagan vía signal cuando el admin guarda el partido."
                )
            )
            return

        from apps.tournaments.infrastructure.adapters import FootballDataOrgAdapter
        from apps.tournaments.infrastructure.models import Match
        from apps.tournaments.application.result_service import MatchResultService

        adapter = FootballDataOrgAdapter()
        dry_run = options["dry_run"]
        window = options["window_minutes"]
        match_id = options.get("match_id")

        now = timezone.now()

        if match_id:
            candidatos = Match.objects.filter(id=match_id)
        else:
            candidatos = Match.objects.filter(
                status__in=("scheduled", "in_progress"),
                match_date__lte=now - timedelta(minutes=90),
                match_date__gte=now - timedelta(minutes=window),
            )

        total = candidatos.count()
        self.stdout.write(f"Partidos candidatos: {total}")

        actualizados = 0
        errores = 0
        service = MatchResultService()

        for match in candidatos.iterator():
            self.stdout.write(f"  → {match} (external_id={match.external_id})")

            try:
                result_dto = adapter.fetch_results(match.external_id)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"    Error API: {e}"))
                errores += 1
                time.sleep(0.5)
                continue

            if result_dto.status != "finished":
                self.stdout.write(f"    Status: {result_dto.status} — se omite")
                time.sleep(0.5)
                continue

            self.stdout.write(
                f"    Resultado: {result_dto.home_score}-{result_dto.away_score} (finished)"
            )

            if dry_run:
                self.stdout.write(self.style.WARNING("    [dry-run] No se aplica"))
                time.sleep(0.5)
                continue

            match.home_score = result_dto.home_score
            match.away_score = result_dto.away_score
            match.status = "finished"
            match.save(update_fields=["home_score", "away_score", "status", "synced_at"])
            # El signal post_save dispara propagar_y_calcular automáticamente.
            actualizados += 1
            time.sleep(0.5)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nListo — actualizados: {actualizados}, omitidos: {total - actualizados - errores}, errores: {errores}"
            )
        )
        if errores:
            raise SystemExit(1)
