# Spec: sync_knockout_matches

**Estado:** Borrador para revisión  
**Fecha:** 2026-06-28  
**Contexto:** La fase de grupos del Mundial 2026 terminó. Los 32 partidos ya están en la BD con `external_id` real (numérico). Los partidos de eliminatorias **no existen aún** y los equipos que jugarán cada cruce se conocen recién después del sorteo/clasificación.

---

## Problema

Los partidos de eliminatorias (Ronda de 32, Octavos, Cuartos, Semis, Final) deben crearse en la BD cuando la API de football-data.org los confirme con equipos reales. Este proceso se repite en cada ronda, por lo que necesitamos un comando reutilizable, idempotente, y que se ejecute manualmente una vez por ronda.

---

## Alcance

**Hace:**
- Fetch de todos los partidos del torneo desde la API (un solo call HTTP)
- Filtra solo fases de eliminación (excluye `GROUP_STAGE`)
- Crea o actualiza `Match` en la BD con `external_id` real (numérico de la API)
- Crea `EventoPartido` para cada quiniela activa del torneo, para cada `TipoEvento` activo en uso
- Calcula `plazo_cierre = match_date − PREDICTION_DEADLINE_MINUTES`
- Respeta el rate limit del free tier (1 call total, sin loops extra)

**No hace:**
- No sincroniza resultados (eso es `sync_match_results`)
- No actualiza horarios de partidos existentes (eso es `sync_match_dates`)
- No crea equipos nuevos — si un equipo no existe en la BD, logea error y continúa
- No toca partidos de fase de grupos

---

## Endpoint de la API

```
GET /competitions/WC/matches?season=2026
```

Retorna todos los partidos del torneo. El campo `stage` identifica la fase. La misma `FootballDataOrgAdapter.fetch_fixtures()` que usan los comandos existentes.

### Mapeo de fases API → Fecha en BD

| `stage` en API        | `Fecha.numero` | `Fecha.nombre`   |
|-----------------------|----------------|------------------|
| `LAST_32`             | 4              | Ronda de 32      |
| `LAST_16`             | 5              | Octavos de Final |
| `QUARTER_FINALS`      | 6              | Cuartos de Final |
| `SEMI_FINALS`         | 7              | Semifinales      |
| `THIRD_PLACE`         | 8              | Final            |
| `FINAL`               | 8              | Final            |

> Las `Fecha`s ya existen en la BD (creadas por `seed_mundial_2026`). El script solo las busca, nunca las crea.

---

## Modelo de datos afectado

| Modelo          | Operación          | Llave de idempotencia                     |
|-----------------|--------------------|-------------------------------------------|
| `Match`         | `update_or_create` | `external_id` (numérico de la API)        |
| `EventoPartido` | `get_or_create`    | `(partido, quiniela, tipo_evento)`        |

### Campos que se escriben en `Match`

```
external_id   ← id numérico de la API (ej. 521934)
tournament    ← Tournament con external_code="WC2026"
home_team     ← Team buscado por nombre (normalizado + alias)
away_team     ← Team buscado por nombre (normalizado + alias)
match_date    ← UTC (Django almacena en UTC, muestra en America/Bogota)
phase         ← stage de la API ("LAST_32", "QUARTER_FINALS", etc.)
fecha         ← Fecha según mapeo de arriba
status        ← "scheduled"
```

> **Timezone:** La API retorna `utcDate` en UTC (`"2026-06-28T18:00:00Z"`). Se parsea con `datetime.fromisoformat()` tal como lo hace el adapter existente. Django + `USE_TZ=True` + `TIME_ZONE="America/Bogota"` maneja la conversión en display automáticamente. No se necesita conversión manual.

---

## Resolución de equipos

Los 48 equipos ya están en la BD desde el seed. El script los busca por nombre usando el mismo patrón que `sync_wc2026_ids`:

1. Normalizar nombre API con `unicodedata.normalize("NFKD")` + lowercase
2. Aplicar diccionario `ALIAS` (inglés → español)
3. Buscar `Team` cuyo nombre normalizado coincida

Si un equipo no se encuentra → `logger.error(...)` + skip del partido (no abortar).

> Para eliminatorias con equipos tipo "Ganador Grupo A", la API puede devolver `tbd: True`. En ese caso el partido se importa con `status="scheduled"` y `home_team`/`away_team` quedan en `null` (si el modelo lo permite) o se skipea hasta que la API tenga equipos reales.

**Acción requerida antes de implementar:** verificar si `Match.home_team` y `away_team` admiten `null`. Si no, el script solo procesa partidos con equipos confirmados (`tbd: False`).

---

## Creación de EventoPartido

Para cada `Match` creado/actualizado:

1. Obtener quinielas activas del torneo:
   ```python
   quinielas = Quiniela.objects.filter(tournament=torneo, status="activa")
   ```

2. Obtener `TipoEvento` en uso en el torneo (lookup dinámico — no hardcodear):
   ```python
   tipos = TipoEvento.objects.filter(
       eventos__partido__tournament=torneo, activo=True
   ).distinct()
   ```

3. Para cada par `(quiniela, tipo_evento)`:
   ```python
   EventoPartido.objects.get_or_create(
       partido=match,
       quiniela=quiniela,
       tipo_evento=tipo_evento,
       defaults={
           "plazo_cierre": match.match_date - timedelta(minutes=settings.PREDICTION_DEADLINE_MINUTES),
           "estado": "abierto",
       }
   )
   ```

---

## Interfaz del comando

```
python manage.py sync_knockout_matches [opciones]

Opciones:
  --dry-run           Imprime qué haría pero no escribe nada en BD
  --competition STR   Código de la competición (default: "WC")
  --season STR        Temporada (default: "2026")
  --quiniela-slug STR Limitar creación de eventos a una quiniela específica
                      (útil para testing o para agregar una quiniela nueva)
```

---

## Flujo detallado

```
1. Cargar torneo = Tournament.objects.get(external_code="WC2026")
2. Cargar Fechas del torneo como dict { numero → Fecha }
3. API call: adapter.fetch_fixtures("WC", "2026")  ← 1 solo request HTTP
4. Filtrar: [m for m in partidos if m.phase no empieza con "GROUP"]
5. Para cada partido knockout:
   a. Si tbd: skip (no hay equipos aún)
   b. Resolver home_team / away_team por nombre normalizado
   c. Si algún equipo no existe: logger.error + continue
   d. Resolver fecha = fechas_dict[PHASE_MAP[m.phase]]
   e. Match.objects.update_or_create(
          external_id=m.external_id,
          defaults={tournament, home_team, away_team, match_date, phase, fecha, status}
      )
   f. Para cada (quiniela, tipo_evento): EventoPartido.objects.get_or_create(...)
6. Imprimir resumen: partidos_procesados, partidos_creados, partidos_actualizados,
                     eventos_creados, eventos_ya_existían, equipos_no_encontrados
```

---

## Idempotencia

El comando es seguro de correr múltiples veces:
- `update_or_create` en `Match` actualiza si hay cambios, no duplica
- `get_or_create` en `EventoPartido` no duplica (unique_together lo garantiza)
- Si ya existe el `EventoPartido`, no se modifica `plazo_cierre` ni `estado` (está en `defaults`)

---

## Rate limiting

Free tier de football-data.org: 10 requests/minuto.  
El comando hace **1 solo request** (todos los partidos del torneo en una llamada). No se necesita sleep.

---

## Ubicación del archivo

```
polla_futbolera/apps/tournaments/management/commands/sync_knockout_matches.py
```

Reutiliza de otros comandos existentes:
- `ALIAS` dict y `_norm()` de `sync_wc2026_ids.py`
- Patrón `update_or_create` de `sync_match_dates.py`

---

## Puntos a resolver antes de implementar

1. **¿`Match.home_team` y `away_team` admiten `null`?**  
   Si no, el script solo puede importar partidos con equipos confirmados. Para Mundial 2026, la Ronda de 32 empieza el 28 de junio — la API ya debería tener los equipos reales hoy.

2. **¿Qué `TipoEvento` tienen configuradas las quinielas activas?**  
   El lookup dinámico lo resuelve, pero conviene verificar en admin qué tipos existen antes de correr el script.

3. **¿El mapeo de `stage` API es correcto para football-data.org v4?**  
   Confirmar que los valores son `LAST_32`, `LAST_16`, `QUARTER_FINALS`, `SEMI_FINALS`, `THIRD_PLACE`, `FINAL` consultando la respuesta real de la API (o la documentación de football-data.org v4).

---

## Lo que NO se construye

- No se crea una tarea Celery/django-q2 para esto — el comando es manual por diseño
- No se construye un sistema de detección automática de "nueva ronda disponible"
- No se migran datos existentes

---

## Decisión de revisión

**¿Proceder con la implementación?**

- La lógica es un subconjunto directo de `sync_wc2026_ids` + `seed_mundial_2026` — no hay código nuevo de riesgo
- El punto crítico es el mapeo de `stage` — conviene hacer un `--dry-run` primero con `manage.py shell` o verificando la respuesta cruda de la API antes del primer run real
- Estimación: ~150 líneas de código, ~1h de implementación
