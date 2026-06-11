"""
Tests del MatchResultService.

TestTraducirResultado  : tests unitarios de la lógica de traducción (sin BD)
TestPropagaryCalcular  : tests de integración con BD real

Ejecutar:
    docker-compose exec web python manage.py test tests.test_result_service
"""
from django.test import SimpleTestCase, TestCase, override_settings

from apps.tournaments.application.result_service import MatchResultService
from tests.fixtures.base_tournament import TournamentScenario


# ── Capa 1: tests unitarios de traducción (sin BD) ───────────────────────────

class TestTraducirResultado(SimpleTestCase):

    def setUp(self):
        self.svc = MatchResultService()

    # ── SCORE ────────────────────────────────────────────────────────────────

    def test_score_victoria_local(self):
        self.assertEqual(self.svc._traducir("SCORE", 3, 1), "3-1")

    def test_score_victoria_visitante(self):
        self.assertEqual(self.svc._traducir("SCORE", 0, 2), "0-2")

    def test_score_empate(self):
        self.assertEqual(self.svc._traducir("SCORE", 1, 1), "1-1")

    def test_score_cero_a_cero(self):
        self.assertEqual(self.svc._traducir("SCORE", 0, 0), "0-0")

    # ── WINNER ───────────────────────────────────────────────────────────────

    def test_winner_local_gana(self):
        self.assertEqual(self.svc._traducir("WINNER", 2, 0), "H")

    def test_winner_visitante_gana(self):
        self.assertEqual(self.svc._traducir("WINNER", 1, 3), "A")

    def test_winner_empate(self):
        self.assertEqual(self.svc._traducir("WINNER", 0, 0), "D")

    def test_winner_empate_con_goles(self):
        self.assertEqual(self.svc._traducir("WINNER", 2, 2), "D")

    # ── BTTS ─────────────────────────────────────────────────────────────────

    def test_btts_ambos_anotaron(self):
        self.assertEqual(self.svc._traducir("BTTS", 1, 2), "yes")

    def test_btts_solo_local(self):
        self.assertEqual(self.svc._traducir("BTTS", 2, 0), "no")

    def test_btts_solo_visitante(self):
        self.assertEqual(self.svc._traducir("BTTS", 0, 1), "no")

    def test_btts_ninguno_anoto(self):
        self.assertEqual(self.svc._traducir("BTTS", 0, 0), "no")

    # ── OU25 ─────────────────────────────────────────────────────────────────

    def test_ou25_tres_goles_es_over(self):
        self.assertEqual(self.svc._traducir("OU25", 2, 1), "over")

    def test_ou25_cuatro_goles_es_over(self):
        self.assertEqual(self.svc._traducir("OU25", 4, 0), "over")

    def test_ou25_dos_goles_es_under(self):
        self.assertEqual(self.svc._traducir("OU25", 1, 1), "under")

    def test_ou25_cero_goles_es_under(self):
        self.assertEqual(self.svc._traducir("OU25", 0, 0), "under")

    def test_ou25_un_gol_es_under(self):
        self.assertEqual(self.svc._traducir("OU25", 1, 0), "under")


# ── Capa 2: tests de integración con BD ──────────────────────────────────────

class TestPropagarYCalcular(TournamentScenario):

    def setUp(self):
        self.svc = MatchResultService()
        self.fecha = self._crear_fecha(numero=1)
        self.match = self._crear_partido(self.fecha)
        self._inscribir_todos()

    def test_propagar_actualiza_evento_partido(self):
        from apps.predictions.infrastructure.models import EventoPartido
        self._crear_evento(self.match, self.tipo_score)

        self.match.home_score = 2
        self.match.away_score = 1
        self.match.status = "finished"
        self.match.save()

        evento = EventoPartido.objects.get(partido=self.match, tipo_evento=self.tipo_score)
        self.assertEqual(evento.resultado, "2-1")
        # El pipeline completo pasa el estado de cerrado → puntuado
        self.assertIn(evento.estado, (EventoPartido.Estado.CERRADO, EventoPartido.Estado.PUNTUADO))

    def test_propagar_score_y_winner(self):
        from apps.predictions.infrastructure.models import EventoPartido, TipoEvento
        tipo_btts, _ = TipoEvento.objects.get_or_create(
            codigo="BTTS", defaults={"nombre": "Ambos anotan", "config": {}}
        )
        tipo_ou25, _ = TipoEvento.objects.get_or_create(
            codigo="OU25", defaults={"nombre": "Más de 2.5", "config": {}}
        )
        for tipo in [self.tipo_score, self.tipo_winner, tipo_btts, tipo_ou25]:
            self._crear_evento(self.match, tipo)

        self.match.home_score = 1
        self.match.away_score = 2
        self.match.status = "finished"
        self.match.save()

        resultados = {
            e.tipo_evento.codigo: e.resultado
            for e in EventoPartido.objects.filter(partido=self.match)
        }
        self.assertEqual(resultados["SCORE"], "1-2")
        self.assertEqual(resultados["WINNER"], "A")
        self.assertEqual(resultados["BTTS"], "yes")
        self.assertEqual(resultados["OU25"], "over")   # 1+2=3 > 2.5

    def test_propagar_es_idempotente(self):
        self._crear_evento(self.match, self.tipo_score)

        self.match.home_score = 1
        self.match.away_score = 0
        self.match.status = "finished"
        self.match.save()

        result = self.svc.propagar_y_calcular(self.match.id)
        self.assertEqual(result["eventos"], 0, "Segunda llamada no debe re-procesar eventos")

    def test_propagar_omite_match_sin_scores(self):
        result = self.svc.propagar_y_calcular(self.match.id)
        self.assertEqual(result["eventos"], 0)

    def test_propagar_omite_match_no_finished(self):
        result = self.svc.propagar_y_calcular(self.match.id)
        self.assertEqual(result["eventos"], 0)
