# Guía de Operación — Toque Mundial 2026

Manual completo para operar el sistema durante el Mundial 2026. Incluye el flujo automático, comandos de diagnóstico y procedimientos manuales de emergencia.

---

## URLs de producción

| Recurso | URL |
|---|---|
| App | https://polla-millonaria-production.up.railway.app |
| Admin | https://polla-millonaria-production.up.railway.app/admin/ |
| Leaderboard | https://polla-millonaria-production.up.railway.app/quinielas/mundial-2026/leaderboard/ |
| Consola Railway | https://railway.app → proyecto → servicio **web** → pestaña Shell |

---

## Cómo funciona el sistema automático

El sistema **NO requiere intervención manual** para registrar resultados ni calcular puntos. El flujo completo ocurre así:

```
Cada 15 minutos (cron)
  └─ run_sync_match_results()
       ├─ Busca partidos con status=scheduled o in_progress
       │   cuya match_date esté entre hace 90 min y hace 5 horas
       ├─ Consulta football-data.org por cada partido
       ├─ Si status=finished → guarda marcador en BD
       └─ Signal post_save dispara automáticamente:
            ├─ Calcula resultado de cada EventoPartido (SCORE/WINNER/BTTS/OU25)
            ├─ Puntúa los pronósticos de todos los jugadores
            ├─ Recalcula RankingFecha
            └─ Recalcula RankingAcumulado
```

**Resultado:** ~15 minutos después de que termina un partido, los rankings están actualizados solos.

---

## Verificar que el cron esté funcionando

Desde la **consola Railway** (servicio web → Shell):

```bash
python manage.py shell -c "
from django_q.models import Success, Failure, Schedule

s = Schedule.objects.filter(name='sync_match_results_auto').first()
if s:
    print(f'Schedule activo: cron={s.cron} | next_run={s.next_run}')
else:
    print('ALERTA: Schedule no encontrado — ejecutar setup_initial_data')

print()
print('Últimas ejecuciones:')
for t in Success.objects.order_by('-stopped')[:5]:
    print(f'  OK  {t.stopped}  resultado={t.result}')

print()
print('Últimas fallas:')
for t in Failure.objects.order_by('-stopped')[:3]:
    print(f'  ERR {t.stopped}  {t.func}')
"
```

**Output esperado cuando todo está bien:**
```
Schedule activo: cron=*/15 * * * * | next_run=2026-06-13 01:45:00+00:00

Últimas ejecuciones:
  OK  2026-06-12 23:30:19  resultado={'procesados': 0, 'actualizados': 0}
  OK  2026-06-12 23:15:27  resultado={'procesados': 0, 'actualizados': 0}
```

`procesados: 0` cuando no hay partidos en ventana es **normal**. Cuando hay partido terminado verás `actualizados: 1`.

---

## Verificar que un partido específico fue procesado correctamente

Después de que el cron corra tras un partido, verifica desde la consola:

```bash
python manage.py shell -c "
from apps.tournaments.infrastructure.models import Match
from apps.predictions.infrastructure.models import EventoPartido
from apps.scoring.infrastructure.models import PuntuacionEvento

# Cambiar el external_id por el del partido a verificar
m = Match.objects.get(external_id='537327')  # México vs Sudáfrica
print(f'{m.home_team.name} vs {m.away_team.name}: {m.status} | {m.home_score}-{m.away_score}')
print()

for ev in EventoPartido.objects.filter(partido=m).select_related('tipo_evento'):
    print(f'  {ev.tipo_evento.codigo:<8} estado={ev.estado:<10} resultado={ev.resultado}')

pts = PuntuacionEvento.objects.filter(evento_partido__partido=m).count()
print(f'  Puntuaciones creadas: {pts}')
"
```

**Estados posibles de EventoPartido:**

| Estado | Significa | Acción |
|---|---|---|
| `abierto` | El signal no se disparó | Ver sección "Forzar pipeline manualmente" |
| `cerrado` | Signal corrió pero scoring falló | Ver sección "Forzar pipeline manualmente" |
| `puntuado` | **Pipeline completo ✓** | Todo OK |

---

## IDs de partidos en producción (Fase de Grupos)

Los external_id son los IDs de football-data.org. Úsalos para verificar partidos específicos.

| Horario Colombia | Partido | external_id |
|---|---|---|
| 11/06 14:00 | México vs Sudáfrica | `537327` |
| 11/06 21:00 | Corea del Sur vs Chequia | `537328` |
| 12/06 14:00 | Canadá vs Bosnia y Herzegovina | `537333` |
| 12/06 20:00 | Estados Unidos vs Paraguay | `537345` |
| 13/06 14:00 | Qatar vs Suiza | `537334` |
| 13/06 17:00 | Brasil vs Marruecos | `537339` |
| 13/06 20:00 | Haití vs Escocia | `537340` |
| 13/06 23:00 | Australia vs Turquía | `537346` |
| 14/06 12:00 | Alemania vs Curazao | `537351` |
| 14/06 15:00 | Países Bajos vs Japón | `537357` |
| 14/06 18:00 | Costa de Marfil vs Ecuador | `537352` |
| 14/06 21:00 | Suecia vs Túnez | `537358` |
| 15/06 11:00 | España vs Cabo Verde | `537369` |
| 15/06 14:00 | Bélgica vs Egipto | `537363` |
| 15/06 17:00 | Arabia Saudita vs Uruguay | `537370` |
| 15/06 20:00 | Irán vs Nueva Zelanda | `537364` |
| 16/06 14:00 | Francia vs Senegal | `537391` |
| 16/06 17:00 | Irak vs Noruega | `537392` |
| 16/06 20:00 | Argentina vs Argelia | `537397` |
| 16/06 23:00 | Austria vs Jordania | `537398` |
| 17/06 12:00 | Portugal vs RD Congo | `537403` |
| 17/06 15:00 | Inglaterra vs Croacia | `537409` |
| 17/06 18:00 | Ghana vs Panamá | `537410` |
| 17/06 21:00 | Uzbekistán vs Colombia | `537404` |

> Todos los horarios en **hora Colombia (UTC-5)**. El admin de Django muestra la misma hora.

---

## Forzar el pipeline manualmente (emergencia)

Usar solo si el cron falló o el partido no fue procesado automáticamente.

### Opción A — Sincronizar un partido específico

```bash
# Primero verificar qué haría (sin aplicar)
python manage.py sync_match_results --dry-run --match-id <ID_INTERNO>

# Aplicar
python manage.py sync_match_results --match-id <ID_INTERNO>
```

Para encontrar el ID interno de un partido:
```bash
python manage.py shell -c "
from apps.tournaments.infrastructure.models import Match
m = Match.objects.get(external_id='537357')  # external_id del partido
print('ID interno:', m.id)
"
```

### Opción B — Sincronizar todos los partidos de una ventana de tiempo

```bash
# Últimas 8 horas (útil si el cron estuvo caído)
python manage.py sync_match_results --window-minutes 480

# Partidos específicos por ID interno
python manage.py sync_match_results --match-id 19
```

### Opción C — Recalcular puntos y ranking desde el admin

Si el resultado ya está en BD pero el scoring no corrió:

```
Admin → Tournaments → Fechas → seleccionar jornada → Acción: "Calcular puntos y recalcular rankings" → Ir
```

---

## Corrección de horarios de partidos

Si FIFA cambia el horario de algún partido:

```bash
# Ver qué cambiaría
python manage.py sync_match_dates --dry-run

# Aplicar cambios de hora Y recalcular plazo de cierre (20 min antes)
python manage.py sync_match_dates --recalc-deadline
```

---

## Diagnóstico completo del sistema

Para un chequeo general de salud antes o después de una jornada:

```bash
python manage.py shell -c "
from django_q.models import Success, Failure, Schedule
from apps.tournaments.infrastructure.models import Match
from apps.predictions.infrastructure.models import EventoPartido
from django.utils import timezone
from datetime import timedelta

print('=== CRON ===')
s = Schedule.objects.filter(name='sync_match_results_auto').first()
print(f'Schedule: {\"OK\" if s else \"NO ENCONTRADO\"}', f'| next_run: {s.next_run if s else \"-\"}')
ok = Success.objects.order_by('-stopped').first()
print(f'Última ejecución OK: {ok.stopped if ok else \"nunca\"}  resultado={ok.result if ok else \"-\"}')
fail = Failure.objects.order_by('-stopped').first()
print(f'Último error: {fail.stopped if fail else \"ninguno\"}')

print()
print('=== PARTIDOS ===')
now = timezone.now()
recientes = Match.objects.filter(match_date__gte=now - timedelta(hours=24), match_date__lte=now)
for m in recientes.order_by('match_date').select_related('home_team', 'away_team'):
    eventos = EventoPartido.objects.filter(partido=m)
    estados = list(eventos.values_list('estado', flat=True))
    print(f'  {m.home_team.name} vs {m.away_team.name} | status={m.status} | score={m.home_score}-{m.away_score} | eventos={estados}')
"
```

---

## Referencia de resultados para EventoPartido

Si necesitas ingresar resultados manualmente en el admin:

| Marcador | SCORE | WINNER | BTTS | OU25 |
|---|---|---|---|---|
| 0-0 | `0-0` | `D` | `no` | `under` |
| 1-0 | `1-0` | `H` | `no` | `under` |
| 0-1 | `0-1` | `A` | `no` | `under` |
| 1-1 | `1-1` | `D` | `yes` | `under` |
| 2-0 | `2-0` | `H` | `no` | `under` |
| 2-1 | `2-1` | `H` | `yes` | `over` |
| 3-0 | `3-0` | `H` | `no` | `over` |
| 0-2 | `0-2` | `A` | `no` | `under` |
| 1-2 | `1-2` | `A` | `yes` | `over` |
| 2-2 | `2-2` | `D` | `yes` | `over` |

- **WINNER:** `H` = local gana · `D` = empate · `A` = visitante gana
- **BTTS:** `yes` si ambos equipos anotaron ≥1 · `no` si alguno quedó en 0
- **OU25:** `over` si total de goles ≥3 · `under` si total es 0, 1 o 2

---

## Sistema de puntos

| Tipo | Condición | Puntos |
|---|---|---|
| SCORE | Marcador exacto | **3 pts** |
| SCORE | Misma diferencia + mismo ganador | **2 pts** |
| SCORE | Solo el ganador correcto | **1 pt** |
| WINNER | Ganador correcto | **3 pts** |
| BTTS | Correcto | **2 pts** |
| OU25 | Correcto | **2 pts** |

**Máximo por partido:** 10 pts · **Máximo Fecha 1 (24 partidos):** 240 pts

---

## Problemas comunes

**El cron corre pero `actualizados: 0` aunque el partido ya terminó**
→ El partido puede haber quedado fuera de la ventana de 5 horas. Usar `--window-minutes 480` o `--match-id`.

**EventoPartido en estado `cerrado` (no `puntuado`)**
→ El resultado se propagó pero el scoring falló. Ir al admin → Fechas → acción "Calcular puntos y ranking".

**El schedule no existe**
→ Ejecutar `python manage.py setup_initial_data` desde la consola Railway.

**El qcluster no arranca**
→ Verificar que el servicio qcluster en Railway tiene las variables: `DATABASE_URL`, `DJANGO_SETTINGS_MODULE`, `SECRET_KEY`, `FOOTBALL_API_KEY`.

**Un jugador no tiene puntuación para un evento**
→ No pronosticó antes del plazo de cierre (20 min antes del partido). El sistema no asigna puntos retroactivamente.

**Necesito corregir un resultado mal ingresado**
→ Editar el campo "Resultado" en el EventoPartido (admin) y volver a correr "Calcular puntos y ranking" en la Fecha. El sistema sobreescribe automáticamente.
