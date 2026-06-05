"""
Tests de correctitud del pipeline de ranking a escala.

Verifica integridad matemática entre PuntuacionEvento, RankingFecha y RankingAcumulado.
No son tests de performance — son tests de consistencia.

Ejecutar:
    docker-compose exec web python manage.py test tests.test_ranking_escala
"""
from apps.scoring.application.services import RankingService, ScoringService
from apps.scoring.infrastructure.models import PuntuacionEvento, RankingAcumulado, RankingFecha
from apps.predictions.infrastructure.models import EventoPartido

from tests.fixtures.base_tournament import TournamentScenario


class TestRankingEscala(TournamentScenario):
    """
    Verifica correctitud del pipeline con 4 usuarios y múltiples fechas.
    Escenario base: 3 fechas, 2 partidos c/u, 2 eventos por partido, 4 jugadores.
    """

    def _setup_fechas_completas(self, n_fechas=3, n_partidos=2):
        """Crea n_fechas con n_partidos cada una, inscribe todos los jugadores,
        y hace que todos pronostiquen todos los eventos."""
        self._inscribir_todos()
        fechas = []
        for f_num in range(1, n_fechas + 1):
            fecha = self._crear_fecha(numero=f_num)
            partidos = [self._crear_partido(fecha, suffix=str(i)) for i in range(n_partidos)]
            eventos_s = [self._crear_evento(p, self.tipo_score) for p in partidos]
            eventos_w = [self._crear_evento(p, self.tipo_winner) for p in partidos]

            for jugador in self.jugadores:
                for ev in eventos_s:
                    self._pronosticar(jugador, ev, "2-1")
                for ev in eventos_w:
                    self._pronosticar(jugador, ev, "H")

            # Setear resultado
            EventoPartido.objects.filter(
                id__in=[e.id for e in eventos_s]
            ).update(resultado="2-1")
            EventoPartido.objects.filter(
                id__in=[e.id for e in eventos_w]
            ).update(resultado="H")

            fechas.append(fecha)

        return fechas

    def _run_pipeline(self, fechas):
        svc = ScoringService()
        ranking_svc = RankingService()

        fechas_quinielas = set()
        for fecha in fechas:
            svc.calcular_puntos_fecha(self.quiniela.id, fecha.id)
            fechas_quinielas.add((self.quiniela.id, fecha.id))

        for quiniela_id, fecha_id in fechas_quinielas:
            ranking_svc.recalcular_ranking_fecha(quiniela_id, fecha_id)

        ranking_svc.recalcular_ranking_acumulado(self.quiniela.id)

    def test_suma_puntos_fecha_es_consistente_entre_ranking_y_puntuaciones(self):
        fechas = self._setup_fechas_completas(n_fechas=3)
        self._run_pipeline(fechas)

        for fecha in fechas:
            for jugador in self.jugadores:
                puntos_raw = (
                    PuntuacionEvento.objects
                    .filter(
                        quiniela=self.quiniela,
                        usuario=jugador,
                        evento_partido__partido__fecha=fecha,
                    )
                    .aggregate(total=__import__("django.db.models", fromlist=["Sum"]).Sum("puntos"))
                )["total"] or 0

                ranking_fecha = RankingFecha.objects.get(
                    quiniela=self.quiniela, fecha=fecha, usuario=jugador
                )
                self.assertEqual(
                    puntos_raw,
                    ranking_fecha.puntos,
                    f"Discrepancia en fecha {fecha.numero} para {jugador.username}: "
                    f"PuntuacionEvento sum={puntos_raw}, RankingFecha.puntos={ranking_fecha.puntos}",
                )

    def test_puntos_acumulados_igual_suma_de_todas_las_fechas(self):
        from django.db.models import Sum
        fechas = self._setup_fechas_completas(n_fechas=3)
        self._run_pipeline(fechas)

        for jugador in self.jugadores:
            suma_fechas = (
                RankingFecha.objects
                .filter(quiniela=self.quiniela, usuario=jugador)
                .aggregate(total=Sum("puntos"))
            )["total"] or 0

            acumulado = RankingAcumulado.objects.get(quiniela=self.quiniela, usuario=jugador)
            self.assertEqual(
                suma_fechas,
                acumulado.puntos_total,
                f"{jugador.username}: suma RankingFecha={suma_fechas}, "
                f"RankingAcumulado.puntos_total={acumulado.puntos_total}",
            )

    def test_posiciones_sin_gaps_cuando_hay_empates(self):
        # Todos los jugadores pronostican igual → todos empatan → todos son posición 1
        fechas = self._setup_fechas_completas(n_fechas=1)
        self._run_pipeline(fechas)

        posiciones = list(
            RankingAcumulado.objects
            .filter(quiniela=self.quiniela)
            .values_list("posicion", flat=True)
        )
        # Todos empatan → todos son posición 1
        self.assertTrue(all(p == 1 for p in posiciones), f"Posiciones: {posiciones}")

    def test_posicion_siguiente_al_empate_es_n_mas_1(self):
        # Un jugador pronóstica diferente (MISS) mientras los otros 3 empatan
        self._inscribir_todos()
        fecha = self._crear_fecha(numero=1)
        partido = self._crear_partido(fecha)
        ev_score = self._crear_evento(partido, self.tipo_score)
        EventoPartido.objects.filter(id=ev_score.id).update(resultado="2-1")

        # jugadores[0] pronostica distinto → MISS
        self._pronosticar(self.jugadores[0], ev_score, "0-0")
        # los otros 3 pronostican exacto → EXACT
        for j in self.jugadores[1:]:
            self._pronosticar(j, ev_score, "2-1")

        ScoringService().calcular_puntos_fecha(self.quiniela.id, fecha.id)
        RankingService().recalcular_ranking_fecha(self.quiniela.id, fecha.id)
        RankingService().recalcular_ranking_acumulado(self.quiniela.id)

        # Los 3 que empatan son posición 1, el que pierde es posición 4 (no 2)
        pos_perdedor = RankingAcumulado.objects.get(
            quiniela=self.quiniela, usuario=self.jugadores[0]
        ).posicion
        self.assertEqual(pos_perdedor, 4)

        pos_ganadores = list(
            RankingAcumulado.objects.filter(
                quiniela=self.quiniela, usuario__in=self.jugadores[1:]
            ).values_list("posicion", flat=True)
        )
        self.assertTrue(all(p == 1 for p in pos_ganadores))

    def test_exactos_total_cuenta_correctamente(self):
        fechas = self._setup_fechas_completas(n_fechas=2, n_partidos=2)
        self._run_pipeline(fechas)

        for jugador in self.jugadores:
            # Cada fecha tiene 2 partidos × 1 evento SCORE con resultado EXACT
            exactos_en_bd = PuntuacionEvento.objects.filter(
                quiniela=self.quiniela, usuario=jugador, codigo_acierto="EXACT"
            ).count()
            acumulado = RankingAcumulado.objects.get(quiniela=self.quiniela, usuario=jugador)
            self.assertEqual(exactos_en_bd, acumulado.exactos_total)

    def test_fechas_jugadas_cuenta_fechas_distintas(self):
        # Crear 3 fechas pero solo 2 con pronósticos del jugador 0
        self._inscribir(self.jugadores[0])

        fechas_con_pron = []
        for f_num in range(1, 3):
            fecha = self._crear_fecha(numero=f_num)
            partido = self._crear_partido(fecha, suffix=str(f_num))
            ev = self._crear_evento(partido, self.tipo_score)
            EventoPartido.objects.filter(id=ev.id).update(resultado="2-1")
            self._pronosticar(self.jugadores[0], ev, "2-1")
            fechas_con_pron.append(fecha)

        # Fecha 3 sin pronósticos
        fecha_sin = self._crear_fecha(numero=3)
        partido_sin = self._crear_partido(fecha_sin, suffix="sin")
        ev_sin = self._crear_evento(partido_sin, self.tipo_score)
        EventoPartido.objects.filter(id=ev_sin.id).update(resultado="2-1")

        for fecha in fechas_con_pron:
            ScoringService().calcular_puntos_fecha(self.quiniela.id, fecha.id)
            RankingService().recalcular_ranking_fecha(self.quiniela.id, fecha.id)
        # fecha_sin se calcula (sin pronósticos de jugadores[0])
        ScoringService().calcular_puntos_fecha(self.quiniela.id, fecha_sin.id)
        RankingService().recalcular_ranking_acumulado(self.quiniela.id)

        acumulado = RankingAcumulado.objects.get(quiniela=self.quiniela, usuario=self.jugadores[0])
        self.assertEqual(acumulado.fechas_jugadas, 2)

    def test_pipeline_idempotente_en_recalculo(self):
        fechas = self._setup_fechas_completas(n_fechas=2)
        self._run_pipeline(fechas)

        # Capturar estado tras primer cálculo
        puntos_antes = {
            (ra.usuario_id, ra.posicion, ra.puntos_total)
            for ra in RankingAcumulado.objects.filter(quiniela=self.quiniela)
        }

        # Ejecutar pipeline de nuevo
        self._run_pipeline(fechas)

        puntos_despues = {
            (ra.usuario_id, ra.posicion, ra.puntos_total)
            for ra in RankingAcumulado.objects.filter(quiniela=self.quiniela)
        }

        self.assertEqual(puntos_antes, puntos_despues)

        # Verificar que no hay duplicados
        total_pun = PuntuacionEvento.objects.filter(quiniela=self.quiniela).count()
        n_eventos = EventoPartido.objects.filter(
            quiniela=self.quiniela,
            estado="puntuado",
        ).count()
        n_jugadores = len(self.jugadores)
        self.assertEqual(total_pun, n_eventos * n_jugadores)
