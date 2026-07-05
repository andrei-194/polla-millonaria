"""
Crea partidos de fases eliminatorias del Mundial 2026 en la BD
y genera EventoPartido para todas las quinielas activas del torneo.

Diseñado para ejecutarse una vez por ronda, cuando la API ya tiene
los equipos confirmados. Es idempotente: correrlo dos veces no duplica datos.

Uso:
    python manage.py sync_knockout_matches --dry-run
    python manage.py sync_knockout_matches
    python manage.py sync_knockout_matches --quiniela-slug mi-quiniela
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.tournaments.management.commands.sync_wc2026_ids import (
    _norm,
    _resolve,
    _team_match,
)

logger = logging.getLogger("scoring.pipeline")

# Prefijos que identifican partidos de grupo — se excluyen
_GROUP_PREFIXES = ("GROUP_",)

# Partidos en estos estados ya tienen resultado real y/o puntuaciones calculadas.
# Re-sincronizar jamás debe pisar su status ni sus datos.
_PROTECTED_STATUSES = ("finished", "in_progress")

# Mapeo de stage API → numero de Fecha en BD (creadas por seed_mundial_2026)
PHASE_TO_FECHA = {
    "LAST_32":        4,
    "ROUND_OF_32":    4,
    "LAST_16":        5,
    "ROUND_OF_16":    5,
    "QUARTER_FINALS": 6,
    "SEMI_FINALS":    7,
    "THIRD_PLACE":    8,
    "FINAL":          8,
}


def _is_group_stage(phase: str) -> bool:
    return phase == "GROUP_STAGE" or any(phase.startswith(p) for p in _GROUP_PREFIXES)


def _find_team(api_name: str, equipos_por_nombre: dict):
    """Resuelve un nombre de equipo de la API al objeto Team de la BD."""
    resolved = _resolve(api_name)
    if resolved in equipos_por_nombre:
        return equipos_por_nombre[resolved]
    for team in equipos_por_nombre.values():
        if _team_match(api_name, team.name):
            return team
    return None


class Command(BaseCommand):
    help = (
        "Crea partidos eliminatorios del WC2026 desde football-data.org "
        "y genera EventoPartido para las quinielas activas."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Muestra qué haría sin escribir en la BD.",
        )
        parser.add_argument("--competition", default="WC")
        parser.add_argument("--season", default="2026")
        parser.add_argument(
            "--quiniela-slug", default=None,
            help="Limitar creación de eventos a una quiniela específica.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        label = "[dry-run] " if dry_run else ""

        if not getattr(settings, "FOOTBALL_API_KEY", ""):
            self.stdout.write(self.style.ERROR("FOOTBALL_API_KEY no configurada."))
            return

        from apps.predictions.infrastructure.models import EventoPartido, TipoEvento
        from apps.quinielas.infrastructure.models import Quiniela
        from apps.tournaments.infrastructure.adapters import FootballDataOrgAdapter
        from apps.tournaments.infrastructure.models import Fecha, Match, Team, Tournament

        # ── Cargar torneo ────────────────────────────────────────────────────
        torneo = Tournament.objects.filter(external_code="WC2026").first()
        if not torneo:
            self.stdout.write(self.style.ERROR("Torneo WC2026 no encontrado en BD."))
            return

        # ── Índices de apoyo ─────────────────────────────────────────────────
        fechas = {f.numero: f for f in Fecha.objects.filter(torneo=torneo)}
        equipos_por_nombre = {_norm(t.name): t for t in Team.objects.all()}

        # ── Quinielas activas del torneo ─────────────────────────────────────
        quinielas_qs = Quiniela.objects.filter(tournament=torneo, status="activa")
        if options["quiniela_slug"]:
            quinielas_qs = quinielas_qs.filter(slug=options["quiniela_slug"])
        quinielas = list(quinielas_qs)

        if not quinielas:
            self.stdout.write(self.style.WARNING(
                "No hay quinielas activas para este torneo. "
                "Se crearán los partidos pero sin EventoPartido."
            ))

        # ── Fetch API (1 solo request) ───────────────────────────────────────
        self.stdout.write(
            f"Fetching {options['competition']}/{options['season']} "
            "desde football-data.org..."
        )
        adapter = FootballDataOrgAdapter()
        try:
            fixtures = adapter.fetch_fixtures(options["competition"], options["season"])
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error al llamar la API: {e}"))
            raise

        knockout = [f for f in fixtures if not _is_group_stage(f.phase)]
        self.stdout.write(
            f"API: {len(fixtures)} partidos totales, {len(knockout)} eliminatorios."
        )
        self.stdout.write("")

        # ── Procesar ─────────────────────────────────────────────────────────
        creados = actualizados = protegidos = eventos_creados = eventos_existentes = 0
        skipped_tbd = skipped_equipo = skipped_fase = 0

        for fixture in knockout:
            # Equipos sin confirmar todavía
            if not fixture.home_team_name or not fixture.away_team_name:
                skipped_tbd += 1
                continue

            # Resolver Fecha
            fecha_num = PHASE_TO_FECHA.get(fixture.phase)
            if fecha_num is None:
                self.stdout.write(self.style.WARNING(
                    f"  Fase desconocida '{fixture.phase}' — skip. "
                    "Agrega al mapeo PHASE_TO_FECHA."
                ))
                skipped_fase += 1
                continue
            fecha_obj = fechas.get(fecha_num)
            if fecha_obj is None:
                self.stdout.write(self.style.WARNING(
                    f"  Fecha num={fecha_num} no encontrada en BD — skip."
                ))
                skipped_fase += 1
                continue

            # Resolver equipos
            home = _find_team(fixture.home_team_name, equipos_por_nombre)
            away = _find_team(fixture.away_team_name, equipos_por_nombre)
            if home is None or away is None:
                faltantes = [
                    n for n, t in [(fixture.home_team_name, home), (fixture.away_team_name, away)]
                    if t is None
                ]
                logger.error(
                    "Equipo(s) no encontrado(s): %s (API id=%s)",
                    faltantes, fixture.external_id,
                )
                self.stdout.write(self.style.ERROR(
                    f"  Equipo no encontrado: {faltantes} — skip."
                ))
                skipped_equipo += 1
                continue

            fecha_str = fixture.match_date.strftime("%Y-%m-%d %H:%M UTC")

            # Un partido ya finalizado (o en curso) es intocable: su resultado
            # y puntuaciones ya están calculados. Re-sincronizar acá nunca debe
            # pisar su status ni sus datos — solo nos interesa crear partidos
            # de fases que todavía no tenemos registradas.
            existente = Match.objects.filter(external_id=fixture.external_id).first()
            protegido = existente is not None and existente.status in _PROTECTED_STATUSES

            if protegido:
                self.stdout.write(
                    f"  {label}{fixture.phase}: {home} vs {away} @ {fecha_str} "
                    f"— ya {existente.get_status_display().lower()}, no se modifica"
                )
                protegidos += 1
                match = existente
            else:
                self.stdout.write(f"  {label}{fixture.phase}: {home} vs {away} @ {fecha_str}")

                if dry_run:
                    if existente is None:
                        creados += 1
                    else:
                        actualizados += 1
                    continue

                # Crear / actualizar partido (solo llega acá si no está protegido)
                match, created = Match.objects.update_or_create(
                    external_id=fixture.external_id,
                    defaults={
                        "tournament": torneo,
                        "home_team": home,
                        "away_team": away,
                        "match_date": fixture.match_date,
                        "phase": fixture.phase,
                        "fecha": fecha_obj,
                        "status": "scheduled",
                    },
                )
                if created:
                    creados += 1
                else:
                    actualizados += 1

            if dry_run:
                continue

            # Crear EventoPartido por quiniela (solo los tipos que ya usa esa quiniela).
            # Se ejecuta también para partidos protegidos, por si se sumó una
            # quiniela nueva después de que el partido ya había finalizado.
            plazo = fixture.match_date - timedelta(
                minutes=settings.PREDICTION_DEADLINE_MINUTES
            )
            for quiniela in quinielas:
                tipos = list(
                    TipoEvento.objects.filter(
                        eventos__quiniela=quiniela, activo=True
                    ).distinct()
                )
                for tipo in tipos:
                    _, ep_created = EventoPartido.objects.get_or_create(
                        partido=match,
                        quiniela=quiniela,
                        tipo_evento=tipo,
                        defaults={"plazo_cierre": plazo, "estado": "abierto"},
                    )
                    if ep_created:
                        eventos_creados += 1
                    else:
                        eventos_existentes += 1

        # ── Resumen ──────────────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"{label}Partidos — creados: {creados} | actualizados: {actualizados} | "
            f"protegidos (ya finalizados/en curso): {protegidos} | "
            f"TBD: {skipped_tbd} | equipo no encontrado: {skipped_equipo} | "
            f"fase desconocida: {skipped_fase}"
        ))
        if not dry_run and quinielas:
            self.stdout.write(self.style.SUCCESS(
                f"{label}EventoPartido — creados: {eventos_creados} | "
                f"ya existían: {eventos_existentes}"
            ))
