"""
Sincroniza match_date desde football-data.org y recalcula plazo_cierre de todos
los EventoPartido asociados. Solo actualiza, nunca crea ni borra.

Estrategia de matching: igual que sync_wc2026_ids (nombre de equipo normalizado
+ alias EN→ES), pero actualiza TODOS los registros que coincidan (tanto los de
external_id sintético como los ya mapeados a numérico).

Uso:
    python manage.py sync_match_dates --dry-run
    python manage.py sync_match_dates
"""
import unicodedata
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand

# Alias reutilizados de sync_wc2026_ids
ALIAS = {
    "turkey": "turquia",
    "ivory coast": "costa de marfil",
    "cote d'ivoire": "costa de marfil",
    "curaçao": "curazao",
    "curacao": "curazao",
    "united states": "estados unidos",
    "netherlands": "paises bajos",
    "belgium": "belgica",
    "switzerland": "suiza",
    "cape verde islands": "cabo verde",
    "cape verde": "cabo verde",
    "bosnia-herzegovina": "bosnia y herzegovina",
    "dr congo": "rd congo",
    "congo dr": "rd congo",
    "democratic republic of congo": "rd congo",
    "czech republic": "chequia",
    "czechia": "chequia",
    "south korea": "corea del sur",
    "korea republic": "corea del sur",
    "south africa": "sudafrica",
    "saudi arabia": "arabia saudita",
    "iran": "iran",
    "new zealand": "nueva zelanda",
    "jordan": "jordania",
    "algeria": "argelia",
    "austria": "austria",
    "norway": "noruega",
    "senegal": "senegal",
    "iraq": "irak",
    "scotland": "escocia",
    "haiti": "haiti",
    "sweden": "suecia",
    "tunisia": "tunez",
    "japan": "japon",
    "egypt": "egipto",
    "uruguay": "uruguay",
    "morocco": "marruecos",
    "panama": "panama",
    "croatia": "croacia",
    "ghana": "ghana",
    "colombia": "colombia",
    "portugal": "portugal",
    "uzbekistan": "uzbekistan",
    "england": "inglaterra",
    "france": "francia",
    "brazil": "brasil",
    "germany": "alemania",
    "argentina": "argentina",
    "mexico": "mexico",
    "canada": "canada",
    "australia": "australia",
    "ecuador": "ecuador",
    "qatar": "qatar",
    "paraguay": "paraguay",
    "spain": "espana",
}


def _norm(text: str | None) -> str:
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _resolve(api_name: str) -> str:
    n = _norm(api_name)
    return ALIAS.get(n, n)


def _team_match(api_name: str, db_name: str) -> bool:
    api_resolved = _resolve(api_name)
    db_norm = _norm(db_name)
    if api_resolved == db_norm:
        return True
    if api_resolved in db_norm or db_norm in api_resolved:
        return True
    stopwords = {"de", "del", "la", "los", "y", "the", "of", "and", "rd", "dr"}
    api_words = {w for w in api_resolved.split() if len(w) >= 4} - stopwords
    db_words = {w for w in db_norm.split() if len(w) >= 4} - stopwords
    return bool(api_words & db_words)


class Command(BaseCommand):
    help = (
        "Sincroniza match_date desde football-data.org y recalcula plazo_cierre "
        "de todos los EventoPartido asociados. Solo actualiza, nunca crea ni borra."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra los cambios sin aplicarlos.",
        )
        parser.add_argument(
            "--tolerance-minutes",
            type=int,
            default=0,
            help="Ignorar diferencias menores a N minutos. Default: 0.",
        )
        parser.add_argument(
            "--recalc-deadline",
            action="store_true",
            help="Recalcula plazo_cierre con el valor actual de PREDICTION_DEADLINE_MINUTES "
                 "aunque match_date no haya cambiado.",
        )
        parser.add_argument(
            "--competition",
            default="WC",
            help="Código de competición en football-data.org. Default: WC.",
        )
        parser.add_argument(
            "--season",
            default="2026",
            help="Temporada. Default: 2026.",
        )

    def handle(self, *args, **options):
        api_key = getattr(settings, "FOOTBALL_API_KEY", "")
        if not api_key:
            self.stdout.write(self.style.ERROR("FOOTBALL_API_KEY no configurada. Abortando."))
            return

        from apps.tournaments.infrastructure.adapters import FootballDataOrgAdapter
        from apps.tournaments.infrastructure.models import Match, Tournament
        from apps.predictions.infrastructure.models import EventoPartido

        dry_run = options["dry_run"]
        tolerance = timedelta(minutes=options["tolerance_minutes"])
        recalc_deadline = options["recalc_deadline"]
        deadline_minutes = getattr(settings, "PREDICTION_DEADLINE_MINUTES", 20)

        prefix = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(
            f"\n{prefix}Sincronizando horarios WC/{options['season']} desde football-data.org..."
        )
        self.stdout.write(
            f"  Tolerancia: {options['tolerance_minutes']} min | "
            f"Plazo cierre: -{deadline_minutes} min antes del partido\n"
        )

        adapter = FootballDataOrgAdapter()
        try:
            fixtures = adapter.fetch_fixtures(options["competition"], options["season"])
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error al obtener fixtures de la API: {e}"))
            return

        self.stdout.write(f"  API retornó {len(fixtures)} partidos.")

        torneo = Tournament.objects.filter(external_code="WC2026").first()
        if not torneo:
            self.stdout.write(self.style.ERROR("Torneo WC2026 no encontrado en BD."))
            return

        # Indexar todos los partidos del torneo por día UTC
        todos = list(
            Match.objects.filter(tournament=torneo)
            .select_related("home_team", "away_team")
        )
        self.stdout.write(f"  Partidos en BD (todos): {len(todos)}\n")

        from datetime import timedelta as td
        by_day: dict[str, list] = {}
        for m in todos:
            day = m.match_date.date().isoformat()
            by_day.setdefault(day, []).append(m)

        self.stdout.write(
            f"  {'PARTIDO':<32} {'HORA BD (UTC)':<22} {'HORA API (UTC)':<22} {'DIFF':>8}  {'REGISTROS':>9}  ACCIÓN"
        )
        self.stdout.write("  " + "-" * 108)

        actualizados_registros = 0
        actualizados_partidos = 0
        sin_cambio = 0
        no_encontrados = 0

        for fixture in sorted(fixtures, key=lambda f: f.match_date):
            api_date = fixture.match_date

            # Omitir fixtures de la API sin equipos definidos (rondas TBD)
            if not fixture.home_team_name or not fixture.away_team_name:
                continue

            api_date_obj = api_date.date()

            # Siempre buscar en día exacto + adyacentes (seed puede estar desfasado ±1 día)
            dias_a_buscar = {
                api_date_obj,
                api_date_obj + td(days=-1),
                api_date_obj + td(days=1),
            }
            candidatos_dia = []
            for d in dias_a_buscar:
                candidatos_dia += by_day.get(d.isoformat(), [])

            # Filtrar por nombre de equipos (orden normal)
            coincidencias = [
                m for m in candidatos_dia
                if m.home_team and m.away_team
                and _team_match(fixture.home_team_name, m.home_team.name)
                and _team_match(fixture.away_team_name, m.away_team.name)
            ]
            # Intentar orden invertido si no hubo
            if not coincidencias:
                coincidencias = [
                    m for m in candidatos_dia
                    if m.home_team and m.away_team
                    and _team_match(fixture.home_team_name, m.away_team.name)
                    and _team_match(fixture.away_team_name, m.home_team.name)
                ]

            if not coincidencias:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ {fixture.home_team_name} vs {fixture.away_team_name} "
                        f"@ {api_date.strftime('%Y-%m-%d %H:%M')} UTC — sin partido en BD"
                    )
                )
                no_encontrados += 1
                continue

            # Tomar el match_date de referencia del primer candidato
            bd_date_ref = coincidencias[0].match_date
            diff = api_date - bd_date_ref
            diff_abs = abs(diff)
            diff_min = int(diff.total_seconds() / 60)

            label = f"{fixture.home_team_name} vs {fixture.away_team_name}"
            bd_str = bd_date_ref.strftime("%Y-%m-%d %H:%M UTC")
            api_str = api_date.strftime("%Y-%m-%d %H:%M UTC")
            diff_str = f"{diff_min:+d} min"
            n_registros = len(coincidencias)

            if diff_abs <= tolerance:
                if recalc_deadline and not dry_run:
                    nuevo_plazo = api_date - timedelta(minutes=deadline_minutes)
                    for match in coincidencias:
                        EventoPartido.objects.filter(
                            partido=match,
                            estado=EventoPartido.Estado.ABIERTO,
                        ).update(plazo_cierre=nuevo_plazo)
                    self.stdout.write(
                        f"  ✓ {label:<32} {bd_str:<22} {api_str:<22} {diff_str:>8}  {n_registros:>9}  plazo recalculado"
                    )
                else:
                    self.stdout.write(
                        f"  ✓ {label:<32} {bd_str:<22} {api_str:<22} {diff_str:>8}  {n_registros:>9}  sin cambio"
                    )
                sin_cambio += 1
                continue

            accion = "[dry-run]" if dry_run else f"ACTUALIZADO"
            line = (
                f"  → {label:<32} {bd_str:<22} {api_str:<22} "
                f"{diff_str:>8}  {n_registros:>9} registros  {accion}"
            )
            self.stdout.write(self.style.SUCCESS(line) if not dry_run else line)

            if not dry_run:
                nuevo_plazo = api_date - timedelta(minutes=deadline_minutes)
                for match in coincidencias:
                    match.match_date = api_date
                    match.save(update_fields=["match_date", "synced_at"])
                    EventoPartido.objects.filter(
                        partido=match,
                        estado=EventoPartido.Estado.ABIERTO,
                    ).update(plazo_cierre=nuevo_plazo)
                    actualizados_registros += 1

            actualizados_partidos += 1

        self.stdout.write("\n" + "=" * 70)
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"  [DRY-RUN] Partidos con cambio pendiente: {actualizados_partidos} | "
                    f"Sin cambio: {sin_cambio} | No en BD: {no_encontrados}\n"
                    f"  → Ejecuta sin --dry-run para aplicar los cambios."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Partidos actualizados: {actualizados_partidos} | "
                    f"Registros DB modificados: {actualizados_registros} | "
                    f"Sin cambio: {sin_cambio} | No en BD: {no_encontrados}"
                )
            )
