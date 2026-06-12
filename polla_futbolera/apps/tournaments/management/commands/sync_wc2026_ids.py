"""
Mapea los external_id sintéticos (WC2026-MEX-RSA) a los IDs numéricos
reales de football-data.org.

Estrategia de matching:
  1. Mismo día UTC (cubre diferencias de hora en el seed)
  2. Nombre de equipo normalizado + mapa de alias EN→ES

Uso:
    python manage.py sync_wc2026_ids --dry-run
    python manage.py sync_wc2026_ids
"""
import logging
import unicodedata

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger("scoring.pipeline")

# Alias: nombre en inglés (API) → nombre en español (BD) — solo raíz significativa
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
    "democratic republic of congo": "rd congo",
    "czech republic": "chequia",
    "czechia": "chequia",
    "south korea": "corea del sur",
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
    "korea republic": "corea del sur",
}


def _norm(text: str | None) -> str:
    """Lowercase + quitar tildes/diacríticos. Retorna '' si text es None."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _resolve(api_name: str) -> str:
    """Normaliza un nombre de equipo de la API al formato de nuestra BD."""
    n = _norm(api_name)
    return ALIAS.get(n, n)


def _team_match(api_name: str, db_name: str) -> bool:
    api_resolved = _resolve(api_name)
    db_norm = _norm(db_name)
    # Coincidencia exacta normalizada
    if api_resolved == db_norm:
        return True
    # Coincidencia parcial: una es substring de la otra
    if api_resolved in db_norm or db_norm in api_resolved:
        return True
    # Comparten alguna palabra significativa (≥4 chars)
    stopwords = {"de", "del", "la", "los", "y", "the", "of", "and", "rd", "dr"}
    api_words = {w for w in api_resolved.split() if len(w) >= 4} - stopwords
    db_words = {w for w in db_norm.split() if len(w) >= 4} - stopwords
    return bool(api_words & db_words)


class Command(BaseCommand):
    help = "Actualiza external_id de partidos del Mundial 2026 con los IDs reales de football-data.org."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Muestra el mapeo sin modificar la BD.")
        parser.add_argument("--competition", default="WC")
        parser.add_argument("--season", default="2026")

    def handle(self, *args, **options):
        api_key = getattr(settings, "FOOTBALL_API_KEY", "")
        if not api_key:
            self.stdout.write(self.style.ERROR("FOOTBALL_API_KEY no configurada."))
            return

        from apps.tournaments.infrastructure.adapters import FootballDataOrgAdapter
        from apps.tournaments.infrastructure.models import Match, Tournament

        torneo = Tournament.objects.filter(external_code="WC2026").first()
        if not torneo:
            self.stdout.write(self.style.ERROR("Torneo WC2026 no encontrado en BD."))
            return

        self.stdout.write(f"Torneo: {torneo.name}")
        self.stdout.write(
            f"Fetching fixtures de football-data.org "
            f"({options['competition']}/{options['season']})..."
        )

        adapter = FootballDataOrgAdapter()
        try:
            fixtures = adapter.fetch_fixtures(options["competition"], options["season"])
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error al llamar la API: {e}"))
            raise

        self.stdout.write(f"API devolvió {len(fixtures)} fixtures.")

        nuestros = list(
            Match.objects.filter(tournament=torneo)
            .select_related("home_team", "away_team")
        )
        self.stdout.write(f"Partidos en BD: {len(nuestros)}")
        self.stdout.write("")

        # Indexar los nuestros por fecha UTC (solo el día)
        by_day: dict[str, list] = {}
        for m in nuestros:
            day = m.match_date.date().isoformat()
            by_day.setdefault(day, []).append(m)

        actualizados = 0
        ya_ok = 0
        sin_match = []
        ambiguos = []

        for fixture in fixtures:
            api_day = fixture.match_date.date().isoformat()

            # Candidatos del mismo día
            candidatos_dia = by_day.get(api_day, [])
            if not candidatos_dia:
                # Probar día anterior y siguiente (por zonas horarias al borde de medianoche)
                from datetime import date, timedelta
                api_date_obj = fixture.match_date.date()
                for delta in (-1, 1):
                    alt_day = (api_date_obj + timedelta(days=delta)).isoformat()
                    candidatos_dia += by_day.get(alt_day, [])

            if not candidatos_dia:
                sin_match.append(fixture)
                continue

            # Filtrar por nombre de equipos
            por_nombre = [
                m for m in candidatos_dia
                if _team_match(fixture.home_team_name, m.home_team.name)
                and _team_match(fixture.away_team_name, m.away_team.name)
            ]

            if len(por_nombre) == 0:
                # Intentar en orden invertido (casos donde API y BD difieren en local/visitante)
                por_nombre = [
                    m for m in candidatos_dia
                    if _team_match(fixture.home_team_name, m.away_team.name)
                    and _team_match(fixture.away_team_name, m.home_team.name)
                ]

            if len(por_nombre) == 0:
                sin_match.append(fixture)
                continue

            if len(por_nombre) > 1:
                ambiguos.append(
                    f"  AMBIGUO ({len(por_nombre)}): "
                    f"{fixture.home_team_name} vs {fixture.away_team_name} @ {fixture.match_date}"
                )
                continue

            match = por_nombre[0]
            new_id = fixture.external_id

            if match.external_id == new_id:
                ya_ok += 1
                continue

            self.stdout.write(
                f"  {match.home_team} vs {match.away_team}: "
                f"{match.external_id!r} → {new_id!r}"
            )

            if not options["dry_run"]:
                match.external_id = new_id
                match.save(update_fields=["external_id"])
            actualizados += 1

        self.stdout.write("")
        label = "[dry-run] " if options["dry_run"] else ""
        self.stdout.write(self.style.SUCCESS(
            f"{label}Actualizados: {actualizados} | Ya correctos: {ya_ok} | "
            f"Sin match: {len(sin_match)} | Ambiguos: {len(ambiguos)}"
        ))

        if ambiguos:
            self.stdout.write(f"\nAmbiguos ({len(ambiguos)}) — revisar manualmente:")
            for msg in ambiguos:
                self.stdout.write(self.style.WARNING(msg))

        if sin_match:
            self.stdout.write(f"\nAPI fixtures sin partido en BD ({len(sin_match)}):")
            for f in sin_match[:5]:
                self.stdout.write(f"  {f.home_team_name} vs {f.away_team_name} @ {f.match_date}")
            if len(sin_match) > 5:
                self.stdout.write(
                    f"  ... y {len(sin_match) - 5} más "
                    f"(probablemente fases eliminatorias pendientes de cargar)"
                )
