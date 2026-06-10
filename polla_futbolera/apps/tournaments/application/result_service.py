import logging

from django.db import transaction

logger = logging.getLogger("scoring.pipeline")


class MatchResultService:
    """Propaga el resultado de un Match terminado a sus EventoPartido y
    dispara el pipeline de scoring + ranking."""

    def propagar_y_calcular(self, match_id: int) -> dict:
        """
        Idempotente: si los EventoPartido ya tienen resultado, retorna sin recalcular.
        Retorna {'eventos': N, 'quinielas': N}.
        """
        from apps.predictions.infrastructure.models import EventoPartido
        from apps.scoring.application.services import ScoringService, RankingService
        from ..infrastructure.models import Match

        with transaction.atomic():
            try:
                match = (
                    Match.objects
                    .select_for_update()
                    .get(id=match_id, status="finished")
                )
            except Match.DoesNotExist:
                logger.info("Match %s no encontrado o no está finished — se omite", match_id)
                return {"eventos": 0, "quinielas": 0}

            if match.home_score is None or match.away_score is None:
                logger.info("Match %s sin scores — se omite", match_id)
                return {"eventos": 0, "quinielas": 0}

            eventos = list(
                EventoPartido.objects
                .select_for_update()
                .select_related("tipo_evento")
                .filter(partido=match, resultado__isnull=True)
                .exclude(estado="cancelado")
            )

            if not eventos:
                logger.debug("Match %s: todos los EventoPartido ya tienen resultado", match_id)
                return {"eventos": 0, "quinielas": 0}

            h, a = match.home_score, match.away_score
            for evento in eventos:
                evento.resultado = self._traducir(evento.tipo_evento.codigo, h, a)
                evento.estado = EventoPartido.Estado.CERRADO

            EventoPartido.objects.bulk_update(eventos, ["resultado", "estado"])
            logger.info("Match %s: %d EventoPartido actualizados", match_id, len(eventos))

        if match.fecha_id is None:
            logger.warning("Match %s sin fecha FK — resultados propagados pero scoring omitido", match_id)
            return {"eventos": len(eventos), "quinielas": 0}

        quiniela_ids = list({e.quiniela_id for e in eventos})
        scoring_svc = ScoringService()
        ranking_svc = RankingService()

        for quiniela_id in quiniela_ids:
            try:
                scoring_svc.calcular_puntos_fecha(quiniela_id, match.fecha_id)
                ranking_svc.recalcular_ranking_fecha(quiniela_id, match.fecha_id)
                ranking_svc.recalcular_ranking_acumulado(quiniela_id)
            except Exception:
                logger.exception(
                    "Error en pipeline para quiniela=%s fecha=%s match=%s",
                    quiniela_id, match.fecha_id, match_id,
                )

        logger.info("Match %s: pipeline completado para %d quiniela(s)", match_id, len(quiniela_ids))
        return {"eventos": len(eventos), "quinielas": len(quiniela_ids)}

    @staticmethod
    def _traducir(codigo: str, home: int, away: int) -> str:
        if codigo == "SCORE":
            return f"{home}-{away}"
        if codigo == "WINNER":
            if home > away:
                return "H"
            if away > home:
                return "A"
            return "D"
        if codigo == "BTTS":
            return "si" if home > 0 and away > 0 else "no"
        if codigo == "OU25":
            return "over" if home + away > 2 else "under"
        # Tipo desconocido: devolver string del marcador como fallback
        logger.warning("TipoEvento desconocido: %s — usando fallback SCORE", codigo)
        return f"{home}-{away}"
