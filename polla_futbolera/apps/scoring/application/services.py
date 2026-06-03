from django.db import transaction
from django.db.models import Sum, Count, Q

from ..domain.entities import RankingEntrada
from ..domain.exceptions import EventoSinResultadoError
from ..infrastructure.models import PuntuacionEvento, ReglaPuntuacion, RankingFecha, RankingAcumulado
from apps.predictions.infrastructure.models import EventoPartido, PronosticoEvento


class ScoringService:

    def calcular_puntos_evento(self, evento_partido_id: int) -> list[PuntuacionEvento]:
        with transaction.atomic():
            evento = (
                EventoPartido.objects
                .select_related("tipo_evento")
                .get(id=evento_partido_id)
            )

            if not evento.resultado:
                raise EventoSinResultadoError(
                    f"El evento {evento_partido_id} no tiene resultado registrado"
                )

            pronosticos = PronosticoEvento.objects.filter(
                evento_partido=evento
            ).select_related("usuario")

            resultados = []
            for pronostico in pronosticos:
                codigo_acierto = self._evaluar(
                    evento.tipo_evento.codigo,
                    pronostico.valor,
                    evento.resultado,
                )
                puntos = self._resolver_puntos(
                    evento.tipo_evento_id,
                    evento.quiniela_id,
                    codigo_acierto,
                )
                puntuacion, _ = PuntuacionEvento.objects.update_or_create(
                    usuario_id=pronostico.usuario_id,
                    evento_partido=evento,
                    defaults={
                        "quiniela_id": evento.quiniela_id,
                        "valor_pronosticado": pronostico.valor,
                        "valor_resultado": evento.resultado,
                        "codigo_acierto": codigo_acierto,
                        "puntos": puntos,
                    },
                )
                resultados.append(puntuacion)

            EventoPartido.objects.filter(id=evento_partido_id).update(estado="puntuado")

            return resultados

    def _evaluar(self, codigo_tipo: str, valor_pronosticado: str, valor_resultado: str) -> str:
        if codigo_tipo == "SCORE":
            return self._evaluar_score(valor_pronosticado, valor_resultado)
        return "HIT" if valor_pronosticado == valor_resultado else "MISS"

    def _evaluar_score(self, pronostico: str, resultado: str) -> str:
        ph, pa = map(int, pronostico.split("-"))
        rh, ra = map(int, resultado.split("-"))

        if ph == rh and pa == ra:
            return "EXACT"

        def ganador(h, a):
            if h > a:
                return "H"
            if a > h:
                return "A"
            return "D"

        if (ph - pa) == (rh - ra) and ganador(ph, pa) == ganador(rh, ra):
            return "GOAL_DIFF"

        if ganador(ph, pa) == ganador(rh, ra):
            return "WINNER"

        return "MISS"

    def _resolver_puntos(self, tipo_evento_id: int, quiniela_id: int, codigo_acierto: str) -> int:
        regla = (
            ReglaPuntuacion.objects
            .filter(tipo_evento_id=tipo_evento_id, quiniela_id=quiniela_id, codigo_acierto=codigo_acierto)
            .first()
        )
        if regla is None:
            regla = (
                ReglaPuntuacion.objects
                .filter(tipo_evento_id=tipo_evento_id, quiniela__isnull=True, codigo_acierto=codigo_acierto)
                .first()
            )
        return regla.puntos if regla else 0


class RankingService:

    def recalcular_ranking_fecha(self, quiniela_id: int, fecha_id: int) -> None:
        with transaction.atomic():
            puntos_qs = (
                PuntuacionEvento.objects
                .filter(
                    quiniela_id=quiniela_id,
                    evento_partido__partido__fecha_id=fecha_id,
                )
                .values("usuario_id", "usuario__username")
                .annotate(puntos=Sum("puntos"))
                .order_by("-puntos")
            )

            ranking = self._asignar_posiciones(list(puntos_qs), campo_puntos="puntos")

            for pos, entrada in enumerate(ranking, start=1):
                RankingFecha.objects.update_or_create(
                    quiniela_id=quiniela_id,
                    fecha_id=fecha_id,
                    usuario_id=entrada["usuario_id"],
                    defaults={
                        "puntos": entrada["puntos"],
                        "posicion": entrada["posicion"],
                    },
                )

    def recalcular_ranking_acumulado(self, quiniela_id: int) -> None:
        with transaction.atomic():
            stats_qs = (
                PuntuacionEvento.objects
                .filter(quiniela_id=quiniela_id)
                .values("usuario_id", "usuario__username")
                .annotate(
                    puntos=Sum("puntos"),
                    exactos_total=Count("id", filter=Q(codigo_acierto="EXACT")),
                    aciertos_total=Count(
                        "id",
                        filter=Q(codigo_acierto__in=["EXACT", "GOAL_DIFF", "WINNER", "HIT"])
                    ),
                    fechas_jugadas=Count(
                        "evento_partido__partido__fecha_id", distinct=True
                    ),
                )
                .order_by("-puntos")
            )

            ranking = self._asignar_posiciones(list(stats_qs), campo_puntos="puntos")

            for entrada in ranking:
                RankingAcumulado.objects.update_or_create(
                    quiniela_id=quiniela_id,
                    usuario_id=entrada["usuario_id"],
                    defaults={
                        "puntos_total": entrada["puntos"] or 0,
                        "posicion": entrada["posicion"],
                        "fechas_jugadas": entrada["fechas_jugadas"],
                        "exactos_total": entrada["exactos_total"],
                        "aciertos_total": entrada["aciertos_total"],
                    },
                )

    def _asignar_posiciones(self, lista: list[dict], campo_puntos: str) -> list[dict]:
        sorted_list = sorted(lista, key=lambda x: x[campo_puntos] or 0, reverse=True)
        posicion = 1
        for i, entrada in enumerate(sorted_list):
            if i > 0 and (sorted_list[i - 1][campo_puntos] or 0) != (entrada[campo_puntos] or 0):
                posicion = i + 1
            entrada["posicion"] = posicion
        return sorted_list
