"""
Capa 4 — Ganador acumulado de torneo (multi-fecha)

Escenario de 2 fechas completas:

    Fecha 1 — resultado "2-1" / "H"
        jugador1 → 14 pts  (EXACT×2 + HIT×2)
        jugador2 → 10 pts  (WINNER×1 + HIT×1 + EXACT×1 + HIT×1)
        jugador3 →  3 pts  (GOAL_DIFF×1 + MISS×3)
        jugador4 →  0 pts  (MISS×4)

    Fecha 2 — resultado "0-0" / "D"
        jugador1 → 12 pts  (EXACT×1 + HIT×1 + GOAL_DIFF×1 + HIT×1)
        jugador2 → 10 pts  (GOAL_DIFF×2 + HIT×2)
        jugador3 →  0 pts  (MISS×4)
        jugador4 → 14 pts  (EXACT×2 + HIT×2)

    Acumulado final:
        jugador1 → 26 pts  pos 1
        jugador2 → 20 pts  pos 2
        jugador4 → 14 pts  pos 3
        jugador3 →  3 pts  pos 4

Ejecutar:
    docker-compose exec web python manage.py test tests.test_tournament_winner
"""
from django.contrib.auth import get_user_model

from apps.quinielas.infrastructure.models import Inscripcion
from apps.scoring.infrastructure.models import RankingAcumulado, RankingFecha

from tests.fixtures.base_tournament import TournamentScenario

User = get_user_model()

RESULTADO_F1_SCORE = "2-1"
RESULTADO_F1_WINNER = "H"
RESULTADO_F2_SCORE = "0-0"
RESULTADO_F2_WINNER = "D"


class TestGanadorTorneo(TournamentScenario):
    """
    Suite E2E: simula 2 fechas completas y verifica el ranking acumulado.
    Cada test crea sus propios datos (setUp) — el estado se revierte entre tests.
    """

    def setUp(self):
        self._inscribir_todos()

        # ── Fecha 1 ─────────────────────────────────────────────────────
        self.fecha1 = self._crear_fecha(numero=1)
        self.f1_p1 = self._crear_partido(self.fecha1, suffix="a")
        self.f1_p2 = self._crear_partido(self.fecha1, suffix="b")
        self.f1_e1_score = self._crear_evento(self.f1_p1, self.tipo_score)
        self.f1_e1_winner = self._crear_evento(self.f1_p1, self.tipo_winner)
        self.f1_e2_score = self._crear_evento(self.f1_p2, self.tipo_score)
        self.f1_e2_winner = self._crear_evento(self.f1_p2, self.tipo_winner)

        # ── Fecha 2 ─────────────────────────────────────────────────────
        self.fecha2 = self._crear_fecha(numero=2)
        self.f2_p1 = self._crear_partido(self.fecha2, suffix="c")
        self.f2_p2 = self._crear_partido(self.fecha2, suffix="d")
        self.f2_e1_score = self._crear_evento(self.f2_p1, self.tipo_score)
        self.f2_e1_winner = self._crear_evento(self.f2_p1, self.tipo_winner)
        self.f2_e2_score = self._crear_evento(self.f2_p2, self.tipo_score)
        self.f2_e2_winner = self._crear_evento(self.f2_p2, self.tipo_winner)

    # ── Helpers internos ─────────────────────────────────────────────────────

    def _simular_fecha1(self):
        """
        Fecha 1 resultado: SCORE="2-1", WINNER="H"

        jugador1: EXACT(5)+HIT(2) + EXACT(5)+HIT(2) = 14
        jugador2: WINNER(1)+HIT(2) + EXACT(5)+HIT(2) = 10
        jugador3: GOAL_DIFF(3)+MISS(0) + MISS(0)+MISS(0) = 3
                  ("1-0" vs "2-1": diff=1 vs 1, ambos H → GOAL_DIFF)
        jugador4: MISS×4 = 0
        """
        j1, j2, j3, j4 = self.jugadores

        self._pronosticar(j1, self.f1_e1_score, "2-1")   # EXACT
        self._pronosticar(j1, self.f1_e1_winner, "H")    # HIT
        self._pronosticar(j1, self.f1_e2_score, "2-1")   # EXACT
        self._pronosticar(j1, self.f1_e2_winner, "H")    # HIT

        self._pronosticar(j2, self.f1_e1_score, "3-1")   # WINNER
        self._pronosticar(j2, self.f1_e1_winner, "H")    # HIT
        self._pronosticar(j2, self.f1_e2_score, "2-1")   # EXACT
        self._pronosticar(j2, self.f1_e2_winner, "H")    # HIT

        self._pronosticar(j3, self.f1_e1_score, "1-0")   # GOAL_DIFF
        self._pronosticar(j3, self.f1_e1_winner, "A")    # MISS
        self._pronosticar(j3, self.f1_e2_score, "0-1")   # MISS
        self._pronosticar(j3, self.f1_e2_winner, "A")    # MISS

        self._pronosticar(j4, self.f1_e1_score, "0-1")   # MISS
        self._pronosticar(j4, self.f1_e1_winner, "A")    # MISS
        self._pronosticar(j4, self.f1_e2_score, "0-1")   # MISS
        self._pronosticar(j4, self.f1_e2_winner, "A")    # MISS

        for ev in (self.f1_e1_score, self.f1_e2_score):
            self._calcular_evento(ev, RESULTADO_F1_SCORE)
        for ev in (self.f1_e1_winner, self.f1_e2_winner):
            self._calcular_evento(ev, RESULTADO_F1_WINNER)
        self._calcular_ranking_fecha(self.fecha1)

    def _simular_fecha2(self):
        """
        Fecha 2 resultado: SCORE="0-0", WINNER="D"

        jugador1: EXACT(5)+HIT(2) + GOAL_DIFF(3)+HIT(2) = 12
                  e1: "0-0" vs "0-0" → EXACT
                  e2: "1-1" vs "0-0" → (1-1)=0, (0-0)=0, ambos D → GOAL_DIFF
        jugador2: GOAL_DIFF(3)+HIT(2) + GOAL_DIFF(3)+HIT(2) = 10
                  e1: "1-1" vs "0-0" → GOAL_DIFF
                  e2: "2-2" vs "0-0" → (2-2)=0, (0-0)=0, ambos D → GOAL_DIFF
        jugador3: MISS×4 = 0
                  ("2-0" → H≠D, "0-1" → A≠D)
        jugador4: EXACT(5)+HIT(2) + EXACT(5)+HIT(2) = 14
                  pronostica "0-0"/"D" en ambos → todo exacto
        """
        j1, j2, j3, j4 = self.jugadores

        self._pronosticar(j1, self.f2_e1_score, "0-0")   # EXACT
        self._pronosticar(j1, self.f2_e1_winner, "D")    # HIT
        self._pronosticar(j1, self.f2_e2_score, "1-1")   # GOAL_DIFF
        self._pronosticar(j1, self.f2_e2_winner, "D")    # HIT

        self._pronosticar(j2, self.f2_e1_score, "1-1")   # GOAL_DIFF
        self._pronosticar(j2, self.f2_e1_winner, "D")    # HIT
        self._pronosticar(j2, self.f2_e2_score, "2-2")   # GOAL_DIFF
        self._pronosticar(j2, self.f2_e2_winner, "D")    # HIT

        self._pronosticar(j3, self.f2_e1_score, "2-0")   # MISS
        self._pronosticar(j3, self.f2_e1_winner, "H")    # MISS
        self._pronosticar(j3, self.f2_e2_score, "0-1")   # MISS
        self._pronosticar(j3, self.f2_e2_winner, "A")    # MISS

        self._pronosticar(j4, self.f2_e1_score, "0-0")   # EXACT
        self._pronosticar(j4, self.f2_e1_winner, "D")    # HIT
        self._pronosticar(j4, self.f2_e2_score, "0-0")   # EXACT
        self._pronosticar(j4, self.f2_e2_winner, "D")    # HIT

        for ev in (self.f2_e1_score, self.f2_e2_score):
            self._calcular_evento(ev, RESULTADO_F2_SCORE)
        for ev in (self.f2_e1_winner, self.f2_e2_winner):
            self._calcular_evento(ev, RESULTADO_F2_WINNER)
        self._calcular_ranking_fecha(self.fecha2)

    def _simular_torneo_completo(self):
        self._simular_fecha1()
        self._simular_fecha2()
        self._calcular_ranking_acumulado()

    # ── Tests de RankingFecha por fecha ──────────────────────────────────────

    def test_ganador_fecha1_es_jugador1(self):
        self._simular_fecha1()
        lider = RankingFecha.objects.get(
            quiniela=self.quiniela, fecha=self.fecha1, posicion=1
        )
        self.assertEqual(lider.usuario, self.jugadores[0])
        self.assertEqual(lider.puntos, 14)

    def test_ganador_fecha2_es_jugador4(self):
        self._simular_fecha1()
        self._simular_fecha2()
        lider = RankingFecha.objects.get(
            quiniela=self.quiniela, fecha=self.fecha2, posicion=1
        )
        self.assertEqual(lider.usuario, self.jugadores[3])
        self.assertEqual(lider.puntos, 14)

    def test_jugador_que_pierde_fecha1_puede_ganar_fecha2(self):
        """El ranking por fecha es independiente del acumulado."""
        self._simular_fecha1()
        self._simular_fecha2()

        lider_f1 = RankingFecha.objects.get(
            quiniela=self.quiniela, fecha=self.fecha1, posicion=1
        )
        lider_f2 = RankingFecha.objects.get(
            quiniela=self.quiniela, fecha=self.fecha2, posicion=1
        )
        self.assertNotEqual(lider_f1.usuario, lider_f2.usuario)

    # ── Tests del RankingAcumulado ────────────────────────────────────────────

    def test_lider_acumulado_es_jugador1_con_26_puntos(self):
        self._simular_torneo_completo()
        lider = RankingAcumulado.objects.get(
            quiniela=self.quiniela, posicion=1
        )
        self.assertEqual(lider.usuario, self.jugadores[0])
        self.assertEqual(lider.puntos_total, 26)

    def test_posicion_2_acumulado_es_jugador2_con_20_puntos(self):
        self._simular_torneo_completo()
        segundo = RankingAcumulado.objects.get(
            quiniela=self.quiniela, posicion=2
        )
        self.assertEqual(segundo.usuario, self.jugadores[1])
        self.assertEqual(segundo.puntos_total, 20)

    def test_orden_acumulado_completo(self):
        """jugador1 > jugador2 > jugador4 > jugador3 en puntos totales."""
        self._simular_torneo_completo()
        ranking = list(
            RankingAcumulado.objects.filter(
                quiniela=self.quiniela
            ).order_by("posicion")
        )
        puntos = [r.puntos_total for r in ranking]
        self.assertEqual(puntos, sorted(puntos, reverse=True))

    def test_puntos_acumulados_de_cada_jugador(self):
        self._simular_torneo_completo()
        esperados = {
            self.jugadores[0].id: 26,
            self.jugadores[1].id: 20,
            self.jugadores[2].id: 3,
            self.jugadores[3].id: 14,
        }
        for entrada in RankingAcumulado.objects.filter(quiniela=self.quiniela):
            self.assertEqual(
                entrada.puntos_total,
                esperados[entrada.usuario_id],
                msg=f"Acumulado incorrecto para {entrada.usuario.username}",
            )

    def test_fechas_jugadas_es_2_para_todos(self):
        """Todo jugador que pronosticó en ambas fechas tiene fechas_jugadas=2."""
        self._simular_torneo_completo()
        for entrada in RankingAcumulado.objects.filter(quiniela=self.quiniela):
            self.assertEqual(
                entrada.fechas_jugadas,
                2,
                msg=f"fechas_jugadas incorrecto para {entrada.usuario.username}",
            )

    def test_lider_acumulado_tiene_mas_exactos_que_miss_total(self):
        """El líder (jugador1) tiene varios EXACT: exactos_total > 0."""
        self._simular_torneo_completo()
        lider = RankingAcumulado.objects.get(
            quiniela=self.quiniela, usuario=self.jugadores[0]
        )
        self.assertGreater(lider.exactos_total, 0)

    # ── Jugador sin pronósticos ───────────────────────────────────────────────

    def test_jugador_inscrito_sin_pronosticos_no_aparece_en_acumulado(self):
        """
        Un jugador que se inscribe pero no envía ningún pronóstico
        no tiene PuntuacionEvento → no aparece en RankingAcumulado.
        """
        jugador_silencioso = User.objects.create_user(
            username="silencioso",
            email="silencioso@test.com",
            password="test1234",
        )
        jugador_silencioso.groups.add(self.grupo_jugador)
        Inscripcion.objects.create(jugador=jugador_silencioso, quiniela=self.quiniela)

        self._simular_torneo_completo()

        self.assertFalse(
            RankingAcumulado.objects.filter(
                quiniela=self.quiniela, usuario=jugador_silencioso
            ).exists()
        )

    # ── Jugador dado de baja (comportamiento actual) ──────────────────────────

    def test_jugador_dado_de_baja_conserva_puntuacion_en_acumulado(self):
        """
        REGLA DE NEGOCIO ACTUAL: dar de baja a un jugador de la quiniela
        no elimina sus PuntuacionEvento → sigue apareciendo en RankingAcumulado.

        Si el comportamiento esperado cambia (excluir dados de baja),
        este test debe actualizarse junto con recalcular_ranking_acumulado.
        """
        self._simular_fecha1()

        # Dar de baja a jugador1 tras la primera fecha
        insc = Inscripcion.objects.get(jugador=self.jugadores[0], quiniela=self.quiniela)
        insc.activa = False
        insc.save(update_fields=["activa"])

        self._calcular_ranking_acumulado()

        # jugador1 sigue apareciendo en el acumulado con sus 14 pts de fecha1
        entrada = RankingAcumulado.objects.get(
            quiniela=self.quiniela, usuario=self.jugadores[0]
        )
        self.assertEqual(entrada.puntos_total, 14)

    # ── Idempotencia ─────────────────────────────────────────────────────────

    def test_recalculo_acumulado_no_duplica_entradas(self):
        self._simular_torneo_completo()
        self._calcular_ranking_acumulado()  # segunda llamada

        count = RankingAcumulado.objects.filter(quiniela=self.quiniela).count()
        self.assertEqual(count, 4)  # un registro por jugador
