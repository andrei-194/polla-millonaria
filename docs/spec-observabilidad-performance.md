# Spec: Sistema de Observabilidad de Performance
**Estado:** Propuesto  
**Fecha:** 2026-06-13  
**Contexto:** Django 5.2 + PostgreSQL + Railway + django-q2

---

## 1. Problema

Los logs de Railway muestran picos esporádicos de ~500 ms en operaciones de scoring/ranking. Con el crecimiento de usuarios y torneos simultáneos, el pipeline `calcular_puntos_fecha → recalcular_ranking_acumulado` puede degradarse significativamente sin que tengamos visibilidad. Hoy no existe ningún mecanismo que nos avise cuando una operación supera un umbral de tiempo, ni forma de ver tendencias históricas.

**Riesgo concreto:**
- `recalcular_ranking_acumulado` con 1 000+ usuarios escala linealmente (GROUP BY + COUNT DISTINCT + bulk_upsert)
- `run_sync_match_results` acumula latencia de API externa (football-data.org) × número de partidos en ventana
- Días de partido (varios partidos en paralelo) disparan múltiples pipelines concurrentes sobre el mismo worker django-q2

---

## 2. Objetivo

Instrumentar los procesos críticos del sistema para:

1. **Medir** el tiempo de ejecución de cada operación clave
2. **Persisitir** las métricas en la base de datos existente (sin infraestructura adicional)
3. **Alertar** por email cuando una operación supere un umbral (vía SendGrid ya integrado)
4. **Visualizar** tendencias con un dashboard interno ligero (Django Admin + vistas dedicadas)
5. **Exportar** opcionalmente a Grafana Cloud (free tier) para gráficas históricas

Todo con **costo $0** de infraestructura adicional.

---

## 3. Arquitectura de la Solución

```
Proceso Django / django-q2 task
        │
        ▼
@track_performance(label="...", umbral_ms=500)
        │  (decorator Python puro)
        │
        ├─── mide wall-clock time
        ├─── captura metadatos (quiniela_id, fecha_id, usuarios, registros afectados)
        ├─── escribe PerformanceMetric (async, no bloquea el pipeline)
        │
        └─── si tiempo > umbral_ms
                │
                └─→ dispatch_email_alerta() ← SendGrid (ya integrado)
                        - Asunto: "[Toque] Alerta performance: <label> tomó Xms"
                        - Cuerpo: metadatos + contexto + link al admin
```

```
Grafana Cloud (opcional, free tier)
        ▲
        │  HTTP push cada 5 min
        │
management command: export_metrics_grafana
  lee PerformanceMetric de las últimas N horas
  formatea en OpenMetrics / Prometheus Exposition Format
  hace POST a Grafana Cloud (Prometheus Remote Write endpoint)
```

---

## 4. Procesos a Instrumentar

| Proceso | Label | Umbral alerta | Metadatos adicionales |
|---------|-------|--------------|----------------------|
| `ScoringService.calcular_puntos_fecha` | `scoring.calcular_puntos_fecha` | 800 ms | quiniela_id, fecha_id, n_usuarios, n_eventos, n_puntuaciones |
| `RankingService.recalcular_ranking_fecha` | `scoring.ranking_fecha` | 300 ms | quiniela_id, fecha_id, n_usuarios |
| `RankingService.recalcular_ranking_acumulado` | `scoring.ranking_acumulado` | 600 ms | quiniela_id, n_usuarios, n_fechas |
| `MatchResultService.propagar_y_calcular` | `scoring.pipeline_completo` | 2 000 ms | match_id, n_quinielas |
| `run_sync_match_results` | `sync.match_results` | 15 000 ms | n_candidatos, n_actualizados, n_errores_api |
| Vistas leaderboard (middleware) | `view.leaderboard` | 400 ms | quiniela_id, n_usuarios |

---

## 5. Modelo de Datos

```python
# apps/observability/models.py

class PerformanceMetric(models.Model):
    """Registro de tiempo de ejecución de operaciones críticas."""

    label        = models.CharField(max_length=100, db_index=True)
    duration_ms  = models.FloatField()
    timestamp    = models.DateTimeField(auto_now_add=True, db_index=True)

    # Contexto del proceso
    quiniela_id  = models.IntegerField(null=True, blank=True, db_index=True)
    fecha_id     = models.IntegerField(null=True, blank=True)
    match_id     = models.IntegerField(null=True, blank=True)
    extra        = models.JSONField(default=dict, blank=True)  # n_usuarios, n_registros, etc.

    # Resultado
    success      = models.BooleanField(default=True)
    error_msg    = models.TextField(blank=True)
    alerta_enviada = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["label", "timestamp"]),
            models.Index(fields=["timestamp"]),
        ]
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.label} | {self.duration_ms:.0f}ms | {self.timestamp:%Y-%m-%d %H:%M}"
```

**Retención:** 30 días (management command de limpieza programado en cron).

---

## 6. Decorador de Instrumentación

```python
# apps/observability/tracking.py

import time, logging
from functools import wraps
from django.db import transaction

logger = logging.getLogger("observability")

def track_performance(label, umbral_ms=500, **ctx_defaults):
    """
    @track_performance("scoring.calcular_puntos_fecha", umbral_ms=800)
    def calcular_puntos_fecha(self, quiniela_id, fecha_id): ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            ctx = {**ctx_defaults}
            t0 = time.perf_counter()
            error_msg = ""
            success = True
            result = None
            try:
                result = fn(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_msg = str(e)
                raise
            finally:
                duration_ms = (time.perf_counter() - t0) * 1000
                _guardar_metrica(label, duration_ms, success, error_msg, ctx)
                if duration_ms > umbral_ms:
                    _enviar_alerta(label, duration_ms, umbral_ms, ctx)
        return wrapper
    return decorator


def _guardar_metrica(label, duration_ms, success, error_msg, ctx):
    try:
        from apps.observability.models import PerformanceMetric
        PerformanceMetric.objects.create(
            label=label,
            duration_ms=duration_ms,
            success=success,
            error_msg=error_msg,
            quiniela_id=ctx.get("quiniela_id"),
            fecha_id=ctx.get("fecha_id"),
            match_id=ctx.get("match_id"),
            extra={k: v for k, v in ctx.items()
                   if k not in ("quiniela_id", "fecha_id", "match_id")},
        )
    except Exception:
        logger.exception("Error al guardar PerformanceMetric")


def _enviar_alerta(label, duration_ms, umbral_ms, ctx):
    try:
        from apps.observability.tasks import enviar_alerta_performance
        enviar_alerta_performance.delay(label, duration_ms, umbral_ms, ctx)
    except Exception:
        logger.exception("Error al despachar alerta de performance")
```

**Uso en servicios existentes:**

```python
# apps/scoring/application/services.py

from apps.observability.tracking import track_performance

class ScoringService:
    @track_performance("scoring.calcular_puntos_fecha", umbral_ms=800)
    def calcular_puntos_fecha(self, quiniela_id, fecha_id):
        ...

class RankingService:
    @track_performance("scoring.ranking_acumulado", umbral_ms=600)
    def recalcular_ranking_acumulado(self, quiniela_id):
        ...
```

---

## 7. Alertas por Email

**Formato del email de alerta:**

```
Asunto: [Toque] ⚠️ Performance: scoring.ranking_acumulado tomó 1 247 ms

Proceso: scoring.ranking_acumulado
Duración: 1 247 ms  (umbral: 600 ms — excedido 2.1x)
Timestamp: 2026-06-13 21:34:07 UTC
Quiniela ID: 3
Contexto: {"n_usuarios": 412, "n_fechas": 8}

Ver métricas: https://toque.up.railway.app/admin/observability/performancemetric/

—
Sistema Toque (automático)
```

**Throttle:** máximo 1 alerta por (label, quiniela_id) cada 30 minutos para evitar spam.

---

## 8. Reporte Diario por Email

Un management command que corre a las 08:00 UTC vía cron django-q2:

```python
# management/commands/enviar_reporte_performance.py

# Métricas de las últimas 24h:
# - Top 5 operaciones más lentas (max y p95)
# - Número de alertas disparadas
# - Operaciones que fallaron
# - Tendencia vs. 7 días anteriores
```

**Formato:**

```
Asunto: [Toque] Reporte diario performance — 2026-06-13

📊 RESUMEN ÚLTIMAS 24 HORAS

Operación                         | p50   | p95    | Max    | Ejecuciones
scoring.calcular_puntos_fecha     | 120ms | 340ms  | 890ms  | 47
scoring.ranking_acumulado         | 85ms  | 210ms  | 620ms  | 47
sync.match_results                | 3.2s  | 8.1s   | 12.4s  | 92
view.leaderboard                  | 45ms  | 180ms  | 420ms  | 1 240

⚠️  ALERTAS: 3 (scoring.ranking_acumulado × 3)
❌  ERRORES: 0

📈 TENDENCIA vs. 7 DÍAS ANTERIORES
scoring.ranking_acumulado p95: 210ms → +12% ↑

Ver dashboard: https://toque.up.railway.app/observability/
```

---

## 9. Dashboard Interno (Django Admin + Vista Propia)

### 9.1 Django Admin

Registrar `PerformanceMetric` con:
- Filtros por `label`, `timestamp`, `quiniela_id`, `success`
- `list_display`: label, duration_ms, quiniela_id, timestamp, alerta_enviada
- Rango de fechas

### 9.2 Vista `/observability/` (solo staff)

Página HTML simple con:
- Tabla: últimas 50 métricas en tiempo real
- Agregados por label: avg, max, count (últimas 24h)
- Indicador visual: verde / amarillo / rojo según umbral

No requiere frontend framework — HTML puro con tabla Bootstrap que ya tenemos.

---

## 10. Exportación a Grafana Cloud (Capa Opcional)

**Grafana Cloud Free Tier:** 10 000 series, 50 GB logs, retención 14 días — suficiente.

**Mecanismo:**
- Management command `export_to_grafana` corriendo cada 5 minutos (cron django-q2)
- Lee las últimas N métricas no exportadas
- Formatea en Prometheus Exposition Format:
  ```
  toque_operation_duration_ms{label="scoring.ranking_acumulado",quiniela="3"} 620 1718316000000
  ```
- POST a Grafana Cloud Prometheus Remote Write endpoint
- Marca registros como exportados

**Configuración:**
```env
GRAFANA_CLOUD_URL=https://prometheus-prod-XX.grafana.net/api/prom/push
GRAFANA_CLOUD_USER=123456
GRAFANA_CLOUD_TOKEN=...
```

**Estado:** Opcional — el sistema funciona completo sin esta capa.

---

## 11. Plan de Implementación

### Fase 1 — Fundación (1 sesión, ~2h)
- [ ] Crear app `observability` con modelo `PerformanceMetric`
- [ ] Implementar `track_performance` decorator
- [ ] Aplicar decorator en `ScoringService` y `RankingService`
- [ ] Migración de base de datos
- [ ] Registro en Django Admin

### Fase 2 — Alertas (1 sesión, ~1h)
- [ ] Task `enviar_alerta_performance` con throttle
- [ ] Template de email de alerta
- [ ] Aplicar decorator en `run_sync_match_results` y vistas de leaderboard

### Fase 3 — Reporte Diario (1 sesión, ~1h)
- [ ] Management command `enviar_reporte_performance`
- [ ] Cron django-q2 a las 08:00 UTC
- [ ] Management command `limpiar_metricas_antiguas` (retención 30 días)

### Fase 4 — Dashboard Interno (1 sesión, ~1h)
- [ ] Vista `/observability/` con tabla + agregados
- [ ] URL protegida con `@staff_member_required`

### Fase 5 — Grafana Cloud (Opcional)
- [ ] Management command `export_to_grafana`
- [ ] Cron cada 5 min
- [ ] Dashboard Grafana con paneles básicos

---

## 12. Costo

| Componente | Costo |
|------------|-------|
| Modelo `PerformanceMetric` en PostgreSQL Railway | $0 (usa BD existente) |
| Emails de alerta vía SendGrid | $0 (free tier: 100 emails/día) |
| Reporte diario | $0 |
| Dashboard interno Django | $0 |
| Grafana Cloud (opcional) | $0 (free tier) |
| **Total** | **$0** |

---

## 13. Métricas de Éxito

- Visibilidad de p95 de cada operación crítica dentro de los próximos 7 días de partido
- Alerta recibida en < 1 minuto cuando `recalcular_ranking_acumulado` supere 1 000 ms
- Reporte diario con tendencia → detectar degradación gradual semana a semana
- Sin impacto en performance del pipeline (escritura de métricas no bloquea el proceso)

---

## 14. Decisiones Pendientes

1. **¿Activar Grafana Cloud desde el inicio o en Fase 5?** Recomiendo Fase 5 — el dashboard interno es suficiente para comenzar.
2. **¿Throttle de alertas:** 30 min por (label, quiniela)? ¿O global por label? Propongo per-quiniela para mayor granularidad.
3. **Retención de métricas:** 30 días propuesto. ¿Suficiente o necesitamos histórico de 90 días?
4. **¿Incluir métricas de vistas HTTP desde el inicio (Fase 1)?** Se puede agregar un middleware liviano o dejarlo para Fase 2.
