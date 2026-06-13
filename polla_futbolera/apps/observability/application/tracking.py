import logging
import time

logger = logging.getLogger("observability")


class PerfTracker:
    """
    Context manager para medir el tiempo de operaciones críticas.

    Uso básico:
        with PerfTracker("scoring.ranking_acumulado", umbral_ms=600, quiniela_id=q_id) as t:
            ...lógica pesada...
            t.extra["n_usuarios"] = len(entradas)

    - Guarda una PerformanceMetric en DB al salir del bloque.
    - Si duration_ms > umbral_ms, envía email de alerta (con throttle).
    - Nunca propaga excepciones propias (el pipeline no se ve afectado).
    """

    def __init__(self, label: str, umbral_ms: float = 500, **context):
        self.label = label
        self.umbral_ms = umbral_ms
        self.context = context
        self.extra: dict = {}
        self._t0: float | None = None
        self._metric = None

    def __enter__(self):
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self._t0) * 1000
        success = exc_type is None
        error_msg = str(exc_val)[:500] if exc_val else ""

        try:
            self._metric = _guardar_metrica(
                label=self.label,
                duration_ms=round(duration_ms, 2),
                success=success,
                error_msg=error_msg,
                context={**self.context, **self.extra},
            )
        except Exception:
            logger.exception("PerfTracker: error al guardar métrica '%s'", self.label)

        if success and self._metric is not None and duration_ms > self.umbral_ms:
            try:
                from apps.observability.application.services import AlertaService
                AlertaService().enviar_si_aplica(self._metric, self.umbral_ms)
            except Exception:
                logger.exception("PerfTracker: error al enviar alerta para '%s'", self.label)

        return False


def _guardar_metrica(label: str, duration_ms: float, success: bool, error_msg: str, context: dict):
    from apps.observability.infrastructure.models import PerformanceMetric

    ctx = dict(context)
    metric = PerformanceMetric.objects.create(
        label=label,
        duration_ms=duration_ms,
        success=success,
        error_msg=error_msg,
        quiniela_id=ctx.pop("quiniela_id", None),
        fecha_id=ctx.pop("fecha_id", None),
        match_id=ctx.pop("match_id", None),
        extra=ctx,
    )
    logger.debug("PerfTracker: %s %.0fms success=%s", label, duration_ms, success)
    return metric
