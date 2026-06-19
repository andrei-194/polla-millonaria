import logging
import math
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger("observability")

_THROTTLE_MINUTOS = getattr(settings, "OBSERVABILITY_THROTTLE_MINUTOS", 30)
_ALERT_EMAILS = getattr(settings, "OBSERVABILITY_ALERT_EMAILS", [])


class AlertaService:
    """Envía email de alerta cuando una operación supera su umbral, con throttle."""

    def enviar_si_aplica(self, metric, umbral_ms: float) -> bool:
        if not _ALERT_EMAILS:
            return False

        from apps.observability.infrastructure.models import PerformanceMetric

        ventana = timezone.now() - timedelta(minutes=_THROTTLE_MINUTOS)
        ya_alertado = PerformanceMetric.objects.filter(
            label=metric.label,
            alerta_enviada=True,
            timestamp__gte=ventana,
        ).exists()

        if ya_alertado:
            return False

        self._enviar_email(metric, umbral_ms)
        metric.alerta_enviada = True
        metric.save(update_fields=["alerta_enviada"])
        return True

    def _enviar_email(self, metric, umbral_ms: float) -> None:
        ratio = metric.duration_ms / umbral_ms if umbral_ms else 0

        ctx_lines = []
        if metric.quiniela_id:
            ctx_lines.append(f"Quiniela ID : {metric.quiniela_id}")
        if metric.fecha_id:
            ctx_lines.append(f"Fecha ID    : {metric.fecha_id}")
        if metric.match_id:
            ctx_lines.append(f"Match ID    : {metric.match_id}")
        if metric.extra:
            ctx_lines.append(f"Contexto    : {metric.extra}")

        ctx_str = "\n".join(ctx_lines) if ctx_lines else "(sin contexto adicional)"
        railway_domain = getattr(settings, "RAILWAY_PUBLIC_DOMAIN", "")
        base_url = f"https://{railway_domain}" if railway_domain else "http://localhost:8000"

        cuerpo = (
            f"Proceso   : {metric.label}\n"
            f"Duración  : {metric.duration_ms:.0f} ms  "
            f"(umbral: {umbral_ms:.0f} ms — excedido {ratio:.1f}x)\n"
            f"Timestamp : {metric.timestamp:%Y-%m-%d %H:%M:%S} UTC\n"
            f"{ctx_str}\n\n"
            f"Ver métricas  : {base_url}/admin/observability/performancemetric/\n"
            f"Ver dashboard : {base_url}/observabilidad/\n\n"
            f"—\nSistema Toque (automático)"
        )

        send_mail(
            subject=f"[Toque] Alerta performance: {metric.label} tomó {metric.duration_ms:.0f}ms",
            message=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=_ALERT_EMAILS,
            fail_silently=True,
        )
        logger.warning(
            "Alerta performance enviada: %s %.0fms (umbral %.0fms)",
            metric.label, metric.duration_ms, umbral_ms,
        )


class ReporteService:
    """Genera y envía el reporte diario de performance por email."""

    def generar_y_enviar(self) -> None:
        if not _ALERT_EMAILS:
            logger.info("ReporteService: OBSERVABILITY_ALERT_EMAILS vacío — reporte omitido")
            return

        from apps.observability.infrastructure.models import PerformanceMetric

        ahora = timezone.now()
        hace_24h = ahora - timedelta(hours=24)
        hace_7d = ahora - timedelta(days=7)

        metricas_24h = list(
            PerformanceMetric.objects
            .filter(timestamp__gte=hace_24h)
            .values("label", "duration_ms", "success", "alerta_enviada")
        )

        if not metricas_24h:
            logger.info("ReporteService: sin métricas en 24h — reporte omitido")
            return

        por_label: dict[str, list[float]] = {}
        errores_por_label: dict[str, int] = {}
        alertas_total = 0

        for m in metricas_24h:
            label = m["label"]
            por_label.setdefault(label, []).append(m["duration_ms"])
            if not m["success"]:
                errores_por_label[label] = errores_por_label.get(label, 0) + 1
            if m["alerta_enviada"]:
                alertas_total += 1

        filas = []
        for label, duraciones in sorted(por_label.items()):
            p50 = self._percentil(duraciones, 50)
            p95 = self._percentil(duraciones, 95)
            max_d = max(duraciones)
            n = len(duraciones)
            filas.append(f"  {label:<42} {p50:>6.0f}ms  {p95:>6.0f}ms  {max_d:>6.0f}ms  {n:>4}")

        metricas_7d = list(
            PerformanceMetric.objects
            .filter(timestamp__gte=hace_7d, timestamp__lt=hace_24h)
            .values("label", "duration_ms")
        )
        tendencias = self._calcular_tendencias(por_label, metricas_7d)

        errores_str = (
            "\n".join(f"  {l}: {c} error(es)" for l, c in errores_por_label.items())
            if errores_por_label else "  Ninguno"
        )

        header = f"  {'Operación':<42} {'p50':>7}   {'p95':>7}   {'Max':>7}   {'N':>4}"
        sep = f"  {'-' * 42} {'-'*7}   {'-'*7}   {'-'*7}   {'-'*4}"
        tabla = "\n".join([header, sep] + filas)

        cuerpo = (
            f"RESUMEN PERFORMANCE — {ahora:%Y-%m-%d} (últimas 24h)\n\n"
            f"{tabla}\n\n"
            f"Alertas disparadas   : {alertas_total}\n"
            f"Errores              :\n{errores_str}\n\n"
            f"Tendencias p95 vs 7 días anteriores:\n{tendencias}\n\n"
            f"—\nSistema Toque (automático)"
        )

        send_mail(
            subject=f"[Toque] Reporte performance {ahora:%Y-%m-%d}",
            message=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=_ALERT_EMAILS,
            fail_silently=True,
        )
        logger.info("ReporteService: reporte diario enviado a %s", _ALERT_EMAILS)

    def _percentil(self, valores: list[float], p: int) -> float:
        if not valores:
            return 0.0
        sorted_v = sorted(valores)
        # ceil asegura que p95 de 10 valores dé el índice 9, no el 8
        idx = max(0, math.ceil(len(sorted_v) * p / 100) - 1)
        return sorted_v[idx]

    def _calcular_tendencias(self, actual: dict[str, list], metricas_7d: list) -> str:
        por_label_7d: dict[str, list[float]] = {}
        for m in metricas_7d:
            por_label_7d.setdefault(m["label"], []).append(m["duration_ms"])

        lineas = []
        for label, duraciones in sorted(actual.items()):
            p95_actual = self._percentil(duraciones, 95)
            if label not in por_label_7d:
                lineas.append(f"  {label}: nuevo (sin datos previos)")
                continue
            p95_prev = self._percentil(por_label_7d[label], 95)
            if p95_prev > 0:
                cambio = ((p95_actual - p95_prev) / p95_prev) * 100
                flecha = "↑" if cambio > 5 else ("↓" if cambio < -5 else "→")
                lineas.append(
                    f"  {label}: p95 {p95_prev:.0f}ms → {p95_actual:.0f}ms ({cambio:+.1f}% {flecha})"
                )

        return "\n".join(lineas) if lineas else "  Sin datos de comparación"
