# Reglas de Puntuación — Polla Futbolera

## Tipos de eventos

Cada partido puede tener hasta 4 tipos de eventos apostables. El jugador pronostica cada uno de forma independiente.

| Código | Nombre | ¿Qué se pronostica? | Ejemplo |
|--------|--------|---------------------|---------|
| `SCORE` | Marcador Exacto | El resultado final gol a gol | `2-1` |
| `WINNER` | Ganador del Partido | Quién gana o si hay empate | `H` / `A` / `D` |
| `BTTS` | Ambos Anotan | ¿Los dos equipos marcan al menos 1 gol? | `YES` / `NO` |
| `OU25` | Más/Menos 2.5 Goles | ¿La suma de goles supera 2.5? | `OVER` / `UNDER` |

---

## Evento SCORE — Marcador Exacto

Es el más complejo porque tiene **4 niveles de acierto**. El sistema evalúa en este orden:

### 1. EXACT — Marcador exacto (3 puntos)

El pronóstico coincide gol a gol con el resultado real.

```
Pronóstico: 2-1  |  Resultado: 2-1  →  EXACT  →  3 pts ✓
```

### 2. GOAL_DIFF — Misma diferencia de goles (2 puntos)

El ganador es el mismo **y** la diferencia de goles es idéntica, aunque los goles marcados sean distintos.

```
Pronóstico: 2-1  |  Resultado: 3-2  →  GOAL_DIFF  →  2 pts
  (diferencia: +1)       (diferencia: +1)

Pronóstico: 0-2  |  Resultado: 1-3  →  GOAL_DIFF  →  2 pts
  (diferencia: -2)       (diferencia: -2)
```

> **Caso especial — empates:** Si pronosticas un empate (cualquier X-X) y el resultado también es empate (otro Y-Y diferente), cae en `GOAL_DIFF` porque la diferencia de ambos es 0.
> ```
> Pronóstico: 1-1  |  Resultado: 2-2  →  GOAL_DIFF  →  2 pts
> ```

### 3. WINNER — Ganador correcto, diferencia incorrecta (1 punto)

El ganador (o empate) coincide, pero la diferencia de goles no.

```
Pronóstico: 2-0  |  Resultado: 3-2  →  WINNER  →  1 pt
  (gana local, diff +2)   (gana local, diff +1)

Pronóstico: 2-1  |  Resultado: 4-1  →  WINNER  →  1 pt
  (gana local, diff +1)   (gana local, diff +3)
```

### 4. MISS — Sin acierto (0 puntos)

El ganador pronosticado no coincide con el resultado real.

```
Pronóstico: 2-1  |  Resultado: 1-2  →  MISS  →  0 pts
  (gana local)              (gana visitante)

Pronóstico: 1-1  |  Resultado: 2-0  →  MISS  →  0 pts
  (empate)                  (gana local)
```

### Resumen SCORE

| Código | Condición | Puntos |
|--------|-----------|--------|
| `EXACT` | Marcador idéntico | **3** |
| `GOAL_DIFF` | Mismo ganador + misma diferencia de goles | **2** |
| `WINNER` | Solo el ganador correcto | **1** |
| `MISS` | Ganador incorrecto | **0** |

---

## Evento WINNER — Ganador del Partido

Pronóstico simple: se elige `H` (local), `A` (visitante) o `D` (empate).

| Código | Condición | Puntos |
|--------|-----------|--------|
| `HIT` | Coincide exactamente | **3** |
| `MISS` | No coincide | **0** |

```
Pronóstico: H  |  Resultado: H  →  HIT   →  3 pts ✓
Pronóstico: D  |  Resultado: D  →  HIT   →  3 pts ✓
Pronóstico: A  |  Resultado: H  →  MISS  →  0 pts
```

> **Nota:** Los valores válidos son exactamente `H`, `A` y `D` (mayúsculas).

---

## Evento BTTS — Ambos Anotan

¿Marcaron los dos equipos al menos 1 gol cada uno?

| Código | Condición | Puntos |
|--------|-----------|--------|
| `HIT` | Coincide | **2** |
| `MISS` | No coincide | **0** |

```
Resultado 2-1  →  BTTS real = YES
  Pronóstico YES  →  HIT   →  2 pts ✓
  Pronóstico NO   →  MISS  →  0 pts

Resultado 3-0  →  BTTS real = NO
  Pronóstico NO   →  HIT   →  2 pts ✓
  Pronóstico YES  →  MISS  →  0 pts
```

---

## Evento OU25 — Más/Menos 2.5 Goles

¿La suma total de goles del partido es mayor o menor que 2.5?

| Código | Condición | Puntos |
|--------|-----------|--------|
| `HIT` | Coincide | **2** |
| `MISS` | No coincide | **0** |

```
Resultado 2-1  →  Total goles = 3  →  OU25 real = OVER
  Pronóstico OVER   →  HIT   →  2 pts ✓
  Pronóstico UNDER  →  MISS  →  0 pts

Resultado 1-0  →  Total goles = 1  →  OU25 real = UNDER
  Pronóstico UNDER  →  HIT   →  2 pts ✓
  Pronóstico OVER   →  MISS  →  0 pts
```

> **Umbral:** Se usa 2.5, por lo que 3+ goles = `OVER` y 2 o menos = `UNDER`. Nunca hay empate en este evento.

---

## Puntuación máxima posible por partido

Si un partido tiene los 4 eventos activos:

| Evento | Máx. pts |
|--------|----------|
| SCORE (EXACT) | 3 |
| WINNER (HIT) | 3 |
| BTTS (HIT) | 2 |
| OU25 (HIT) | 2 |
| **Total por partido** | **10** |

---

## Personalización por quiniela

Las reglas anteriores son las **reglas globales** (aplican a todas las quinielas por defecto). Un superadmin puede configurar reglas específicas para una quiniela particular desde el panel de administración en **Scoring → Reglas de Puntuación**, que tendrán prioridad sobre las globales.

---

## Cómo se calcula el ranking

1. **Ranking por fecha:** suma de puntos de todos los eventos de los partidos de esa jornada.
2. **Ranking acumulado:** suma total de puntos en todas las jornadas jugadas.
3. En caso de empate de puntos, dos jugadores comparten la misma posición (no se desempata automáticamente).

Los rankings se recalculan desde el admin en **Torneos → Fechas → acción "Calcular puntos y ranking"**, tras registrar los resultados de los partidos.
