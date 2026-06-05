"""
Tasks para django-q2 worker.
Se ejecutan en proceso separado: python manage.py qcluster
"""
import json
import traceback

from apps.predictions.infrastructure.models import EventoPartido


def pipeline_ranking(job_id: int) -> None:
    """
    Task ejecutada por django-q2 worker.
    Corre el pipeline completo (scoring + ranking fecha + ranking acumulado)
    para todas las fechas del CalculoJob.
    """
    from ..infrastructure.models import CalculoJob
    from .services import ScoringService, RankingService

    job = CalculoJob.objects.get(id=job_id)
    job.estado = "RUNNING"
    job.save(update_fields=["estado", "actualizado_en"])

    scoring_svc = ScoringService()
    ranking_svc = RankingService()
    resumen = {"eventos_ok": 0, "sin_resultado": 0, "fechas": []}

    try:
        fechas_quinielas: set[tuple[int, int]] = set()

        for fecha in job.fechas.all():
            quiniela_ids = (
                EventoPartido.objects
                .filter(partido__fecha=fecha)
                .values_list("quiniela_id", flat=True)
                .distinct()
            )
            for quiniela_id in quiniela_ids:
                resultado = scoring_svc.calcular_puntos_fecha(quiniela_id, fecha.id)
                resumen["eventos_ok"] += resultado["ok"]
                resumen["sin_resultado"] += len(resultado["sin_resultado"])
                if resultado["ok"]:
                    fechas_quinielas.add((quiniela_id, fecha.id))

        quinielas = {q for q, _ in fechas_quinielas}
        for quiniela_id, fecha_id in fechas_quinielas:
            ranking_svc.recalcular_ranking_fecha(quiniela_id, fecha_id)
        for quiniela_id in quinielas:
            ranking_svc.recalcular_ranking_acumulado(quiniela_id)

        resumen["fechas_procesadas"] = len(fechas_quinielas)
        resumen["quinielas_procesadas"] = len(quinielas)

        job.estado = "DONE"
        job.resumen = json.dumps(resumen)
        job.save(update_fields=["estado", "resumen", "actualizado_en"])

    except Exception:
        job.estado = "ERROR"
        job.error_msg = traceback.format_exc()
        job.save(update_fields=["estado", "error_msg", "actualizado_en"])
        raise
