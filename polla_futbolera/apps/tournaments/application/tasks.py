"""
Tasks para django-q2 worker.
"""
import logging

logger = logging.getLogger("scoring.pipeline")


def run_sync_match_results(window_minutes: int = 300) -> dict:
    """
    Busca partidos finalizados en la ventana indicada y dispara el pipeline
    de scoring. Seguro de correr frecuentemente — termina en segundos si no
    hay candidatos o si FOOTBALL_API_KEY no está configurada.
    """
    from django.conf import settings
    from django.utils import timezone
    from datetime import timedelta
    from apps.tournaments.infrastructure.models import Match
    from apps.tournaments.infrastructure.adapters import FootballDataOrgAdapter
    from apps.tournaments.application.result_service import MatchResultService
    from apps.observability.application.tracking import PerfTracker

    api_key = getattr(settings, "FOOTBALL_API_KEY", "")
    if not api_key:
        logger.debug("run_sync_match_results: FOOTBALL_API_KEY no configurada — nada que hacer")
        return {"procesados": 0, "actualizados": 0}

    now = timezone.now()
    candidatos = Match.objects.filter(
        status__in=("scheduled", "in_progress"),
        match_date__lte=now - timedelta(minutes=90),
        match_date__gte=now - timedelta(minutes=window_minutes),
    )

    n_candidatos = candidatos.count()
    if not n_candidatos:
        logger.debug("run_sync_match_results: sin candidatos en ventana de %d min", window_minutes)
        return {"procesados": 0, "actualizados": 0}

    adapter = FootballDataOrgAdapter()
    service = MatchResultService()
    actualizados = 0
    errores_api = 0

    with PerfTracker("sync.match_results", umbral_ms=15000) as tracker:
        for match in candidatos.iterator():
            try:
                result_dto = adapter.fetch_results(match.external_id)
            except Exception:
                logger.exception("run_sync_match_results: error API para match %s", match.id)
                errores_api += 1
                continue

            if result_dto.status != "finished":
                continue

            match.home_score = result_dto.home_score
            match.away_score = result_dto.away_score
            match.status = "finished"
            match.save(update_fields=["home_score", "away_score", "status", "synced_at"])
            actualizados += 1
            logger.info(
                "run_sync_match_results: match %s actualizado %s-%s",
                match.id, result_dto.home_score, result_dto.away_score,
            )

        tracker.extra["n_candidatos"] = n_candidatos
        tracker.extra["n_actualizados"] = actualizados
        tracker.extra["n_errores_api"] = errores_api

    logger.info("run_sync_match_results: procesados=%d actualizados=%d", n_candidatos, actualizados)
    return {"procesados": n_candidatos, "actualizados": actualizados}
