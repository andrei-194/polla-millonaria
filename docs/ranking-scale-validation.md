# Spec: Validación de Escala y Async del Proceso de Ranking

**Rama sugerida:** `feat/ranking-scale-and-async`  
**Prioridad:** Alta — debe completarse antes del primer torneo con >100 usuarios  
**Estimación:** 3–4 sesiones de trabajo

---

## Contexto y problema

El pipeline de cálculo de ranking se ejecuta sincrónicamente desde Django Admin:

```
FechaAdmin.calcular_puntos_y_ranking()
  └── ScoringService.calcular_puntos_fecha()        ← N+1 oculto aquí
        └── for evento in eventos:
              └── calcular_puntos_evento(evento.id)  ← 1 transaction + 5 queries por evento
  └── RankingService.recalcular_ranking_fecha()      ← OK: 1 query GROUP BY
  └── RankingService.recalcular_ranking_acumulado()  ← OK: 1 query GROUP BY
```

### Problema A — N+1 en `calcular_puntos_fecha`

Cada iteración del loop en `services.py:96` abre su propia `transaction.atomic()` y ejecuta:
1. `SELECT EventoPartido` con `select_related`
2. `SELECT PronosticoEvento` filtrado por evento
3. `SELECT ReglaPuntuacion` filtrado por `tipo_evento + quiniela` (repetida aunque el tipo sea igual)
4. `bulk_create` PuntuacionEvento
5. `UPDATE EventoPartido.estado = "puntuado"`

Con 10 partidos × 2 eventos × 500 usuarios → **100 queries / ~3–12 segundos** dependiendo de latencia a Postgres en Railway.

### Problema B — Request HTTP síncrono

El admin action de Django espera a que termine todo antes de responder. Railway tiene un timeout de **30 segundos** en requests HTTP. Con >700 usuarios y un torneo de 10 partidos es posible alcanzarlo.

### Lo que NO es problema

`recalcular_ranking_fecha` y `recalcular_ranking_acumulado` son una sola query SQL cada uno. Escalan bien hasta ~50,000 filas en PuntuacionEvento sin ajustes.

---

## Alcance de este spec

### Fase 1 — Medir antes de optimizar (entregable: management command)
### Fase 2 — Eliminar el N+1 (entregable: refactor + tests)
### Fase 3 — Async con Django-Q2 (entregable: worker + admin mejorado)

---

## Arquitectura propuesta

### Flujo actual (síncrono)

```
Admin HTTP Request
    │
    ▼
FechaAdmin.calcular_puntos_y_ranking()
    │
    ├── [for cada fecha] calcular_puntos_fecha()
    │       └── [for cada evento] calcular_puntos_evento()  ← N queries
    │
    ├── [for cada quiniela×fecha] recalcular_ranking_fecha()
    │
    └── [for cada quiniela] recalcular_ranking_acumulado()
    │
    ▼
HTTP Response (puede tardar 10–30s)
```

### Flujo propuesto (async con Django-Q2)

```
Admin HTTP Request
    │
    ▼
FechaAdmin.calcular_puntos_y_ranking()
    │
    ├── Crea CalculoJob(estado=PENDING, fechas=[...])
    │
    └── django_q.tasks.async_task("scoring.tasks.pipeline_ranking", job_id)
    │
    ▼
HTTP Response inmediata → redirige a página con polling

[En worker separado: python manage.py qcluster]
    │
    ▼
pipeline_ranking(job_id)
    │
    ├── job.estado = RUNNING; job.save()
    │
    ├── calcular_puntos_fecha_bulk()      ← versión refactorizada (3 queries total)
    │
    ├── recalcular_ranking_fecha()
    │
    ├── recalcular_ranking_acumulado()
    │
    └── job.estado = DONE / ERROR; job.save()

[Admin polling cada 2s via AJAX]
    │
    ▼
GET /admin/scoring/calculojob/<id>/status/ → {"estado": "DONE", "resumen": "..."}
```

---

## Fase 1: Management command `benchmark_ranking`

### Ubicación
```
polla_futbolera/apps/scoring/management/
    __init__.py
    commands/
        __init__.py
        benchmark_ranking.py
```

### Interface del comando
```bash
python manage.py benchmark_ranking --usuarios 500 --fechas 20 --partidos 8 --limpiar
python manage.py benchmark_ranking --usuarios 1000 --fechas 38 --partidos 10
python manage.py benchmark_ranking --usuarios 50 --fechas 8 --partidos 8 --limpiar --verbose
```

### Flags
| Flag | Default | Descripción |
|------|---------|-------------|
| `--usuarios` | 100 | Cantidad de usuarios sintéticos a crear |
| `--fechas` | 10 | Cantidad de fechas/jornadas |
| `--partidos` | 8 | Partidos por fecha |
| `--limpiar` | False | Elimina todos los datos del torneo sintético al finalizar |
| `--verbose` | False | Imprime EXPLAIN ANALYZE de las queries críticas |
| `--solo-ranking` | False | Salta generación de datos, asume que ya existen |

### Lógica de generación de datos sintéticos

```python
# El comando debe:
# 1. Crear un Tournament con name="BENCHMARK_<timestamp>" para poder limpiarlo después
# 2. Crear N usuarios con username="bench_user_{i}"
# 3. Crear una Quiniela ligada al torneo
# 4. Inscribir todos los usuarios a la quiniela
# 5. Crear M fechas, cada una con K partidos
# 6. Por cada partido: crear 2 EventoPartido (tipo SCORE + tipo WINNER)
# 7. Por cada EventoPartido: crear PronosticoEvento para TODOS los usuarios
#    (todos pronósticaron, caso de carga máxima)
# 8. Setear resultado en todos los EventoPartido

# IMPORTANTE: usar bulk_create en cada paso, nunca .save() en loop
# Los usuarios deben tener password inutilizable (set_unusable_password)
# para no contaminar auth
```

### Output esperado

```
══════════════════════════════════════════════════════════════
  BENCHMARK RANKING — 500 usuarios / 20 fechas / 8 partidos
══════════════════════════════════════════════════════════════
  Generando datos...
    ✓ 500 usuarios creados
    ✓ 20 fechas, 160 partidos, 320 eventos
    ✓ 160,000 pronósticos insertados (bulk)
  
  Fase 1: calcular_puntos_fecha (1 fecha × 1 quiniela)
    Eventos procesados: 16
    Puntuaciones creadas: 8,000
    Tiempo: 0.842s

  Fase 2: recalcular_ranking_fecha
    Usuarios rankeados: 500
    Tiempo: 0.043s

  Fase 3: recalcular_ranking_acumulado
    Usuarios rankeados: 500
    Tiempo: 0.078s

  Pipeline completo (20 fechas):
    calcular_puntos (todas las fechas): 17.2s   ← aquí está el problema
    recalcular_ranking_fecha (×20):      0.86s
    recalcular_ranking_acumulado:        0.08s
    TOTAL:                              18.1s

  ⚠ ALERTA: calcular_puntos supera 10s. Se recomienda async.

══════════════════════════════════════════════════════════════
```

### EXPLAIN ANALYZE (solo con `--verbose`)

Con `--verbose`, el comando debe ejecutar y mostrar el plan de la query de `recalcular_ranking_acumulado`:

```python
from django.db import connection
sql = str(stats_qs.query)
with connection.cursor() as cursor:
    cursor.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {sql}")
    rows = cursor.fetchall()
    for row in rows:
        self.stdout.write(row[0])
```

---

## Fase 2: Refactor `calcular_puntos_fecha` (eliminar N+1)

### Objetivo

Pasar de `5 × N_eventos` queries a exactamente **4 queries** independientes del número de eventos:

| Query | Actual | Propuesto |
|-------|--------|-----------|
| Cargar eventos | 1 por evento (dentro del loop) | 1 total con `prefetch_related` |
| Cargar pronósticos | 1 por evento | 1 total: `PronosticoEvento.filter(evento_partido__in=evento_ids)` |
| Cargar reglas | 1 por evento (puede repetirse por tipo) | 1 total: `ReglaPuntuacion.filter(tipo_evento__in=tipos_ids, quiniela_id__in=[quiniela_id, None])` |
| `bulk_create` PuntuacionEvento | 1 por evento | 1 total |
| `UPDATE` EventoPartido.estado | 1 por evento | 1 total: `EventoPartido.filter(id__in=...).update(estado="puntuado")` |

### Pseudocódigo del refactor

```python
def calcular_puntos_fecha(self, quiniela_id: int, fecha_id: int) -> dict:
    with transaction.atomic():

        # Query 1: Cargar todos los eventos de la fecha con resultado
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

        # Query 2: Todos los pronósticos de todos los eventos en una sola query
        pronosticos = list(
            PronosticoEvento.objects
            .filter(evento_partido_id__in=evento_ids)
            .values("usuario_id", "evento_partido_id", "valor")
        )

        # Indexar por evento_partido_id para acceso O(1) en el loop de evaluación
        pronosticos_por_evento: dict[int, list] = defaultdict(list)
        for p in pronosticos:
            pronosticos_por_evento[p["evento_partido_id"]].append(p)

        # Query 3: Todas las reglas de todos los tipos involucrados
        reglas_qs = ReglaPuntuacion.objects.filter(
            tipo_evento_id__in=tipo_ids,
            quiniela_id__in=[quiniela_id, None],
        )
        # Construir dict {(tipo_evento_id, codigo_acierto): puntos}
        # con prioridad quiniela-específica sobre global (misma lógica de _cargar_reglas)
        reglas_globales: dict[tuple, int] = {}
        reglas_especificas: dict[tuple, int] = {}
        for r in reglas_qs:
            key = (r.tipo_evento_id, r.codigo_acierto)
            if r.quiniela_id is None:
                reglas_globales[key] = r.puntos
            else:
                reglas_especificas[key] = r.puntos
        reglas = {**reglas_globales, **reglas_especificas}  # específicas sobrescriben

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

        # Query 4a: Un solo bulk_create para todos los PuntuacionEvento
        PuntuacionEvento.objects.bulk_create(
            puntuaciones,
            update_conflicts=True,
            unique_fields=["usuario_id", "evento_partido_id"],
            update_fields=["valor_pronosticado", "valor_resultado",
                           "codigo_acierto", "puntos", "calculado_en"],
        )

        # Query 4b: Un solo UPDATE de estado
        EventoPartido.objects.filter(id__in=evento_ids).update(estado="puntuado")

        return {"ok": len(eventos_con_resultado), "sin_resultado": sin_resultado}
```

### Contrato de compatibilidad

- La firma del método **no cambia**: `calcular_puntos_fecha(self, quiniela_id, fecha_id) -> dict`
- El dict de retorno **no cambia**: `{"ok": int, "sin_resultado": [ids]}`
- `calcular_puntos_evento` **se mantiene** sin cambios — sigue siendo útil para recalcular un evento individual desde el admin de Predictions
- La lógica de evaluación (`_evaluar`, `_evaluar_score`) **no se toca**

### Tests a agregar/modificar

Archivo: `polla_futbolera/tests/test_scoring_engine.py`

1. **Verificar que el refactor produce el mismo resultado que el original:**
   Crear un test `TestCalcularPuntosFechaBulk` que use la misma fixture `TournamentScenario` y compare resultados con múltiples eventos y usuarios.

2. **Test de escala mínima en CI:**
   ```python
   def test_calcular_fecha_multiples_usuarios_y_eventos(self):
       # 4 usuarios, 3 partidos, 2 eventos cada uno = 6 EventoPartido, 24 pronósticos
       # Verifica: len(PuntuacionEvento) == 24, todos con puntos correctos
   ```

3. **Test de idempotencia en batch:**
   Llamar `calcular_puntos_fecha` dos veces → sigue habiendo `24` filas, no `48`.

---

## Fase 3: Integración Django-Q2 (async)

> Esta fase se implementa **solo si el benchmark de Fase 1 muestra que el tiempo supera 8s** para el volumen de producción esperado, O desde el principio si queremos arquitectura correcta.

### Dependencia a agregar

```
# requirements.txt
django-q2>=1.7.0
```

### Configuración en settings.py

```python
Q_CLUSTER = {
    "name": "polla_futbolera",
    "workers": 1,          # Railway Starter Plan: 1 worker es suficiente
    "recycle": 500,
    "timeout": 300,        # 5 min max por tarea
    "compress": False,
    "save_limit": 50,
    "queue_limit": 10,
    "cpu_affinity": 1,
    "label": "Ranking Worker",
    "orm": "default",      # usa Postgres como broker, sin Redis
}
```

### Procfile para Railway

```
web: gunicorn polla_futbolera.wsgi:application --bind 0.0.0.0:$PORT
worker: python manage.py qcluster
```

> Railway permite múltiples procesos en el mismo servicio con Procfile. El worker consume ~50MB adicionales.

### Nuevo modelo `CalculoJob`

```
App: scoring
Archivo: scoring/infrastructure/models.py (agregar al final)
```

```python
class CalculoJob(models.Model):
    ESTADO_CHOICES = [
        ("PENDING", "Pendiente"),
        ("RUNNING", "En proceso"),
        ("DONE", "Completado"),
        ("ERROR", "Error"),
    ]

    estado         = models.CharField(max_length=10, choices=ESTADO_CHOICES, default="PENDING")
    fechas         = models.ManyToManyField("tournaments.Fecha")
    iniciado_por   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    creado_en      = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    resumen        = models.TextField(blank=True)   # JSON con resultados al terminar
    error_msg      = models.TextField(blank=True)   # traceback si estado=ERROR

    class Meta:
        db_table = "scoring_calculo_job"
        ordering = ["-creado_en"]
        verbose_name = "Job de Cálculo"
```

### Task function

```
Archivo: polla_futbolera/apps/scoring/application/tasks.py (nuevo)
```

```python
def pipeline_ranking(job_id: int) -> None:
    """
    Task ejecutada por django-q2 worker.
    Corre el pipeline completo para todas las fechas del CalculoJob.
    """
    from ..infrastructure.models import CalculoJob
    from .services import ScoringService, RankingService
    from apps.predictions.infrastructure.models import EventoPartido

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

    except Exception as exc:
        import traceback
        job.estado = "ERROR"
        job.error_msg = traceback.format_exc()
        job.save(update_fields=["estado", "error_msg", "actualizado_en"])
        raise
```

### Admin action modificado

```python
# tournaments/infrastructure/admin.py — reemplazar calcular_puntos_y_ranking

@admin.action(description="▶ Calcular puntos y recalcular rankings (async)")
def calcular_puntos_y_ranking(self, request, queryset):
    from django_q.tasks import async_task
    from apps.scoring.infrastructure.models import CalculoJob

    job = CalculoJob.objects.create(iniciado_por=request.user)
    job.fechas.set(queryset)

    async_task(
        "apps.scoring.application.tasks.pipeline_ranking",
        job.id,
        task_name=f"ranking-job-{job.id}",
    )

    self.message_user(
        request,
        f"⏳ Cálculo encolado (Job #{job.id}). Podés ver el progreso en "
        f"<a href='/admin/scoring/calculojob/{job.id}/'>Admin → Scoring → Jobs</a>.",
        messages.INFO,
    )
```

### Endpoint de polling

```
URL: /admin/scoring/calculojob/<int:job_id>/status/
Vista: scoring/infrastructure/admin.py (view adicional registrada con get_urls)
Respuesta JSON: {"estado": "RUNNING", "resumen": null, "error": null}
```

```python
# En CalculoJobAdmin:
def get_urls(self):
    urls = super().get_urls()
    custom = [path("<int:job_id>/status/", self.admin_site.admin_view(self.status_view))]
    return custom + urls

def status_view(self, request, job_id):
    from django.http import JsonResponse
    job = CalculoJob.objects.get(id=job_id)
    return JsonResponse({
        "estado": job.estado,
        "resumen": json.loads(job.resumen) if job.resumen else None,
        "error": job.error_msg or None,
    })
```

### Template de polling (JavaScript mínimo)

```html
<!-- En change_view del CalculoJob, si estado != DONE/ERROR -->
<script>
(function poll() {
  fetch("{% url 'admin:scoring_calculojob_status' job.id %}")
    .then(r => r.json())
    .then(data => {
      if (data.estado === "DONE" || data.estado === "ERROR") {
        location.reload();
      } else {
        setTimeout(poll, 2000);
      }
    });
})();
</script>
```

---

## Estructura de archivos

### Archivos nuevos

```
polla_futbolera/
├── apps/
│   └── scoring/
│       ├── application/
│       │   └── tasks.py                          ← NUEVO: pipeline_ranking task
│       ├── infrastructure/
│       │   └── models.py                         ← MODIFICAR: agregar CalculoJob
│       └── management/
│           ├── __init__.py                        ← NUEVO
│           └── commands/
│               ├── __init__.py                    ← NUEVO
│               └── benchmark_ranking.py           ← NUEVO
├── tests/
│   ├── test_scoring_engine.py                     ← MODIFICAR: agregar tests de batch
│   └── test_ranking_escala.py                     ← NUEVO: tests de correctitud a escala
└── requirements.txt                               ← MODIFICAR: agregar django-q2 (Fase 3)
```

### Archivos modificados

```
polla_futbolera/apps/scoring/application/services.py
    → calcular_puntos_fecha() refactorizado (Fase 2)

polla_futbolera/apps/tournaments/infrastructure/admin.py
    → calcular_puntos_y_ranking() usa async_task (Fase 3)

polla_futbolera/apps/scoring/infrastructure/admin.py
    → Registrar CalculoJobAdmin con polling (Fase 3)
```

---

## Tests de correctitud a escala

Archivo: `polla_futbolera/tests/test_ranking_escala.py`

```python
class TestRankingEscala(TournamentScenario):
    """
    Verifica correctitud del pipeline con 4 usuarios y múltiples fechas.
    No es un test de performance — es un test de integridad matemática.
    """

    def test_suma_puntos_fecha_es_consistente_entre_ranking_y_puntuaciones(self):
        # Crear 3 fechas con 2 partidos cada una, todos los jugadores pronostican
        # Calcular todo el pipeline
        # Verificar: SUM(PuntuacionEvento.puntos) para usuario X en fecha Y
        #            == RankingFecha.puntos para ese usuario × fecha
        pass

    def test_puntos_acumulados_igual_suma_de_todas_las_fechas(self):
        # RankingAcumulado.puntos_total == sum(RankingFecha.puntos) para cada usuario
        pass

    def test_posiciones_sin_gaps_cuando_hay_empates(self):
        # Si jugadores A y B empatan en 10pts, ambos son posición 1
        # El siguiente es posición 3, no 2
        pass

    def test_exactos_total_cuenta_correctamente(self):
        # RankingAcumulado.exactos_total == count de PuntuacionEvento con codigo_acierto="EXACT"
        pass

    def test_fechas_jugadas_cuenta_fechas_distintas(self):
        # Un usuario que pronosticó en 3 de 5 fechas → fechas_jugadas == 3
        pass

    def test_pipeline_idempotente_en_recalculo(self):
        # Ejecutar el pipeline completo 2 veces sobre las mismas fechas
        # → mismos resultados, sin duplicados, sin cambios en posiciones
        pass
```

---

## Orden de implementación recomendado

```
1. [Fase 1] benchmark_ranking management command
   → Ejecutar en local y en Railway con --usuarios 500 --fechas 20
   → Medir tiempos base ANTES de cualquier cambio de código

2. [Fase 2] Refactor calcular_puntos_fecha
   → Agregar tests de correctitud primero (test_ranking_escala.py)
   → Refactorizar el servicio
   → Correr tests existentes + nuevos para verificar que nada se rompió
   → Ejecutar benchmark_ranking de nuevo para medir mejora

3. [Decisión] Si post-Fase2 el tiempo > 8s para el volumen esperado → implementar Fase 3
             Si post-Fase2 el tiempo < 8s → Fase 3 queda como deuda técnica documentada

4. [Fase 3 - opcional según benchmark] Django-Q2 async
   → Migration para CalculoJob
   → tasks.py
   → Admin modificado + polling
   → Procfile actualizado para Railway
```

---

## Criterios de aceptación

- [ ] `benchmark_ranking` corre sin errores con `--limpiar` y no deja datos basura
- [ ] `benchmark_ranking` imprime tiempos reales para 100 / 500 / 1000 usuarios
- [ ] `calcular_puntos_fecha` refactorizado produce resultados idénticos al original (tests pasan)
- [ ] `calcular_puntos_fecha` refactorizado usa exactamente 4 queries (verificar con `django.test.utils.override_settings(DEBUG=True)` + `len(connection.queries)`)
- [ ] Los tests de correctitud a escala cubren los 6 casos listados
- [ ] (Fase 3) Admin action encola job y responde en <500ms
- [ ] (Fase 3) Worker procesa el job y actualiza `CalculoJob.estado` correctamente
- [ ] (Fase 3) Polling de la vista de status funciona y recarga cuando está DONE

---

## Notas para el implementador

1. **Isolation del benchmark:** Los datos sintéticos deben usar un Tournament con un prefijo reconocible (ej: `BENCHMARK_`) para que `--limpiar` pueda borrarlos sin riesgo. Nunca borrar datos sin ese prefijo.

2. **`calcular_puntos_evento` no se elimina.** El refactor solo toca `calcular_puntos_fecha`. El método individual sigue siendo necesario para corregir un evento específico desde el admin de Predictions.

3. **Django-Q2 con ORM broker no necesita Redis.** Usa la tabla `django_q_task` en Postgres. En Railway esto funciona sin servicios adicionales. El worker se agrega como proceso en el mismo Procfile.

4. **SmallIntegerField en RankingAcumulado.puntos_total:** Con >1000 usuarios y muchas fechas, los puntos totales pueden superar 32,767. Verificar si hay riesgo real según el sistema de puntuación configurado. Si es posible superarlo, migrar a IntegerField.

5. **El benchmark debe correr en el mismo ambiente de Railway** (no solo local) para que los tiempos sean representativos de la latencia real a Postgres.
