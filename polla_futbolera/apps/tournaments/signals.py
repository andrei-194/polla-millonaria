import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger("scoring.pipeline")


def _handle_match_finished(match):
    from .application.result_service import MatchResultService
    try:
        result = MatchResultService().propagar_y_calcular(match.id)
        if result["eventos"] > 0:
            logger.info(
                "Signal match_finished: match=%s eventos=%s quinielas=%s",
                match.id, result["eventos"], result["quinielas"],
            )
    except Exception:
        logger.exception("Error en signal post_save para Match %s", match.id)


def register_signals():
    from .infrastructure.models import Match

    @receiver(post_save, sender=Match, weak=False)
    def on_match_saved(sender, instance, **kwargs):
        if (
            instance.status == "finished"
            and instance.home_score is not None
            and instance.away_score is not None
        ):
            _handle_match_finished(instance)
