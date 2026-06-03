"""
Capa 3 — Ciclo completo de una fecha (jornada)

Escenario fijo por cada test:
    - 4 jugadores inscritos en la quiniela
    - 1 fecha con 2 partidos
    - 4 eventos: SCORE + WINNER por partido
    - Resultado real: "2-1" (SCORE) / "H" (WINNER)

Puntos esperados por jugador (diseño deliberado):
    jugador1 → 14 pts  (EXACT×2 + HIT×2)
    jugador2 → 10 pts  (WINNER×1 + HIT×1 + EXACT×1 + HIT×1)
    jugador3 →  3 pts  (GOAL_DIFF×1 + MISS×3)
    jugador4 →  0 pts  (MISS×4)

Ejecutar:
    docker-compose exec web python manage.py test tests.test_fecha_completa
"""
from apps.scoring.infrastructure.models import RankingFecha

from tests.fixtures.base_tournament import TournamentScenario

# Resultado real para todos los tests de esta clase
RESULTADO_SCORE = "2-1"
RESULTADO_WINNER = "H"


class TestFechaCompletaCiclo(TournamentScenario):
    """
    Verifica que el ciclo pronóstico → cálculo → RankingFecha produce
    posiciones y puntos correctos para los distintos niveles de acierto.
    """

    def setUp(self):
        self._inscribir_todos()

        self.fecha1 = self._crear_fecha(numero=1)
        self.p1 = self._crear_partido(self.fecha1, suffix="a")
        self.p2 = self._crear_partido(self.fecha1, suffix="b")

        self.e1_score = self._crear_evento(self.p1, self.tipo_score)
        self.e1_winner = self._crear_evento(self.p1, self.tipo_winner)
        self.e2_score = self._crear_evento(self.p2, self.tipo_score)
        self.e2_winner = self._crear_evento(self.p2, self.tipo_winner)

    def _enviar_pronosticos_estandar(self):
        """
        Pronósticos diseñados para producir la distribución de puntos del encabezado.

        jugador1 (14 pts): acierta marcador exacto en ambos partidos.
        jugador2 (10 pts): WINNER en p1 SCORE, exacto en p2 SCORE.
        jugador3  (3 pts): GOAL_DIFF en p1 SCORE, MISS en el resto.
        jugador4  (0 pts): equivoca todo.

        Verificación manual:
            jugador3 p1 SCORE "1-0" vs "2-1": (1-0)=1, (2-1)=1, ambos H → GOAL_DIFF
            jugador2 p1 SCORE "3-1" vs "2-1": (3-1)=2, (2-1)=1, ambos H → WINNER
        """
        j1, j2, j3, j4 = self.jugadores

        # jugador1: todo exacto
        self._pronosticar(j1, self.e1_score, "2-1")
        self._pronosticar(j1, self.e1_winner, "H")
        self._pronosticar(j1, self.e2_score, "2-1")
        self._pronosticar(j1, self.e2_winner, "H")

        # jugador2: WINNER en p1, exacto en p2
        self._pronosticar(j2, self.e1_score, "3-1")   # WINNER (1pt)
        self._pronosticar(j2, self.e1_winner, "H")    # HIT    (2pt)
        self._pronosticar(j2, self.e2_score, "2-1")   # EXACT  (5pt)
        self._pronosticar(j2, self.e2_winner, "H")    # HIT    (2pt)

        # jugador3: GOAL_DIFF en p1, MISS en el resto
        self._pronosticar(j3, self.e1_score, "1-0")   # GOAL_DIFF (3pt)
        self._pronosticar(j3, self.e1_winner, "A")    # MISS       (0pt)
        self._pronosticar(j3, self.e2_score, "0-1")   # MISS       (0pt)
        self._pronosticar(j3, self.e2_winner, "A")    # MISS       (0pt)

        # jugador4: todo MISS
        self._pronosticar(j4, self.e1_score, "0-1")   # MISS (0pt)
        self._pronosticar(j4, self.e1_winner, "A")    # MISS (0pt)
        self._pronosticar(j4, self.e2_score, "0-1")   # MISS (0pt)
        self._pronosticar(j4, self.e2_winner, "A")    # MISS (0pt)

    def _calcular_todos_y_ranking(self):
        for ev in (self.e1_score, self.e2_score):
            self._calcular_evento(ev, RESULTADO_SCORE)
        for ev in (self.e1_winner, self.e2_winner):
            self._calcular_evento(ev, RESULTADO_WINNER)
        self._calcular_ranking_fecha(self.fecha1)

    # --- Ganador correcto -----------------------------------------------

    def test_ganador_de_fecha_es_jugador1(self):
        self._enviar_pronosticos_estandar()
        self._calcular_todos_y_ranking()

        lider = RankingFecha.objects.get(
            quiniela=self.quiniela, fecha=self.fecha1, posicion=1
        )
        self.assertEqual(lider.usuario, self.jugadores[0])

    def test_ganador_de_fecha_tiene_14_puntos(self):
        self._enviar_pronosticos_estandar()
        self._calcular_todos_y_ranking()

        lider = RankingFecha.objects.get(
            quiniela=self.quiniela, fecha=self.fecha1, posicion=1
        )
        self.assertEqual(lider.puntos, 14)

    def test_orden_completo_de_posiciones(self):
        self._enviar_pronosticos_estandar()
        self._calcular_todos_y_ranking()

        ranking = list(
            RankingFecha.objects.filter(
                quiniela=self.quiniela, fecha=self.fecha1
            ).order_by("posicion")
        )
        usuarios_ordenados = [r.usuario for r in ranking]
        self.assertEqual(usuarios_ordenados, list(self.jugadores))

    def test_puntos_de_cada_jugador_son_correctos(self):
        self._enviar_pronosticos_estandar()
        self._calcular_todos_y_ranking()

        esperados = {
            self.jugadores[0].id: 14,
            self.jugadores[1].id: 10,
            self.jugadores[2].id: 3,
            self.jugadores[3].id: 0,
        }
        for entrada in RankingFecha.objects.filter(
            quiniela=self.quiniela, fecha=self.fecha1
        ):
            self.assertEqual(
                entrada.puntos,
                esperados[entrada.usuario_id],
                msg=f"Puntos incorrectos para {entrada.usuario.username}",
            )

    def test_lider_tiene_mas_puntos_que_segundo(self):
        self._enviar_pronosticos_estandar()
        self._calcular_todos_y_ranking()

        ranking = list(
            RankingFecha.objects.filter(
                quiniela=self.quiniela, fecha=self.fecha1
            ).order_by("posicion")
        )
        self.assertGreater(ranking[0].puntos, ranking[1].puntos)

    # --- Empate de posiciones -------------------------------------------

    def test_empate_produce_misma_posicion(self):
        """Dos jugadores con igual puntaje comparten posición."""
        j1, j2 = self.jugadores[0], self.jugadores[1]

        # Ambos predicen exactamente lo mismo → mismos puntos
        for ev, valor in [
            (self.e1_score, "2-1"),
            (self.e1_winner, "H"),
            (self.e2_score, "0-0"),
            (self.e2_winner, "D"),
        ]:
            self._pronosticar(j1, ev, valor)
            self._pronosticar(j2, ev, valor)

        self._calcular_todos_y_ranking()

        r1 = RankingFecha.objects.get(
            quiniela=self.quiniela, fecha=self.fecha1, usuario=j1
        )
        r2 = RankingFecha.objects.get(
            quiniela=self.quiniela, fecha=self.fecha1, usuario=j2
        )
        self.assertEqual(r1.puntos, r2.puntos)
        self.assertEqual(r1.posicion, r2.posicion)

    # --- Jugador sin pronósticos ----------------------------------------

    def test_jugador_sin_pronosticos_no_aparece_en_ranking_fecha(self):
        """
        Un jugador inscrito que no envía ningún pronóstico no tiene
        PuntuacionEvento → no aparece en RankingFecha.
        """
        j1 = self.jugadores[0]

        # Solo j1 pronostica; j2, j3, j4 no envían nada
        self._pronosticar(j1, self.e1_score, "2-1")
        self._pronosticar(j1, self.e1_winner, "H")
        self._pronosticar(j1, self.e2_score, "2-1")
        self._pronosticar(j1, self.e2_winner, "H")

        self._calcular_todos_y_ranking()

        usuarios_en_ranking = set(
            RankingFecha.objects.filter(
                quiniela=self.quiniela, fecha=self.fecha1
            ).values_list("usuario_id", flat=True)
        )
        for j in self.jugadores[1:]:
            self.assertNotIn(j.id, usuarios_en_ranking)

    # --- Idempotencia del ranking ---------------------------------------

    def test_recalcular_dos_veces_produce_mismo_resultado(self):
        self._enviar_pronosticos_estandar()
        self._calcular_todos_y_ranking()
        self._calcular_ranking_fecha(self.fecha1)  # segunda llamada

        # El número de entradas no se duplica
        count = RankingFecha.objects.filter(
            quiniela=self.quiniela, fecha=self.fecha1
        ).count()
        self.assertEqual(count, 4)

        lider = RankingFecha.objects.get(
            quiniela=self.quiniela, fecha=self.fecha1, posicion=1
        )
        self.assertEqual(lider.usuario, self.jugadores[0])
