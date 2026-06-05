"""
Descarga los escudos de los equipos del Mundial 2026 desde football-data.org
y los guarda en static/img/teams/{CODE}.svg para ser servidos por WhiteNoise.

Uso:
    python manage.py fetch_team_crests
    python manage.py fetch_team_crests --dry-run
    python manage.py fetch_team_crests --competition WC --season 2026
    python manage.py fetch_team_crests --force   # sobreescribir existentes
"""
import time
from pathlib import Path

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.tournaments.infrastructure.models import Team

STATIC_TEAMS_DIR = Path(settings.BASE_DIR) / "static" / "img" / "teams"

# football-data.org limita a 10 req/min en plan gratuito
_REQUEST_DELAY = 6.5  # segundos entre descargas de imagen


class Command(BaseCommand):
    help = "Descarga escudos de equipos desde football-data.org y actualiza Team.logo_url"

    def add_arguments(self, parser):
        parser.add_argument("--competition", default="WC", help="Código de competición (default: WC)")
        parser.add_argument("--season", default="2026", help="Temporada (default: 2026)")
        parser.add_argument("--force", action="store_true", help="Sobreescribir imágenes ya descargadas")
        parser.add_argument("--dry-run", action="store_true", help="Mostrar qué se haría sin descargar")

    def handle(self, *args, **options):
        api_key = getattr(settings, "FOOTBALL_API_KEY", "")
        if not api_key:
            raise CommandError("FOOTBALL_API_KEY no está configurado en settings.")

        STATIC_TEAMS_DIR.mkdir(parents=True, exist_ok=True)

        self.stdout.write(f"Obteniendo equipos de {options['competition']} {options['season']}...")
        api_teams = self._fetch_api_teams(api_key, options["competition"], options["season"])

        if not api_teams:
            raise CommandError(
                f"La API no devolvió equipos para {options['competition']} {options['season']}. "
                "Verificá que tu plan incluye esta competición y que la temporada existe."
            )

        self.stdout.write(f"  {len(api_teams)} equipos recibidos de la API\n")

        ok, skipped, not_found, failed = 0, 0, 0, 0

        for api_team in api_teams:
            tla = (api_team.get("tla") or "").upper()
            crest_url = api_team.get("crest") or ""
            name = api_team.get("name", "?")

            if not tla or not crest_url:
                self.stdout.write(self.style.WARNING(f"  SKIP  {name} — sin tla o sin crest"))
                skipped += 1
                continue

            try:
                db_team = Team.objects.get(external_code=tla)
            except Team.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  NF    {tla} ({name}) — no está en la BD"))
                not_found += 1
                continue

            ext = self._extension_from_url(crest_url)
            dest_path = STATIC_TEAMS_DIR / f"{tla}{ext}"
            static_path = f"img/teams/{tla}{ext}"

            if dest_path.exists() and not options["force"]:
                self.stdout.write(f"  EXIST {tla} — {dest_path.name}")
                if db_team.logo_url != static_path:
                    db_team.logo_url = static_path
                    db_team.save(update_fields=["logo_url"])
                skipped += 1
                continue

            if options["dry_run"]:
                self.stdout.write(f"  DRY   {tla} → {dest_path.name}  ({crest_url})")
                ok += 1
                continue

            success = self._download_image(crest_url, dest_path, tla)
            if success:
                db_team.logo_url = static_path
                db_team.save(update_fields=["logo_url"])
                self.stdout.write(self.style.SUCCESS(f"  OK    {tla} ({name}) → {dest_path.name}"))
                ok += 1
                time.sleep(_REQUEST_DELAY)
            else:
                failed += 1

        self._print_summary(ok, skipped, not_found, failed, options["dry_run"])

        if not options["dry_run"] and ok > 0:
            self.stdout.write(
                "\nPróximo paso: commitear las imágenes descargadas:\n"
                "  git add polla_futbolera/static/img/teams/\n"
                "  git commit -m 'feat: agregar escudos equipos Mundial 2026'"
            )

    # ──────────────────────────────────────────────────────────────────────

    def _fetch_api_teams(self, api_key: str, competition: str, season: str) -> list[dict]:
        url = f"{settings.FOOTBALL_API_BASE_URL}/competitions/{competition}/teams"
        try:
            with httpx.Client(timeout=20) as client:
                resp = client.get(
                    url,
                    params={"season": season},
                    headers={"X-Auth-Token": api_key},
                )
                if resp.status_code == 403:
                    raise CommandError(
                        "403 Forbidden — tu plan de football-data.org no incluye esta competición."
                    )
                resp.raise_for_status()
                return resp.json().get("teams", [])
        except httpx.HTTPStatusError as e:
            raise CommandError(f"Error de API: {e.response.status_code} {e.response.text[:200]}")
        except httpx.RequestError as e:
            raise CommandError(f"Error de red: {e}")

    def _download_image(self, url: str, dest: Path, code: str) -> bool:
        try:
            with httpx.Client(timeout=15, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
                dest.write_bytes(resp.content)
            return True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  FAIL  {code} — {e}"))
            return False

    def _extension_from_url(self, url: str) -> str:
        path = url.split("?")[0]
        if path.endswith(".svg"):
            return ".svg"
        if path.endswith(".png"):
            return ".png"
        return ".svg"  # football-data.org sirve SVG por defecto

    def _print_summary(self, ok: int, skipped: int, not_found: int, failed: int, dry_run: bool):
        label = "[DRY RUN] " if dry_run else ""
        self.stdout.write(f"\n{label}Resumen:")
        self.stdout.write(self.style.SUCCESS(f"  ✓ Descargados : {ok}"))
        self.stdout.write(f"  → Existentes  : {skipped}")
        if not_found:
            self.stdout.write(self.style.WARNING(f"  ? No en BD    : {not_found}"))
        if failed:
            self.stdout.write(self.style.ERROR(f"  ✗ Fallidos    : {failed}"))
