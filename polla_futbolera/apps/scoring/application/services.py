from collections import defaultdict

from django.db import transaction
from django.db.models import Sum, Count, Q

from ..domain.entities import RankingEntrada
from ..domain.exceptions import EventoSinResultadoError
from ..infrastructure.models import PuntuacionEvento, ReglaPuntuacion, RankingFecha, RankingAcumulado
from apps.predictions.infrastructure.models import EventoPartido, PronosticoEvento


def _cargar_reglas(tipo_evento_id: int, quiniela_id: int) -> dict[str, int]:
    """Carga todas las reglas para un tipo+quiniela en un dict {codigo_acierto: puntos}.
    Reglas de quiniela específica tienen prioridad sobre globales."""
    reglas_qs = ReglaPuntuacion.objects.filter(
        tipo_evento_id=tipo_evento_id,
        quiniela_id__in=[quiniela_id, None],
    )
    resultado = {}
    globales = {}
    for r in reglas_qs:
        if r.quiniela_id is None:
            globales[r.codigo_acierto] = r.puntos
        else:
            resultado[r.codigo_acierto] = r.puntos
    # Globals fill in only what the quiniela-specific rules don't override
    for k, v in globales.items():
        resultado.setdefault(k, v)
    return resultado


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

            reglas = _cargar_reglas(evento.tipo_evento_id, evento.quiniela_id)

            puntuaciones = []
            for pronostico in pronosticos:
                codigo_acierto = self._evaluar(
                    evento.tipo_evento.codigo,
                    pronostico.valor,
                    evento.resultado,
                )
                puntos = reglas.get(codigo_acierto, 0)
                puntuaciones.append(PuntuacionEvento(
                    usuario_id=pronostico.usuario_id,
                    evento_partido=evento,
                    quiniela_id=evento.quiniela_id,
                    valor_pronosticado=pronostico.valor,
                    valor_resultado=evento.resultado,
                    codigo_acierto=codigo_acierto,
                    puntos=puntos,
                ))

            resultados = PuntuacionEvento.objects.bulk_create(
                puntuaciones,
                update_conflicts=True,
                unique_fields=["usuario_id", "evento_partido_id"],
                update_fields=[
                    "valor_pronosticado", "valor_resultado",
                    "codigo_acierto", "puntos", "calculado_en",
                ],
            )

            EventoPartido.objects.filter(id=evento_partido_id).update(estado="puntuado")

            return list(resultados)

    def calcular_puntos_fecha(self, quiniela_id: int, fecha_id: int) -> dict:
        """Calcula puntos para TODOS los eventos de una fecha en exactamente 4 queries.
        Retorna {'ok': N, 'sin_resultado': [ids]}."""
        with transaction.atomic():
            # Query 1: todos los eventos de la fecha
            eventos = list(
                EventoPartido.objects
                .filter(partido__fecha_id=fecha_id, quiniela_id=quiniela_id)
                .exclude(estado="cancelado")
                .select_related("tipo_evento")
            )

            eventos_con_resultado = [e for e in eventos if e.resultado]
            sin_resultado = [e.id for e in eventos if not e.resultado]

            if not eventos_con_resultado:
                return {"ok": 0, "sin_resultado": sin_resultado}

            evento_ids = [e.id for e in eventos_con_resultado]
            tipo_ids = {e.tipo_evento_id for e in eventos_con_resultado}

            # Query 2: todos los pronósticos de todos los eventos en una sola query
            pronosticos = list(
                PronosticoEvento.objects
                .filter(evento_partido_id__in=evento_ids)
                .values("usuario_id", "evento_partido_id", "valor")
            )

            pronosticos_por_evento: dict[int, list] = defaultdict(list)
            for p in pronosticos:
                pronosticos_por_evento[p["evento_partido_id"]].append(p)

            # Query 3: todas las reglas de todos los tipos involucrados
            reglas_qs = ReglaPuntuacion.objects.filter(
                tipo_evento_id__in=tipo_ids,
                quiniela_id__in=[quiniela_id, None],
            )
            reglas_globales: dict[tuple, int] = {}
            reglas_especificas: dict[tuple, int] = {}
            for r in reglas_qs:
                key = (r.tipo_evento_id, r.codigo_acierto)
                if r.quiniela_id is None:
                    reglas_globales[key] = r.puntos
                else:
                    reglas_especificas[key] = r.puntos
            reglas = {**reglas_globales, **reglas_especificas}

            # Evaluación en memoria — sin queries adicionales
            puntuaciones = []
            for evento in eventos_con_resultado:
                for pron in pronosticos_por_evento[evento.id]:
                    codigo_acierto = self._evaluar(
                        evento.tipo_evento.codigo,
                        pron["valor"],
                        evento.resultado,
                    )
                    puntos = reglas.get((evento.tipo_evento_id, codigo_acierto), 0)
                    puntuaciones.append(PuntuacionEvento(
                        usuario_id=pron["usuario_id"],
                        evento_partido_id=evento.id,
                        quiniela_id=quiniela_id,
                        valor_pronosticado=pron["valor"],
                        valor_resultado=evento.resultado,
                        codigo_acierto=codigo_acierto,
                        puntos=puntos,
                    ))

            # Query 4a: bulk_create de todos los PuntuacionEvento
            PuntuacionEvento.objects.bulk_create(
                puntuaciones,
                update_conflicts=True,
                unique_fields=["usuario_id", "evento_partido_id"],
                update_fields=[
                    "valor_pronosticado", "valor_resultado",
                    "codigo_acierto", "puntos", "calculado_en",
                ],
            )

            # Query 4b: UPDATE de estado en un solo statement
            EventoPartido.objects.filter(id__in=evento_ids).update(estado="puntuado")

            return {"ok": len(eventos_con_resultado), "sin_resultado": sin_resultado}

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

        gp = ganador(ph, pa)
        gr = ganador(rh, ra)

        if (ph - pa) == (rh - ra) and gp == gr:
            return "GOAL_DIFF"

        if gp == gr:
            return "WINNER"

        return "MISS"

    def _resolver_puntos(self, tipo_evento_id: int, quiniela_id: int, codigo_acierto: str) -> int:
        """Mantenido por compatibilidad con código externo. Preferir _cargar_reglas() en bulk."""
        reglas = _cargar_reglas(tipo_evento_id, quiniela_id)
        return reglas.get(codigo_acierto, 0)


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

            entradas = [
                RankingFecha(
                    quiniela_id=quiniela_id,
                    fecha_id=fecha_id,
                    usuario_id=entrada["usuario_id"],
                    puntos=entrada["puntos"],
                    posicion=entrada["posicion"],
                )
                for entrada in ranking
            ]
            RankingFecha.objects.bulk_create(
                entradas,
                update_conflicts=True,
                unique_fields=["quiniela_id", "fecha_id", "usuario_id"],
                update_fields=["puntos", "posicion", "calculado_en"],
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

            entradas = [
                RankingAcumulado(
                    quiniela_id=quiniela_id,
                    usuario_id=entrada["usuario_id"],
                    puntos_total=entrada["puntos"] or 0,
                    posicion=entrada["posicion"],
                    fechas_jugadas=entrada["fechas_jugadas"],
                    exactos_total=entrada["exactos_total"],
                    aciertos_total=entrada["aciertos_total"],
                )
                for entrada in ranking
            ]
            RankingAcumulado.objects.bulk_create(
                entradas,
                update_conflicts=True,
                unique_fields=["quiniela_id", "usuario_id"],
                update_fields=[
                    "puntos_total", "posicion", "fechas_jugadas",
                    "exactos_total", "aciertos_total", "calculado_en",
                ],
            )

    def _asignar_posiciones(self, lista: list[dict], campo_puntos: str) -> list[dict]:
        sorted_list = sorted(lista, key=lambda x: x[campo_puntos] or 0, reverse=True)
        posicion = 1
        for i, entrada in enumerate(sorted_list):
            if i > 0 and (sorted_list[i - 1][campo_puntos] or 0) != (entrada[campo_puntos] or 0):
                posicion = i + 1
            entrada["posicion"] = posicion
        return sorted_list
