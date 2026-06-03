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
        """Calcula puntos para TODOS los eventos de una fecha en batch.
        Retorna {'ok': N, 'sin_resultado': [ids], 'total_pronósticos': N}."""
        eventos = (
            EventoPartido.objects
            .filter(partido__fecha_id=fecha_id, quiniela_id=quiniela_id)
            .exclude(estado="cancelado")
            .select_related("tipo_evento")
        )

        ok = 0
        sin_resultado = []

        for evento in eventos:
            if not evento.resultado:
                sin_resultado.append(evento.id)
                continue
            self.calcular_puntos_evento(evento.id)
            ok += 1

        return {"ok": ok, "sin_resultado": sin_resultado}

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
