from datetime import datetime, timedelta, timezone

from django.conf import settings
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

_TEAMS_DIR = Path(settings.BASE_DIR) / "static" / "img" / "teams"


def _detect_logo(code: str) -> str:
    for ext in (".svg", ".png"):
        if (_TEAMS_DIR / f"{code}{ext}").exists():
            return f"img/teams/{code}{ext}"
    return ""


TORNEO = {
    "name": "Copa Mundial FIFA 2026",
    "external_code": "WC2026",
    "season": "2026",
}

EQUIPOS = [
    # Grupo A
    ("MEX", "México"),
    ("RSA", "Sudáfrica"),
    ("KOR", "Corea del Sur"),
    ("CZE", "Chequia"),
    # Grupo B
    ("CAN", "Canadá"),
    ("BIH", "Bosnia y Herzegovina"),
    ("QAT", "Qatar"),
    ("SUI", "Suiza"),
    # Grupo C
    ("BRA", "Brasil"),
    ("MAR", "Marruecos"),
    ("HAI", "Haití"),
    ("SCO", "Escocia"),
    # Grupo D
    ("USA", "Estados Unidos"),
    ("PAR", "Paraguay"),
    ("AUS", "Australia"),
    ("TUR", "Turquía"),
    # Grupo E
    ("GER", "Alemania"),
    ("CUW", "Curazao"),
    ("CIV", "Costa de Marfil"),
    ("ECU", "Ecuador"),
    # Grupo F
    ("NED", "Países Bajos"),
    ("JPN", "Japón"),
    ("SWE", "Suecia"),
    ("TUN", "Túnez"),
    # Grupo G
    ("BEL", "Bélgica"),
    ("EGY", "Egipto"),
    ("IRN", "Irán"),
    ("NZL", "Nueva Zelanda"),
    # Grupo H
    ("ESP", "España"),
    ("CPV", "Cabo Verde"),
    ("KSA", "Arabia Saudita"),
    ("URY", "Uruguay"),
    # Grupo I
    ("FRA", "Francia"),
    ("SEN", "Senegal"),
    ("IRQ", "Irak"),
    ("NOR", "Noruega"),
    # Grupo J
    ("ARG", "Argentina"),
    ("ALG", "Argelia"),
    ("AUT", "Austria"),
    ("JOR", "Jordania"),
    # Grupo K
    ("POR", "Portugal"),
    ("COD", "RD Congo"),
    ("UZB", "Uzbekistán"),
    ("COL", "Colombia"),
    # Grupo L
    ("ENG", "Inglaterra"),
    ("CRO", "Croacia"),
    ("GHA", "Ghana"),
    ("PAN", "Panamá"),
]

# (numero, nombre, fecha_inicio, fecha_fin)
FECHAS = [
    (1, "Jornada 1 — Fase de Grupos", "2026-06-11", "2026-06-17"),
    (2, "Jornada 2 — Fase de Grupos", "2026-06-18", "2026-06-23"),
    (3, "Jornada 3 — Fase de Grupos", "2026-06-24", "2026-06-27"),
    (4, "Ronda de 32",                "2026-06-28", "2026-07-03"),
    (5, "Octavos de Final",           "2026-07-04", "2026-07-07"),
    (6, "Cuartos de Final",           "2026-07-08", "2026-07-12"),
    (7, "Semifinales",                "2026-07-14", "2026-07-15"),
    (8, "Final",                      "2026-07-18", "2026-07-19"),
]

# (local, visitante, datetime_utc, phase, fecha_num)
PARTIDOS = [
    # ── FECHA 1: JORNADA 1 ──────────────────────────────────────────
    # Jun 11
    ("MEX", "RSA",  "2026-06-11 19:00", "GROUP_A", 1),
    ("KOR", "CZE",  "2026-06-12 03:00", "GROUP_A", 1),
    # Jun 12
    ("CAN", "BIH",  "2026-06-12 21:00", "GROUP_B", 1),
    ("USA", "PAR",  "2026-06-12 23:00", "GROUP_D", 1),
    # Jun 13
    ("QAT", "SUI",  "2026-06-13 19:00", "GROUP_B", 1),
    ("BRA", "MAR",  "2026-06-13 23:00", "GROUP_C", 1),
    ("HAI", "SCO",  "2026-06-14 03:00", "GROUP_C", 1),
    ("AUS", "TUR",  "2026-06-14 04:00", "GROUP_D", 1),
    # Jun 14
    ("GER", "CUW",  "2026-06-14 17:00", "GROUP_E", 1),
    ("NED", "JPN",  "2026-06-14 19:00", "GROUP_F", 1),
    ("SWE", "TUN",  "2026-06-15 00:00", "GROUP_F", 1),
    ("CIV", "ECU",  "2026-06-15 00:00", "GROUP_E", 1),
    # Jun 15
    ("BEL", "EGY",  "2026-06-15 16:00", "GROUP_G", 1),
    ("ESP", "CPV",  "2026-06-15 16:00", "GROUP_H", 1),
    ("IRN", "NZL",  "2026-06-15 23:00", "GROUP_G", 1),
    ("KSA", "URY",  "2026-06-15 23:00", "GROUP_H", 1),
    # Jun 16
    ("FRA", "SEN",  "2026-06-16 20:00", "GROUP_I", 1),
    ("IRQ", "NOR",  "2026-06-16 23:00", "GROUP_I", 1),
    ("ARG", "ALG",  "2026-06-17 01:00", "GROUP_J", 1),
    ("AUT", "JOR",  "2026-06-17 01:00", "GROUP_J", 1),
    # Jun 17
    ("POR", "COD",  "2026-06-17 16:00", "GROUP_K", 1),
    ("ENG", "CRO",  "2026-06-17 19:00", "GROUP_L", 1),
    ("GHA", "PAN",  "2026-06-18 00:00", "GROUP_L", 1),
    ("UZB", "COL",  "2026-06-18 02:00", "GROUP_K", 1),

    # ── FECHA 2: JORNADA 2 ──────────────────────────────────────────
    # Jun 18
    ("CZE", "RSA",  "2026-06-18 18:00", "GROUP_A", 2),
    ("SUI", "BIH",  "2026-06-18 19:00", "GROUP_B", 2),
    ("CAN", "QAT",  "2026-06-18 21:00", "GROUP_B", 2),
    ("MEX", "KOR",  "2026-06-19 01:00", "GROUP_A", 2),
    # Jun 19
    ("USA", "AUS",  "2026-06-19 16:00", "GROUP_D", 2),
    ("SCO", "MAR",  "2026-06-19 23:00", "GROUP_C", 2),
    ("BRA", "HAI",  "2026-06-20 02:00", "GROUP_C", 2),
    ("TUR", "PAR",  "2026-06-20 04:00", "GROUP_D", 2),
    # Jun 20
    ("NED", "SWE",  "2026-06-20 16:00", "GROUP_F", 2),
    ("GER", "CIV",  "2026-06-20 21:00", "GROUP_E", 2),
    ("ECU", "CUW",  "2026-06-21 00:00", "GROUP_E", 2),
    ("TUN", "JPN",  "2026-06-21 02:00", "GROUP_F", 2),
    # Jun 21
    ("BEL", "IRN",  "2026-06-21 16:00", "GROUP_G", 2),
    ("ESP", "KSA",  "2026-06-21 16:00", "GROUP_H", 2),
    ("NZL", "EGY",  "2026-06-21 23:00", "GROUP_G", 2),
    ("URY", "CPV",  "2026-06-21 23:00", "GROUP_H", 2),
    # Jun 22
    ("ARG", "AUT",  "2026-06-22 16:00", "GROUP_J", 2),
    ("FRA", "IRQ",  "2026-06-22 22:00", "GROUP_I", 2),
    ("JOR", "ALG",  "2026-06-23 00:00", "GROUP_J", 2),
    ("NOR", "SEN",  "2026-06-23 01:00", "GROUP_I", 2),
    # Jun 23
    ("POR", "UZB",  "2026-06-23 16:00", "GROUP_K", 2),
    ("ENG", "GHA",  "2026-06-23 20:00", "GROUP_L", 2),
    ("PAN", "CRO",  "2026-06-23 23:00", "GROUP_L", 2),
    ("COL", "COD",  "2026-06-24 02:00", "GROUP_K", 2),

    # ── FECHA 3: JORNADA 3 ──────────────────────────────────────────
    # Jun 24 — Grupos B y C (simultáneos por grupo)
    ("SUI", "CAN",  "2026-06-24 18:00", "GROUP_B", 3),
    ("BIH", "QAT",  "2026-06-24 19:00", "GROUP_B", 3),
    ("MAR", "HAI",  "2026-06-24 23:00", "GROUP_C", 3),
    ("SCO", "BRA",  "2026-06-24 23:00", "GROUP_C", 3),
    # Jun 24-25 — Grupo A (simultáneos)
    ("CZE", "MEX",  "2026-06-25 03:00", "GROUP_A", 3),
    ("RSA", "KOR",  "2026-06-25 03:00", "GROUP_A", 3),
    # Jun 25 — Grupos D, E, F (simultáneos por grupo)
    ("ECU", "GER",  "2026-06-25 21:00", "GROUP_E", 3),
    ("CUW", "CIV",  "2026-06-25 21:00", "GROUP_E", 3),
    ("JPN", "SWE",  "2026-06-25 22:00", "GROUP_F", 3),
    ("TUN", "NED",  "2026-06-25 22:00", "GROUP_F", 3),
    ("TUR", "USA",  "2026-06-25 23:00", "GROUP_D", 3),
    ("PAR", "AUS",  "2026-06-26 00:00", "GROUP_D", 3),
    # Jun 26 — Grupos G, H, I (simultáneos por grupo)
    ("SEN", "IRQ",  "2026-06-26 20:00", "GROUP_I", 3),
    ("NOR", "FRA",  "2026-06-26 20:00", "GROUP_I", 3),
    ("URY", "ESP",  "2026-06-26 22:00", "GROUP_H", 3),
    ("CPV", "KSA",  "2026-06-26 23:00", "GROUP_H", 3),
    ("NZL", "BEL",  "2026-06-27 00:00", "GROUP_G", 3),
    ("EGY", "IRN",  "2026-06-27 00:00", "GROUP_G", 3),
    # Jun 27 — Grupos J, K, L (simultáneos por grupo)
    ("CRO", "GHA",  "2026-06-27 21:00", "GROUP_L", 3),
    ("PAN", "ENG",  "2026-06-27 21:00", "GROUP_L", 3),
    ("COD", "UZB",  "2026-06-28 00:30", "GROUP_K", 3),
    ("COL", "POR",  "2026-06-28 00:30", "GROUP_K", 3),
    ("JOR", "ARG",  "2026-06-28 01:00", "GROUP_J", 3),
    ("ALG", "AUT",  "2026-06-28 01:00", "GROUP_J", 3),
]


def _parse_utc(dt_str: str) -> datetime:
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    return dt.replace(tzinfo=timezone.utc)


class Command(BaseCommand):
    help = "Carga los 48 equipos, 8 fechas y 72 partidos de la fase grupal del Mundial 2026."

    def add_arguments(self, parser):
        parser.add_argument(
            "--quiniela-slug",
            type=str,
            default=None,
            help="Slug de la quiniela a la que se le crearán EventoPartido (SCORE + WINNER)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Recrear partidos aunque ya existan",
        )

    def handle(self, *args, **options):
        from apps.tournaments.infrastructure.models import Fecha, Match, Team, Tournament

        torneo, created = Tournament.objects.get_or_create(
            external_code=TORNEO["external_code"],
            defaults={"name": TORNEO["name"], "season": TORNEO["season"], "status": "active"},
        )
        self.stdout.write(
            self.style.SUCCESS(f"{'+ Torneo creado' if created else '  Torneo ya existe'}: {torneo}")
        )

        equipos = self._seed_equipos()
        fechas = self._seed_fechas(torneo)
        partidos_count = self._seed_partidos(torneo, equipos, fechas, options["force"])

        self.stdout.write(self.style.SUCCESS(
            f"\n✓ {len(equipos)} equipos | {len(fechas)} fechas | {partidos_count} partidos"
        ))

        if options["quiniela_slug"]:
            deadline_minutes = getattr(settings, "PREDICTION_DEADLINE_MINUTES", 20)
            self._seed_eventos(options["quiniela_slug"], torneo, deadline_minutes)

    # ──────────────────────────────────────────────────────────────────────

    def _seed_equipos(self):
        from apps.tournaments.infrastructure.models import Team

        equipos = {}
        nuevos = 0
        logos_actualizados = 0
        for code, name in EQUIPOS:
            logo = _detect_logo(code)
            team, created = Team.objects.get_or_create(
                external_code=code,
                defaults={"name": name, "logo_url": logo},
            )
            if created:
                nuevos += 1
            elif logo and team.logo_url != logo:
                team.logo_url = logo
                team.save(update_fields=["logo_url"])
                logos_actualizados += 1
            equipos[code] = team
        self.stdout.write(
            f"  Equipos: {nuevos} nuevos, {len(EQUIPOS) - nuevos} ya existían"
            + (f", {logos_actualizados} logos actualizados" if logos_actualizados else "")
        )
        return equipos

    def _seed_fechas(self, torneo):
        from apps.tournaments.infrastructure.models import Fecha

        fechas = {}
        nuevas = 0
        for numero, nombre, inicio, fin in FECHAS:
            fecha, created = Fecha.objects.get_or_create(
                torneo=torneo,
                numero=numero,
                defaults={
                    "nombre": nombre,
                    "fecha_inicio": inicio,
                    "fecha_fin": fin,
                },
            )
            if created:
                nuevas += 1
            fechas[numero] = fecha
        self.stdout.write(f"  Fechas:  {nuevas} nuevas, {len(FECHAS) - nuevas} ya existían")
        return fechas

    def _seed_partidos(self, torneo, equipos, fechas, force):
        from apps.tournaments.infrastructure.models import Match

        nuevos = 0
        for home_code, away_code, dt_str, phase, fecha_num in PARTIDOS:
            ext_id = f"WC2026-{home_code}-{away_code}"
            match_date = _parse_utc(dt_str)

            if force:
                Match.objects.filter(
                    tournament=torneo,
                    home_team=equipos[home_code],
                    away_team=equipos[away_code],
                ).delete()

            # Idempotencia robusta: buscar por external_id sintético primero,
            # luego por nombre de equipo (cubre el caso en que sync_wc2026_ids
            # ya mapeó el external_id a numérico, o que el equipo tenga un código
            # distinto por haber sido sembrado con una versión anterior del seed).
            exists = (
                Match.objects.filter(external_id=ext_id).exists()
                or Match.objects.filter(
                    tournament=torneo,
                    home_team__name=equipos[home_code].name,
                    away_team__name=equipos[away_code].name,
                ).exists()
            )
            if not exists:
                Match.objects.create(
                    external_id=ext_id,
                    tournament=torneo,
                    home_team=equipos[home_code],
                    away_team=equipos[away_code],
                    phase=phase,
                    match_date=match_date,
                    status="scheduled",
                    fecha=fechas[fecha_num],
                )
                nuevos += 1

        total = len(PARTIDOS)
        self.stdout.write(f"  Partidos:{nuevos} nuevos, {total - nuevos} ya existían")
        return total

    def _seed_eventos(self, slug, torneo, deadline_minutes):
        from apps.predictions.infrastructure.models import EventoPartido, TipoEvento
        from apps.quinielas.infrastructure.models import Quiniela
        from apps.tournaments.infrastructure.models import Match

        try:
            quiniela = Quiniela.objects.get(slug=slug)
        except Quiniela.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"  Quiniela '{slug}' no encontrada."))
            return

        tipos = list(TipoEvento.objects.filter(codigo__in=["SCORE", "WINNER", "BTTS", "OU25"]))
        if len(tipos) != 4:
            self.stdout.write(self.style.ERROR("  TipoEvento faltante. Ejecutá migrate primero."))
            return

        matches = Match.objects.filter(tournament=torneo, fecha__isnull=False)
        count = 0
        for match in matches:
            for tipo in tipos:
                _, created = EventoPartido.objects.get_or_create(
                    partido=match,
                    quiniela=quiniela,
                    tipo_evento=tipo,
                    defaults={
                        "estado": EventoPartido.Estado.ABIERTO,
                        "plazo_cierre": match.match_date - timedelta(minutes=deadline_minutes),
                    },
                )
                if created:
                    count += 1

        self.stdout.write(self.style.SUCCESS(
            f"  ✓ {count} EventoPartido creados para quiniela '{quiniela.name}'"
        ))
