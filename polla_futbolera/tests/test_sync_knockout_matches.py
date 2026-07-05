"""
Tests del comando sync_knockout_matches.

Ejecutar:
    docker-compose exec web python manage.py test tests.test_sync_knockout_matches
"""
import datetime
from datetime import timezone as dt_tz
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.predictions.infrastructure.models import EventoPartido, TipoEvento
from apps.quinielas.infrastructure.models import Quiniela
from apps.tournaments.domain.ports import MatchDTO
from apps.tournaments.infrastructure.models import Fecha, Match, Team, Tournament

UTC = dt_tz.utc


def _fixture(home_name, away_name, phase, external_id="900001"):
    return MatchDTO(
        external_id=external_id,
        home_team_name=home_name,
        away_team_name=away_name,
        home_team_code="X",
        away_team_code="Y",
        match_date=datetime.datetime(2026, 6, 29, 18, 0, 0, tzinfo=UTC),
        phase=phase,
    )


@override_settings(FOOTBALL_API_KEY="test-key", PREDICTION_DEADLINE_MINUTES=20)
class TestSyncKnockoutMatches(TestCase):

    def setUp(self):
        self.torneo = Tournament.objects.create(
            name="Copa Mundial FIFA 2026",
            external_code="WC2026",
            season="2026",
            status="active",
        )
        # Fechas necesarias para eliminatorias
        self.fecha_r32 = Fecha.objects.create(
            torneo=self.torneo, numero=4, nombre="Ronda de 32",
            fecha_inicio="2026-06-28", fecha_fin="2026-07-03",
        )
        self.fecha_octavos = Fecha.objects.create(
            torneo=self.torneo, numero=5, nombre="Octavos de Final",
            fecha_inicio="2026-07-04", fecha_fin="2026-07-07",
        )
        self.fecha_final = Fecha.objects.create(
            torneo=self.torneo, numero=8, nombre="Final",
            fecha_inicio="2026-07-18", fecha_fin="2026-07-19",
        )

        # Equipos
        self.mex = Team.objects.create(name="México", external_code="MEX")
        self.ger = Team.objects.create(name="Alemania", external_code="GER")

        # Quiniela activa
        self.quiniela = Quiniela.objects.create(
            name="Q Test", slug="q-test",
            tournament=self.torneo, status="activa",
        )
        self.tipo_score, _ = TipoEvento.objects.get_or_create(
            codigo="SCORE", defaults={"nombre": "Marcador exacto", "config": {}, "activo": True},
        )
        self.tipo_winner, _ = TipoEvento.objects.get_or_create(
            codigo="WINNER",
            defaults={"nombre": "Ganador", "config": {}, "activo": True},
        )

        # Partido de grupo preexistente → genera EventoPartido para que el lookup de tipos funcione
        fecha_grupo = Fecha.objects.create(
            torneo=self.torneo, numero=1, nombre="Jornada 1",
            fecha_inicio="2026-06-11", fecha_fin="2026-06-17",
        )
        match_grupo = Match.objects.create(
            tournament=self.torneo,
            home_team=self.mex, away_team=self.ger,
            external_id="grupo-001",
            match_date=datetime.datetime(2026, 6, 12, 18, 0, tzinfo=UTC),
            phase="GROUP_A", fecha=fecha_grupo,
        )
        plazo = datetime.datetime(2026, 6, 12, 17, 40, tzinfo=UTC)
        EventoPartido.objects.create(
            partido=match_grupo, quiniela=self.quiniela,
            tipo_evento=self.tipo_score, plazo_cierre=plazo,
        )
        EventoPartido.objects.create(
            partido=match_grupo, quiniela=self.quiniela,
            tipo_evento=self.tipo_winner, plazo_cierre=plazo,
        )

    # ── Caso base: crea partido + eventos ────────────────────────────────────

    @patch("apps.tournaments.infrastructure.adapters.FootballDataOrgAdapter.fetch_fixtures")
    def test_crea_partido_y_eventos(self, mock_fetch):
        mock_fetch.return_value = [
            _fixture("Mexico", "Germany", "LAST_32", "900001"),
        ]
        call_command("sync_knockout_matches")

        match = Match.objects.get(external_id="900001")
        self.assertEqual(match.home_team, self.mex)
        self.assertEqual(match.away_team, self.ger)
        self.assertEqual(match.phase, "LAST_32")
        self.assertEqual(match.fecha, self.fecha_r32)
        self.assertEqual(match.status, "scheduled")

        eventos = EventoPartido.objects.filter(partido=match, quiniela=self.quiniela)
        self.assertEqual(eventos.count(), 2)  # SCORE + WINNER
        tipos_creados = set(eventos.values_list("tipo_evento__codigo", flat=True))
        self.assertSetEqual(tipos_creados, {"SCORE", "WINNER"})

    # ── Plazo de cierre correcto ─────────────────────────────────────────────

    @patch("apps.tournaments.infrastructure.adapters.FootballDataOrgAdapter.fetch_fixtures")
    def test_plazo_cierre_es_match_date_menos_deadline(self, mock_fetch):
        mock_fecha = datetime.datetime(2026, 6, 29, 18, 0, 0, tzinfo=UTC)
        mock_fetch.return_value = [
            MatchDTO(
                external_id="900002",
                home_team_name="Mexico",
                away_team_name="Germany",
                home_team_code="X", away_team_code="Y",
                match_date=mock_fecha,
                phase="LAST_32",
            )
        ]
        call_command("sync_knockout_matches")

        evento = EventoPartido.objects.filter(
            partido__external_id="900002", tipo_evento__codigo="SCORE"
        ).first()
        esperado = mock_fecha - datetime.timedelta(minutes=20)
        self.assertEqual(evento.plazo_cierre, esperado)

    # ── Idempotencia ─────────────────────────────────────────────────────────

    @patch("apps.tournaments.infrastructure.adapters.FootballDataOrgAdapter.fetch_fixtures")
    def test_idempotente_no_duplica(self, mock_fetch):
        mock_fetch.return_value = [
            _fixture("Mexico", "Germany", "LAST_32", "900003"),
        ]
        call_command("sync_knockout_matches")
        call_command("sync_knockout_matches")

        self.assertEqual(Match.objects.filter(external_id="900003").count(), 1)
        self.assertEqual(
            EventoPartido.objects.filter(partido__external_id="900003").count(), 2
        )

    # ── Dry-run no escribe ───────────────────────────────────────────────────

    @patch("apps.tournaments.infrastructure.adapters.FootballDataOrgAdapter.fetch_fixtures")
    def test_dry_run_no_escribe(self, mock_fetch):
        mock_fetch.return_value = [
            _fixture("Mexico", "Germany", "LAST_32", "900004"),
        ]
        call_command("sync_knockout_matches", dry_run=True)

        self.assertFalse(Match.objects.filter(external_id="900004").exists())
        self.assertFalse(EventoPartido.objects.filter(partido__external_id="900004").exists())

    # ── Partidos TBD se omiten ───────────────────────────────────────────────

    @patch("apps.tournaments.infrastructure.adapters.FootballDataOrgAdapter.fetch_fixtures")
    def test_tbd_se_omite(self, mock_fetch):
        mock_fetch.return_value = [
            MatchDTO(
                external_id="900005",
                home_team_name=None,
                away_team_name=None,
                home_team_code="", away_team_code="",
                match_date=datetime.datetime(2026, 6, 29, 18, 0, tzinfo=UTC),
                phase="LAST_32",
            )
        ]
        call_command("sync_knockout_matches")
        self.assertFalse(Match.objects.filter(external_id="900005").exists())

    # ── Equipo desconocido se omite ──────────────────────────────────────────

    @patch("apps.tournaments.infrastructure.adapters.FootballDataOrgAdapter.fetch_fixtures")
    def test_equipo_desconocido_se_omite(self, mock_fetch):
        mock_fetch.return_value = [
            _fixture("EquipoDesconocidoXYZ", "Germany", "LAST_32", "900006"),
        ]
        call_command("sync_knockout_matches")
        self.assertFalse(Match.objects.filter(external_id="900006").exists())

    # ── Fase desconocida se omite ─────────────────────────────────────────────

    @patch("apps.tournaments.infrastructure.adapters.FootballDataOrgAdapter.fetch_fixtures")
    def test_fase_desconocida_se_omite(self, mock_fetch):
        mock_fetch.return_value = [
            _fixture("Mexico", "Germany", "PLAY_OFF_ROUND", "900007"),
        ]
        call_command("sync_knockout_matches")
        self.assertFalse(Match.objects.filter(external_id="900007").exists())

    # ── Partidos de grupo se filtran ─────────────────────────────────────────

    @patch("apps.tournaments.infrastructure.adapters.FootballDataOrgAdapter.fetch_fixtures")
    def test_grupo_se_ignora(self, mock_fetch):
        mock_fetch.return_value = [
            _fixture("Mexico", "Germany", "GROUP_A", "900008"),
            _fixture("Mexico", "Germany", "GROUP_STAGE", "900009"),
        ]
        call_command("sync_knockout_matches")
        self.assertFalse(Match.objects.filter(external_id="900008").exists())
        self.assertFalse(Match.objects.filter(external_id="900009").exists())

    # ── Mapeo completo de fases ───────────────────────────────────────────────

    @patch("apps.tournaments.infrastructure.adapters.FootballDataOrgAdapter.fetch_fixtures")
    def test_mapeo_fases_knockout(self, mock_fetch):
        Fecha.objects.create(
            torneo=self.torneo, numero=6, nombre="Cuartos",
            fecha_inicio="2026-07-08", fecha_fin="2026-07-12",
        )
        Fecha.objects.create(
            torneo=self.torneo, numero=7, nombre="Semis",
            fecha_inicio="2026-07-14", fecha_fin="2026-07-15",
        )
        casos = [
            ("LAST_32",        "910001", 4),
            ("ROUND_OF_32",    "910002", 4),
            ("LAST_16",        "910003", 5),
            ("ROUND_OF_16",    "910004", 5),
            ("QUARTER_FINALS", "910005", 6),
            ("SEMI_FINALS",    "910006", 7),
            ("THIRD_PLACE",    "910007", 8),
            ("FINAL",          "910008", 8),
        ]
        mock_fetch.return_value = [
            _fixture("Mexico", "Germany", phase, ext_id)
            for phase, ext_id, _ in casos
        ]
        call_command("sync_knockout_matches")

        for phase, ext_id, fecha_num in casos:
            with self.subTest(phase=phase):
                match = Match.objects.filter(external_id=ext_id).first()
                self.assertIsNotNone(match, f"Partido {phase} no creado")
                self.assertEqual(match.fecha.numero, fecha_num)

    # ── Partido ya finalizado no se toca ─────────────────────────────────────

    @patch("apps.tournaments.infrastructure.adapters.FootballDataOrgAdapter.fetch_fixtures")
    def test_partido_finalizado_no_se_modifica(self, mock_fetch):
        otro_equipo = Team.objects.create(name="Bélgica", external_code="BEL")
        match = Match.objects.create(
            tournament=self.torneo,
            home_team=self.mex, away_team=self.ger,
            external_id="900011",
            match_date=datetime.datetime(2026, 6, 29, 18, 0, tzinfo=UTC),
            phase="LAST_32", fecha=self.fecha_r32,
            status="finished", home_score=2, away_score=2,
        )
        evento = EventoPartido.objects.create(
            partido=match, quiniela=self.quiniela, tipo_evento=self.tipo_score,
            plazo_cierre=datetime.datetime(2026, 6, 29, 17, 40, tzinfo=UTC),
            estado=EventoPartido.Estado.PUNTUADO, resultado="2-2",
        )

        # La API "corrige" el fixture con otro equipo y otra fecha —
        # nada de esto debe aplicarse porque el partido ya finalizó.
        mock_fetch.return_value = [
            _fixture(otro_equipo.name, "Germany", "LAST_32", "900011"),
        ]
        call_command("sync_knockout_matches")

        match.refresh_from_db()
        self.assertEqual(match.status, "finished")
        self.assertEqual(match.home_score, 2)
        self.assertEqual(match.away_score, 2)
        self.assertEqual(match.home_team, self.mex)  # no se pisó con "Bélgica"

        evento.refresh_from_db()
        self.assertEqual(evento.estado, EventoPartido.Estado.PUNTUADO)
        self.assertEqual(evento.resultado, "2-2")

    @patch("apps.tournaments.infrastructure.adapters.FootballDataOrgAdapter.fetch_fixtures")
    def test_partido_en_curso_no_se_modifica(self, mock_fetch):
        match = Match.objects.create(
            tournament=self.torneo,
            home_team=self.mex, away_team=self.ger,
            external_id="900012",
            match_date=datetime.datetime(2026, 6, 29, 18, 0, tzinfo=UTC),
            phase="LAST_32", fecha=self.fecha_r32,
            status="in_progress", home_score=1, away_score=0,
        )
        mock_fetch.return_value = [
            _fixture("Mexico", "Germany", "LAST_32", "900012"),
        ]
        call_command("sync_knockout_matches")

        match.refresh_from_db()
        self.assertEqual(match.status, "in_progress")
        self.assertEqual(match.home_score, 1)

    @patch("apps.tournaments.infrastructure.adapters.FootballDataOrgAdapter.fetch_fixtures")
    def test_dry_run_reporta_protegidos_sin_contarlos_como_creados(self, mock_fetch):
        Match.objects.create(
            tournament=self.torneo,
            home_team=self.mex, away_team=self.ger,
            external_id="900013",
            match_date=datetime.datetime(2026, 6, 29, 18, 0, tzinfo=UTC),
            phase="LAST_32", fecha=self.fecha_r32,
            status="finished", home_score=3, away_score=1,
        )
        mock_fetch.return_value = [
            _fixture("Mexico", "Germany", "LAST_32", "900013"),
        ]
        call_command("sync_knockout_matches", dry_run=True)

        # El dry-run no debe alterar nada (verificación adicional a las demás).
        match = Match.objects.get(external_id="900013")
        self.assertEqual(match.status, "finished")
        self.assertEqual(match.home_score, 3)

    # ── Filtro por quiniela-slug ─────────────────────────────────────────────

    @patch("apps.tournaments.infrastructure.adapters.FootballDataOrgAdapter.fetch_fixtures")
    def test_quiniela_slug_filtra_eventos(self, mock_fetch):
        otra_quiniela = Quiniela.objects.create(
            name="Otra Q", slug="otra-q",
            tournament=self.torneo, status="activa",
        )
        # No creamos EventoPartido de grupo para otra_quiniela → tipos = [] → 0 eventos

        mock_fetch.return_value = [
            _fixture("Mexico", "Germany", "LAST_32", "900010"),
        ]
        call_command("sync_knockout_matches", quiniela_slug="q-test")

        eventos = EventoPartido.objects.filter(partido__external_id="900010")
        quinielas_con_eventos = set(eventos.values_list("quiniela__slug", flat=True))
        self.assertIn("q-test", quinielas_con_eventos)
        self.assertNotIn("otra-q", quinielas_con_eventos)
