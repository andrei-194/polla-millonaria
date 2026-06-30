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
            help="Procesa un único partido por ID interno de Django.",
        )
        parser.add_argument(
            "--external-id",
            type=str,
            help="Procesa un único partido por external_id (ID de football-data.org).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-sincroniza aunque el partido ya esté marcado como 'finished' en la BD.",
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
        force = options["force"]
        window = options["window_minutes"]
        match_id = options.get("match_id")
        external_id = options.get("external_id")

        now = timezone.now()

        if external_id:
            candidatos = Match.objects.filter(external_id=external_id)
        elif match_id:
            candidatos = Match.objects.filter(id=match_id)
        else:
            status_filter = ("scheduled", "in_progress") if not force else ("scheduled", "in_progress", "finished")
            candidatos = Match.objects.filter(
                status__in=status_filter,
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
                if force or external_id or match_id:
                    self.stdout.write(
                        self.style.WARNING(f"    Status API: {result_dto.status} — forzando igualmente")
                    )
                else:
                    self.stdout.write(f"    Status: {result_dto.status} — se omite")
                    time.sleep(0.5)
                    continue

            duration_label = f" [{result_dto.match_duration}]" if result_dto.match_duration else ""
            pen_label = (
                f" (pen {result_dto.home_score_pen}-{result_dto.away_score_pen})"
                if result_dto.home_score_pen is not None else ""
            )
            self.stdout.write(
                f"    Resultado: {result_dto.home_score}-{result_dto.away_score}"
                f"{pen_label}{duration_label} (finished)"
            )

            if dry_run:
                self.stdout.write(self.style.WARNING("    [dry-run] No se aplica"))
                time.sleep(0.5)
                continue

            match.home_score = result_dto.home_score
            match.away_score = result_dto.away_score
            match.home_score_et = result_dto.home_score_et
            match.away_score_et = result_dto.away_score_et
            match.home_score_pen = result_dto.home_score_pen
            match.away_score_pen = result_dto.away_score_pen
            match.match_duration = result_dto.match_duration
            match.penalty_winner = result_dto.penalty_winner
            match.status = "finished"

            # Si el partido ya estaba puntuado, resetear eventos para que
            # propagar_y_calcular los re-procese con el score correcto.
            if force or external_id or match_id:
                from apps.predictions.infrastructure.models import EventoPartido
                reseteados = EventoPartido.objects.filter(
                    partido=match
                ).exclude(estado="cancelado").update(
                    resultado=None, estado=EventoPartido.Estado.CERRADO
                )
                if reseteados:
                    self.stdout.write(f"    EventoPartido reseteados: {reseteados}")

            match.save(update_fields=[
                "home_score", "away_score",
                "home_score_et", "away_score_et",
                "home_score_pen", "away_score_pen",
                "match_duration", "penalty_winner",
                "status", "synced_at",
            ])
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
