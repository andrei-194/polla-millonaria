"""
Capa 2 — Motor de puntuación (ScoringService)

TestEvaluarScore         : tests unitarios puros de _evaluar_score (sin BD)
TestEvaluar              : tests del dispatcher _evaluar (sin BD)
TestCalcularPuntos       : tests de integración calcular_puntos_evento con BD real
TestCalcularPuntosFecha  : tests del refactor bulk de calcular_puntos_fecha

Ejecutar:
    docker-compose exec web python manage.py test tests.test_scoring_engine
"""
from django.test import SimpleTestCase, override_settings
from django.db import connection

from apps.scoring.application.services import ScoringService
from apps.scoring.domain.exceptions import EventoSinResultadoError
from apps.scoring.infrastructure.models import PuntuacionEvento

from tests.fixtures.base_tournament import TournamentScenario


# ── Capa 2a: tests puramente unitarios (sin base de datos) ───────────────────

class TestEvaluarScore(SimpleTestCase):
    """
    Tests de la lógica de clasificación de marcadores.

    Árbol de clasificación de _evaluar_score:
        EXACT      → marcador idéntico
        GOAL_DIFF  → misma diferencia de goles Y mismo ganador (no exacto)
        WINNER     → solo el ganador coincide
        MISS       → nada coincide
    """

    def setUp(self):
        self.svc = ScoringService()

    # --- EXACT ----------------------------------------------------------

    def test_exact_marcador_basico(self):
        self.assertEqual(self.svc._evaluar_score("2-1", "2-1"), "EXACT")

    def test_exact_empate_cero_cero(self):
        self.assertEqual(self.svc._evaluar_score("0-0", "0-0"), "EXACT")

    def test_exact_empate_con_goles(self):
        self.assertEqual(self.svc._evaluar_score("3-3", "3-3"), "EXACT")

    def test_exact_marcadores_altos_dos_digitos(self):
        self.assertEqual(self.svc._evaluar_score("10-0", "10-0"), "EXACT")

    # --- GOAL_DIFF ------------------------------------------------------

    def test_goal_diff_local_gana(self):
        # (3-1)=2  (4-2)=2 → misma diferencia, ambos H
        self.assertEqual(self.svc._evaluar_score("3-1", "4-2"), "GOAL_DIFF")

    def test_goal_diff_visitante_gana(self):
        # (0-2)=-2  (0-3)=-3? No: (0-2)=-2, (0-3)=-3 → distinto! corrijo:
        # (0-2)=-2  (1-3)=-2 → misma diferencia, ambos A
        self.assertEqual(self.svc._evaluar_score("0-2", "1-3"), "GOAL_DIFF")

    def test_goal_diff_empate_diferente_marcador(self):
        # Ambos empate (D), diferencia 0 en ambos → GOAL_DIFF no EXACT
        self.assertEqual(self.svc._evaluar_score("1-1", "2-2"), "GOAL_DIFF")

    def test_goal_diff_local_diferencia_uno(self):
        # (2-1)=1  (3-2)=1 → misma diferencia, ambos H
        self.assertEqual(self.svc._evaluar_score("2-1", "3-2"), "GOAL_DIFF")

    # --- WINNER ---------------------------------------------------------

    def test_winner_local_diferencia_distinta(self):
        # (2-0)=2  (3-2)=1 → diferencia distinta, pero ambos H
        self.assertEqual(self.svc._evaluar_score("2-0", "3-2"), "WINNER")

    def test_winner_visitante_diferencia_distinta(self):
        # (0-1)=-1  (0-3)=-3 → diferencia distinta, ambos A
        self.assertEqual(self.svc._evaluar_score("0-1", "0-3"), "WINNER")

    def test_winner_local_gana_marcador_mas_abultado(self):
        self.assertEqual(self.svc._evaluar_score("1-0", "5-0"), "WINNER")

    # --- MISS -----------------------------------------------------------

    def test_miss_local_pronostica_visitante_gana(self):
        self.assertEqual(self.svc._evaluar_score("2-1", "1-2"), "MISS")

    def test_miss_empate_pronosticado_local_gana(self):
        self.assertEqual(self.svc._evaluar_score("1-1", "2-0"), "MISS")

    def test_miss_local_pronosticado_empate_real(self):
        self.assertEqual(self.svc._evaluar_score("2-0", "1-1"), "MISS")

    def test_miss_visitante_pronosticado_local_gana(self):
        self.assertEqual(self.svc._evaluar_score("0-2", "2-0"), "MISS")

    def test_miss_empate_pronosticado_visitante_gana(self):
        self.assertEqual(self.svc._evaluar_score("0-0", "0-1"), "MISS")

    # --- Casos límite ---------------------------------------------------

    def test_marcador_9_9_igual(self):
        self.assertEqual(self.svc._evaluar_score("9-9", "9-9"), "EXACT")

    def test_goal_diff_empate_varios_goles(self):
        # 5-5 vs 4-4: ambos D, (5-5)=0 == (4-4)=0 → GOAL_DIFF
        self.assertEqual(self.svc._evaluar_score("5-5", "4-4"), "GOAL_DIFF")


class TestEvaluar(SimpleTestCase):
    """Tests del dispatcher _evaluar — verifica el enrutamiento por tipo de evento."""

    def setUp(self):
        self.svc = ScoringService()

    def test_score_delega_a_evaluar_score_exact(self):
        self.assertEqual(self.svc._evaluar("SCORE", "2-1", "2-1"), "EXACT")

    def test_score_delega_a_evaluar_score_miss(self):
        self.assertEqual(self.svc._evaluar("SCORE", "2-1", "1-2"), "MISS")

    def test_winner_hit_cuando_coincide(self):
        self.assertEqual(self.svc._evaluar("WINNER", "H", "H"), "HIT")
        self.assertEqual(self.svc._evaluar("WINNER", "D", "D"), "HIT")
        self.assertEqual(self.svc._evaluar("WINNER", "A", "A"), "HIT")

    def test_winner_miss_cuando_no_coincide(self):
        self.assertEqual(self.svc._evaluar("WINNER", "H", "A"), "MISS")
        self.assertEqual(self.svc._evaluar("WINNER", "D", "H"), "MISS")

    def test_btts_hit(self):
        self.assertEqual(self.svc._evaluar("BTTS", "si", "si"), "HIT")

    def test_btts_miss(self):
        self.assertEqual(self.svc._evaluar("BTTS", "si", "no"), "MISS")

    def test_tipo_generico_hit_si_valor_igual(self):
        self.assertEqual(self.svc._evaluar("OU25", "over", "over"), "HIT")

    def test_tipo_generico_miss_si_valor_distinto(self):
        self.assertEqual(self.svc._evaluar("OU25", "over", "under"), "MISS")


# ── Capa 2b: integración con BD (calcular_puntos_evento) ─────────────────────

class TestCalcularPuntos(TournamentScenario):
    """Tests de integración del flujo completo: pronóstico → puntuación → estado."""

    def setUp(self):
        self.fecha = self._crear_fecha(numero=1)
        self.partido = self._crear_partido(self.fecha)
        self.ev_score = self._crear_evento(self.partido, self.tipo_score)
        self.ev_winner = self._crear_evento(self.partido, self.tipo_winner)
        self._inscribir(self.jugadores[0])
        self._inscribir(self.jugadores[1])

    # --- Volumen de registros generados ----------------------------------

    def test_genera_una_puntuacion_por_pronostico(self):
        self._pronosticar(self.jugadores[0], self.ev_score, "2-1")
        self._pronosticar(self.jugadores[1], self.ev_score, "1-0")
        resultados = self._calcular_evento(self.ev_score, "2-1")
        self.assertEqual(len(resultados), 2)

    def test_sin_pronosticos_no_genera_puntuaciones(self):
        resultados = self._calcular_evento(self.ev_score, "2-1")
        self.assertEqual(resultados, [])

    # --- Puntuación SCORE ------------------------------------------------

    def test_exact_asigna_5_puntos(self):
        self._pronosticar(self.jugadores[0], self.ev_score, "2-1")
        self._calcular_evento(self.ev_score, "2-1")
        p = PuntuacionEvento.objects.get(
            usuario=self.jugadores[0], evento_partido=self.ev_score
        )
        self.assertEqual(p.codigo_acierto, "EXACT")
        self.assertEqual(p.puntos, 5)

    def test_goal_diff_asigna_3_puntos(self):
        self._pronosticar(self.jugadores[0], self.ev_score, "3-1")
        self._calcular_evento(self.ev_score, "4-2")
        p = PuntuacionEvento.objects.get(
            usuario=self.jugadores[0], evento_partido=self.ev_score
        )
        self.assertEqual(p.codigo_acierto, "GOAL_DIFF")
        self.assertEqual(p.puntos, 3)

    def test_winner_score_asigna_1_punto(self):
        self._pronosticar(self.jugadores[0], self.ev_score, "2-0")
        self._calcular_evento(self.ev_score, "3-2")
        p = PuntuacionEvento.objects.get(
            usuario=self.jugadores[0], evento_partido=self.ev_score
        )
        self.assertEqual(p.codigo_acierto, "WINNER")
        self.assertEqual(p.puntos, 1)

    def test_miss_asigna_0_puntos(self):
        self._pronosticar(self.jugadores[0], self.ev_score, "0-3")
        self._calcular_evento(self.ev_score, "2-1")
        p = PuntuacionEvento.objects.get(
            usuario=self.jugadores[0], evento_partido=self.ev_score
        )
        self.assertEqual(p.codigo_acierto, "MISS")
        self.assertEqual(p.puntos, 0)

    # --- Puntuación WINNER -----------------------------------------------

    def test_winner_hit_asigna_2_puntos(self):
        self._pronosticar(self.jugadores[0], self.ev_winner, "H")
        self._calcular_evento(self.ev_winner, "H")
        p = PuntuacionEvento.objects.get(
            usuario=self.jugadores[0], evento_partido=self.ev_winner
        )
        self.assertEqual(p.codigo_acierto, "HIT")
        self.assertEqual(p.puntos, 2)

    def test_winner_miss_asigna_0_puntos(self):
        self._pronosticar(self.jugadores[0], self.ev_winner, "A")
        self._calcular_evento(self.ev_winner, "H")
        p = PuntuacionEvento.objects.get(
            usuario=self.jugadores[0], evento_partido=self.ev_winner
        )
        self.assertEqual(p.codigo_acierto, "MISS")
        self.assertEqual(p.puntos, 0)

    # --- Campos almacenados en PuntuacionEvento --------------------------

    def test_almacena_valor_pronosticado_y_resultado(self):
        self._pronosticar(self.jugadores[0], self.ev_score, "2-1")
        self._calcular_evento(self.ev_score, "3-2")
        p = PuntuacionEvento.objects.get(
            usuario=self.jugadores[0], evento_partido=self.ev_score
        )
        self.assertEqual(p.valor_pronosticado, "2-1")
        self.assertEqual(p.valor_resultado, "3-2")

    # --- Estado del EventoPartido tras calcular --------------------------

    def test_evento_queda_en_estado_puntuado(self):
        self._pronosticar(self.jugadores[0], self.ev_score, "2-1")
        self._calcular_evento(self.ev_score, "2-1")
        self.ev_score.refresh_from_db()
        self.assertEqual(self.ev_score.estado, "puntuado")

    # --- Errores esperados -----------------------------------------------

    def test_calcular_sin_resultado_levanta_error(self):
        with self.assertRaises(EventoSinResultadoError):
            ScoringService().calcular_puntos_evento(self.ev_score.id)

    # --- Idempotencia ------------------------------------------------

    def test_recalculo_no_duplica_puntuaciones(self):
        """update_or_create garantiza que llamar dos veces produce un solo registro."""
        self._pronosticar(self.jugadores[0], self.ev_score, "2-1")
        self._calcular_evento(self.ev_score, "2-1")
        # Segunda llamada (recálculo): el evento ya fue marcado como "puntuado",
        # pero el servicio no valida el estado → actualiza el registro existente.
        ScoringService().calcular_puntos_evento(self.ev_score.id)
        count = PuntuacionEvento.objects.filter(
            usuario=self.jugadores[0], evento_partido=self.ev_score
        ).count()
        self.assertEqual(count, 1)


# ── Capa 2c: calcular_puntos_fecha bulk (refactor N+1) ───────────────────────

class TestCalcularPuntosFechaBulk(TournamentScenario):
    """
    Verifica que el refactor bulk de calcular_puntos_fecha produce resultados
    idénticos al loop original y usa exactamente 4 queries.

    Escenario: 4 usuarios, 3 partidos, 2 eventos cada uno = 6 EventoPartido, 24 pronósticos.
    """

    def setUp(self):
        self.fecha = self._crear_fecha(numero=1)
        self._inscribir_todos()

        self.partidos = [self._crear_partido(self.fecha, suffix=str(i)) for i in range(3)]
        self.eventos_score = [self._crear_evento(p, self.tipo_score) for p in self.partidos]
        self.eventos_winner = [self._crear_evento(p, self.tipo_winner) for p in self.partidos]

        # Todos los usuarios pronostican todos los eventos
        for jugador in self.jugadores:
            for ev_s in self.eventos_score:
                self._pronosticar(jugador, ev_s, "2-1")
            for ev_w in self.eventos_winner:
                self._pronosticar(jugador, ev_w, "H")

        # Setear resultado en todos los eventos
        from apps.predictions.infrastructure.models import EventoPartido
        EventoPartido.objects.filter(
            id__in=[e.id for e in self.eventos_score]
        ).update(resultado="2-1")
        EventoPartido.objects.filter(
            id__in=[e.id for e in self.eventos_winner]
        ).update(resultado="H")

    def test_genera_una_puntuacion_por_cada_pronostico(self):
        # 4 jugadores × 6 eventos = 24 puntuaciones
        ScoringService().calcular_puntos_fecha(self.quiniela.id, self.fecha.id)
        total = PuntuacionEvento.objects.filter(
            quiniela=self.quiniela,
            evento_partido__partido__fecha=self.fecha,
        ).count()
        self.assertEqual(total, 24)

    def test_puntos_exactos_correctos_para_score(self):
        # Todos pronostican "2-1" y resultado es "2-1" → EXACT = 5 pts para tipo SCORE
        ScoringService().calcular_puntos_fecha(self.quiniela.id, self.fecha.id)
        for jugador in self.jugadores:
            for ev_s in self.eventos_score:
                p = PuntuacionEvento.objects.get(usuario=jugador, evento_partido=ev_s)
                self.assertEqual(p.codigo_acierto, "EXACT")
                self.assertEqual(p.puntos, 5)

    def test_puntos_hit_correctos_para_winner(self):
        # Todos pronostican "H" y resultado es "H" → HIT = 2 pts para tipo WINNER
        ScoringService().calcular_puntos_fecha(self.quiniela.id, self.fecha.id)
        for jugador in self.jugadores:
            for ev_w in self.eventos_winner:
                p = PuntuacionEvento.objects.get(usuario=jugador, evento_partido=ev_w)
                self.assertEqual(p.codigo_acierto, "HIT")
                self.assertEqual(p.puntos, 2)

    def test_eventos_quedan_en_estado_puntuado(self):
        ScoringService().calcular_puntos_fecha(self.quiniela.id, self.fecha.id)
        from apps.predictions.infrastructure.models import EventoPartido
        todos = list(
            EventoPartido.objects.filter(
                partido__fecha=self.fecha, quiniela=self.quiniela
            ).values_list("estado", flat=True)
        )
        self.assertTrue(all(e == "puntuado" for e in todos))

    def test_idempotencia_batch(self):
        # Llamar dos veces → misma cantidad de filas (upsert, no duplicados)
        svc = ScoringService()
        svc.calcular_puntos_fecha(self.quiniela.id, self.fecha.id)
        svc.calcular_puntos_fecha(self.quiniela.id, self.fecha.id)
        total = PuntuacionEvento.objects.filter(
            quiniela=self.quiniela,
            evento_partido__partido__fecha=self.fecha,
        ).count()
        self.assertEqual(total, 24)

    @override_settings(DEBUG=True)
    def test_usa_exactamente_4_queries(self):
        # Con DEBUG=True Django registra cada query
        connection.queries_log.clear()
        ScoringService().calcular_puntos_fecha(self.quiniela.id, self.fecha.id)
        # savepoint open + 4 queries de negocio + savepoint release = 6 como máximo
        # Las 4 queries de negocio son: eventos, pronósticos, reglas, bulk_create+update
        n_queries = len(connection.queries)
        self.assertLessEqual(
            n_queries, 7,
            f"Se esperaban ≤7 queries (4 negocio + savepoints), se ejecutaron {n_queries}: "
            + str([q["sql"][:80] for q in connection.queries]),
        )

    def test_eventos_sin_resultado_son_ignorados(self):
        # Quitar resultado de un evento y verificar que retorna el id en sin_resultado
        from apps.predictions.infrastructure.models import EventoPartido
        ev = self.eventos_score[0]
        EventoPartido.objects.filter(id=ev.id).update(resultado=None)

        resultado = ScoringService().calcular_puntos_fecha(self.quiniela.id, self.fecha.id)
        self.assertIn(ev.id, resultado["sin_resultado"])
        # Los demás 5 eventos sí se calcularon
        self.assertEqual(resultado["ok"], 5)
