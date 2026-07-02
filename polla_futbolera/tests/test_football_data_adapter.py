"""
Tests del FootballDataOrgAdapter.fetch_results — parseo de marcadores.

Ejecutar:
    docker-compose exec web python manage.py test tests.test_football_data_adapter
"""
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.tournaments.infrastructure.adapters import FootballDataOrgAdapter


@override_settings(FOOTBALL_API_KEY="test-key", FOOTBALL_API_BASE_URL="https://example.test")
class TestFetchResults(SimpleTestCase):

    def setUp(self):
        self.adapter = FootballDataOrgAdapter()

    def _mock_response(self, score: dict, status: str = "FINISHED"):
        return {"status": status, "score": score}

    def test_partido_normal_usa_fulltime(self):
        data = self._mock_response({
            "duration": "REGULAR",
            "winner": "HOME_TEAM",
            "fullTime": {"home": 2, "away": 1},
        })
        with patch.object(FootballDataOrgAdapter, "get", return_value=data):
            result = self.adapter.fetch_results("123")
        self.assertEqual(result.home_score, 2)
        self.assertEqual(result.away_score, 1)

    def test_regulartime_null_sin_tiempo_extra_cae_a_fulltime(self):
        # Bug reproducido en producción: la API a veces manda regularTime
        # como {"home": null, "away": null} (dict presente pero sin datos).
        # Sin extraTime, fullTime SÍ es el marcador de los 90 minutos.
        data = self._mock_response({
            "duration": "REGULAR",
            "winner": "HOME_TEAM",
            "regularTime": {"home": None, "away": None},
            "fullTime": {"home": 3, "away": 2},
        })
        with patch.object(FootballDataOrgAdapter, "get", return_value=data):
            result = self.adapter.fetch_results("111")
        self.assertEqual(result.home_score, 3)
        self.assertEqual(result.away_score, 2)

    def test_regulartime_null_con_tiempo_extra_resta_extratime_de_fulltime(self):
        # Caso real de producción (external_id 537422, Bélgica vs Senegal):
        # regularTime viene en null, fullTime (3-2) YA incluye los goles del
        # alargue (extraTime: 1-0). El marcador reglamentario real fue 2-2,
        # no 3-2 — hay que restar extraTime, no usar fullTime tal cual.
        data = self._mock_response({
            "duration": "REGULAR",
            "winner": "HOME_TEAM",
            "regularTime": {"home": None, "away": None},
            "fullTime": {"home": 3, "away": 2},
            "extraTime": {"home": 1, "away": 0},
        })
        with patch.object(FootballDataOrgAdapter, "get", return_value=data):
            result = self.adapter.fetch_results("537422")
        self.assertEqual(result.home_score, 2)
        self.assertEqual(result.away_score, 2)
        self.assertEqual(result.home_score_et, 1)
        self.assertEqual(result.away_score_et, 0)

    def test_regulartime_con_valores_reales_tiene_prioridad(self):
        data = self._mock_response({
            "duration": "REGULAR",
            "winner": "AWAY_TEAM",
            "regularTime": {"home": 1, "away": 4},
            "fullTime": {"home": 1, "away": 4},
        })
        with patch.object(FootballDataOrgAdapter, "get", return_value=data):
            result = self.adapter.fetch_results("999")
        self.assertEqual(result.home_score, 1)
        self.assertEqual(result.away_score, 4)

    def test_penales_calcula_penalty_winner(self):
        data = self._mock_response({
            "duration": "PENALTY_SHOOTOUT",
            "winner": "AWAY_TEAM",
            "regularTime": {"home": 1, "away": 1},
            "fullTime": {"home": 1, "away": 1},
            "penalties": {"home": 3, "away": 4},
        })
        with patch.object(FootballDataOrgAdapter, "get", return_value=data):
            result = self.adapter.fetch_results("456")
        self.assertEqual(result.home_score, 1)
        self.assertEqual(result.away_score, 1)
        self.assertEqual(result.home_score_pen, 3)
        self.assertEqual(result.away_score_pen, 4)
        self.assertEqual(result.penalty_winner, "A")

    def test_sin_datos_de_marcador_devuelve_none(self):
        data = self._mock_response({"duration": "REGULAR", "winner": ""})
        with patch.object(FootballDataOrgAdapter, "get", return_value=data):
            result = self.adapter.fetch_results("789")
        self.assertIsNone(result.home_score)
        self.assertIsNone(result.away_score)
