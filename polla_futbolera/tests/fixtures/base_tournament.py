import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone

from apps.predictions.infrastructure.models import (
    EventoPartido,
    PronosticoEvento,
    TipoEvento,
)
from apps.quinielas.infrastructure.models import Inscripcion, Quiniela
from apps.scoring.application.services import RankingService, ScoringService
from apps.scoring.infrastructure.models import ReglaPuntuacion
from apps.tournaments.infrastructure.models import Fecha, Match, Team, Tournament

User = get_user_model()


class TournamentScenario(TestCase):
    """
    Fixture base inmutable para toda la suite.

    setUpTestData crea una vez: torneo, quiniela, equipos, tipos de evento,
    reglas globales de puntuación, 4 jugadores y 1 moderador.

    Los datos mutables (Fecha, Match, EventoPartido, Inscripcion, PronosticoEvento)
    se crean en setUp o dentro de cada test mediante los helpers de instancia,
    y son revertidos automáticamente por el rollback de TestCase entre tests.
    """

    @classmethod
    def setUpTestData(cls):
        cls.grupo_jugador, _ = Group.objects.get_or_create(name="Jugador")
        cls.grupo_moderador, _ = Group.objects.get_or_create(name="Moderador")

        cls.torneo = Tournament.objects.create(
            name="Copa Test 2026",
            external_code="CT26",
            season="2026",
            status="active",
        )
        cls.quiniela = Quiniela.objects.create(
            name="Quiniela Test",
            slug="quiniela-test",
            tournament=cls.torneo,
        )

        cls.equipo_a = Team.objects.create(name="Equipo A", external_code="EA")
        cls.equipo_b = Team.objects.create(name="Equipo B", external_code="EB")

        # Las migraciones 0003_seed_tipo_eventos ya crean estos registros → get_or_create
        cls.tipo_score, _ = TipoEvento.objects.get_or_create(
            codigo="SCORE",
            defaults={"nombre": "Marcador exacto", "config": {}},
        )
        cls.tipo_winner, _ = TipoEvento.objects.get_or_create(
            codigo="WINNER",
            defaults={
                "nombre": "Ganador del partido",
                "config": {"choices": ["H", "D", "A"]},
            },
        )

        # Reglas ESPECÍFICAS de la quiniela de test con los puntos del diseño.
        # Se usan quiniela-specific (quiniela=cls.quiniela) para:
        #   1) no colisionar con las reglas globales de la migración (NULL ≠ NULL en PG)
        #   2) garantizar que _resolver_puntos las encuentre primero (FK quiniela tiene prioridad)
        # Puntos: EXACT=5, GOAL_DIFF=3, WINNER=1, MISS=0 | HIT=2, MISS=0
        for codigo, pts in [("EXACT", 5), ("GOAL_DIFF", 3), ("WINNER", 1), ("MISS", 0)]:
            ReglaPuntuacion.objects.create(
                tipo_evento=cls.tipo_score,
                quiniela=cls.quiniela,
                codigo_acierto=codigo,
                puntos=pts,
            )
        for codigo, pts in [("HIT", 2), ("MISS", 0)]:
            ReglaPuntuacion.objects.create(
                tipo_evento=cls.tipo_winner,
                quiniela=cls.quiniela,
                codigo_acierto=codigo,
                puntos=pts,
            )

        # jugador1..jugador4 en el grupo Jugador
        cls.jugadores = []
        for i in range(1, 5):
            u = User.objects.create_user(
                username=f"jugador{i}",
                email=f"jugador{i}@test.com",
                password="test1234",
            )
            u.groups.add(cls.grupo_jugador)
            cls.jugadores.append(u)

        cls.moderador = User.objects.create_user(
            username="moderador1",
            email="moderador@test.com",
            password="test1234",
        )
        cls.moderador.groups.add(cls.grupo_moderador)

    # ── Helpers para datos mutables ───────────────────────────────────────────

    def _crear_fecha(self, numero: int) -> Fecha:
        hoy = datetime.date.today()
        return Fecha.objects.create(
            torneo=self.torneo,
            numero=numero,
            nombre=f"Fecha {numero}",
            fecha_inicio=hoy,
            fecha_fin=hoy + datetime.timedelta(days=6),
        )

    def _crear_partido(
        self,
        fecha: Fecha,
        suffix: str = "a",
        *,
        status: str = "finished",
    ) -> Match:
        # status="finished"  → partido terminado (default para tests de scoring/ranking)
        # status="scheduled" → partido por jugarse, 4h adelante para que plazo_cierre
        #                       (+2h vía _crear_evento abierto=True) quede ANTES del partido
        offset_horas = 4 if status == "scheduled" else -2
        return Match.objects.create(
            tournament=self.torneo,
            home_team=self.equipo_a,
            away_team=self.equipo_b,
            external_id=f"match-f{fecha.numero}-{suffix}",
            match_date=timezone.now() + datetime.timedelta(hours=offset_horas),
            status=status,
            fecha=fecha,
        )

    def _crear_evento(
        self,
        partido: Match,
        tipo: TipoEvento,
        *,
        abierto: bool = False,
    ) -> EventoPartido:
        # abierto=True → plazo en el futuro (jugador puede pronosticar)
        # abierto=False → plazo en el pasado (evento cerrado para pronósticos)
        delta = datetime.timedelta(hours=2 if abierto else -2)
        return EventoPartido.objects.create(
            partido=partido,
            quiniela=self.quiniela,
            tipo_evento=tipo,
            plazo_cierre=timezone.now() + delta,
        )

    def _inscribir(self, jugador) -> Inscripcion:
        return Inscripcion.objects.create(jugador=jugador, quiniela=self.quiniela)

    def _inscribir_todos(self) -> None:
        for j in self.jugadores:
            self._inscribir(j)

    def _pronosticar(
        self,
        jugador,
        evento: EventoPartido,
        valor: str,
    ) -> PronosticoEvento:
        obj, _ = PronosticoEvento.objects.update_or_create(
            usuario=jugador,
            evento_partido=evento,
            defaults={"valor": valor},
        )
        return obj

    def _calcular_evento(self, evento: EventoPartido, resultado: str) -> list:
        evento.resultado = resultado
        evento.save(update_fields=["resultado"])
        return ScoringService().calcular_puntos_evento(evento.id)

    def _calcular_ranking_fecha(self, fecha: Fecha) -> None:
        RankingService().recalcular_ranking_fecha(self.quiniela.id, fecha.id)

    def _calcular_ranking_acumulado(self) -> None:
        RankingService().recalcular_ranking_acumulado(self.quiniela.id)
