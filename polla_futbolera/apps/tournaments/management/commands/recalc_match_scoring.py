"""
Re-ejecuta el pipeline de scoring para partidos ya finalizados.

Útil para corregir puntuaciones erróneas cuando el score almacenado era incorrecto
(ej: marcador de penales guardado como score de tiempo reglamentario).

Uso:
    python manage.py recalc_match_scoring --match-id 42
    python manage.py recalc_match_scoring --from-date 2026-06-28
    python manage.py recalc_match_scoring --phase knockout
    python manage.py recalc_match_scoring --from-date 2026-06-28 --dry-run
"""
import logging
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

logger = logging.getLogger("scoring.pipeline")


class Command(BaseCommand):
    help = "Re-ejecuta el pipeline de scoring para partidos finalizados con puntuación incorrecta."

    def add_arguments(self, parser):
        parser.add_argument(
            "--match-id", type=int, default=None,
            help="ID interno del partido a recalcular.",
        )
        parser.add_argument(
            "--from-date", default=None,
            help="Recalcular todos los partidos finalizados desde esta fecha (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--phase", default=None,
            help="Filtrar por fase del partido (ej: 'knockout', 'QUARTER_FINALS').",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Muestra qué partidos se recalcularían sin modificar la BD.",
        )

    def handle(self, *args, **options):
        from apps.predictions.infrastructure.models import EventoPartido
        from apps.tournaments.application.result_service import MatchResultService
        from apps.tournaments.infrastructure.models import Match

        if not options["match_id"] and not options["from_date"] and not options["phase"]:
            raise CommandError(
                "Debes especificar al menos uno de: --match-id, --from-date, --phase"
            )

        qs = Match.objects.filter(status="finished")

        if options["match_id"]:
            qs = qs.filter(id=options["match_id"])

        if options["from_date"]:
            try:
                from_date = date.fromisoformat(options["from_date"])
            except ValueError:
                raise CommandError("--from-date debe estar en formato YYYY-MM-DD")
            qs = qs.filter(match_date__date__gte=from_date)

        if options["phase"]:
            qs = qs.filter(phase__icontains=options["phase"])

        partidos = list(qs.order_by("match_date"))
        total = len(partidos)

        if not partidos:
            self.stdout.write(self.style.WARNING("No se encontraron partidos con los filtros indicados."))
            return

        self.stdout.write(f"Partidos a recalcular: {total}")
        if options["dry_run"]:
            for m in partidos:
                self.stdout.write(f"  [dry-run] {m} (id={m.id}, score={m.home_score}-{m.away_score})")
            return

        service = MatchResultService()
        recalculados = 0
        errores = 0

        for match in partidos:
            self.stdout.write(f"  → {match} (id={match.id})")

            try:
                with transaction.atomic():
                    # Resetear EventoPartido para que propagar_y_calcular los re-procese
                    eventos_qs = EventoPartido.objects.filter(
                        partido=match
                    ).exclude(estado="cancelado")

                    resetados = eventos_qs.update(resultado=None, estado=EventoPartido.Estado.CERRADO)
                    self.stdout.write(f"    EventoPartido reseteados: {resetados}")

                resultado = service.propagar_y_calcular(match.id)
                self.stdout.write(
                    f"    Pipeline OK — eventos: {resultado['eventos']}, "
                    f"quinielas: {resultado['quinielas']}"
                )
                recalculados += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"    ERROR: {e}"))
                logger.exception("Error recalculando match %s", match.id)
                errores += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Listo — recalculados: {recalculados} | errores: {errores}"
            )
        )
        if errores:
            raise SystemExit(1)
