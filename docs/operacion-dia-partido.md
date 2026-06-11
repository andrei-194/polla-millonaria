# Guía de Operación — Día de Partido

Manual para registrar resultados y calcular puntos en Toque durante el Mundial 2026.

---

## Estado actual (al 10/06/2026)

| Elemento | Valor |
|---|---|
| Quiniela activa | **Mundial 2026** (slug: `mundial-2026`) |
| Jugadores inscritos | `jugador1`, `drei` |
| Fecha 1 (Jornada 1) | 25 partidos — 11 al 17 de junio |
| Primer partido | **México vs Sudáfrica** — 11/06 a las 14:00 hora Colombia |
| Pronósticos cierran | 13:00 hora Colombia (1h antes de cada partido) |
| URL producción | https://polla-millonaria-production.up.railway.app |
| Admin | https://polla-millonaria-production.up.railway.app/admin/ |

---

## Flujo completo de un partido

### Antes del partido (antes de las 13:00 del 11/06)

Los jugadores pronostican en:
```
/quinielas/mundial-2026/fechas/1/
```

Puedes verificar que ambos ya pronosticaron en:
```
/admin/predictions/pronosticoevento/
```
Filtra por `evento_partido → partido → México vs Sudáfrica`. Deben aparecer 8 registros (2 jugadores × 4 eventos).

Si algún jugador no pronosticó a tiempo, el sistema simplemente no le da puntos para esos eventos — no hay que hacer nada manualmente.

---

### Después del partido — Registrar resultados

Ir a:
```
Admin → Predictions → Eventos de partido
```
URL directa: `/admin/predictions/eventopartido/`

Filtra por partido (usa el buscador o el filtro de fecha). Para **México vs Sudáfrica**, busca los 4 eventos y completa el campo **Resultado** de cada uno:

#### Valores a ingresar según el marcador final

Supón que el partido terminó **2-1** (México gana):

| Tipo de evento | Campo "Resultado" | Lógica |
|---|---|---|
| **SCORE** | `2-1` | Goles local - Goles visitante, sin espacios |
| **WINNER** | `H` | H = local gana, D = empate, A = visitante gana |
| **BTTS** | `yes` | `yes` si ambos anotaron al menos 1, `no` si alguno quedó en 0 |
| **OU25** | `over` | `over` si hay 3+ goles totales, `under` si hay 0, 1 o 2 goles totales |

#### Ejemplos rápidos

| Marcador | SCORE | WINNER | BTTS | OU25 |
|---|---|---|---|---|
| 0-0 | `0-0` | `D` | `no` | `under` |
| 1-0 | `1-0` | `H` | `no` | `under` |
| 1-1 | `1-1` | `D` | `yes` | `under` |
| 2-1 | `2-1` | `H` | `yes` | `over` |
| 3-0 | `3-0` | `H` | `no` | `over` |
| 0-2 | `0-2` | `A` | `no` | `under` |
| 2-2 | `2-2` | `D` | `yes` | `over` |

**Regla BTTS**: si el marcador tiene algún `0` en cualquiera de los dos lados → `no`. Si ambos tienen ≥1 → `yes`.  
**Regla OU25**: suma los goles. Si da 3 o más → `over`. Si da 0, 1 o 2 → `under`.

#### Cómo guardar en el admin

1. Abre el EventoPartido (ej: `SCORE — México vs Sudáfrica`)
2. Escribe el resultado en el campo **Resultado**
3. Guarda (botón "Guardar" al fondo)
4. Repite para los otros 3 eventos del mismo partido

No toques el campo **Estado** — se actualiza automáticamente al calcular puntos.

---

### Calcular puntos de la Fecha 1

> **Cuándo hacerlo:** Después de que el **último partido de Fecha 1** haya terminado y hayas ingresado todos sus resultados. El último partido es **Uzbekistán vs Colombia** el **17/06 a las 21:00 hora Colombia**.

Si querés calcular parcialmente antes (ej. después de los primeros 5 partidos), podés hacerlo — el sistema es idempotente y no da error si se recalcula.

#### Pasos para calcular

1. Ir a **Admin → Tournaments → Fechas**
   URL: `/admin/tournaments/fecha/`

2. Marcar el checkbox de **"Jornada 1 — Fase de Grupos"**

3. En el menú **Acción**, seleccionar **"Calcular puntos y ranking"**

4. Hacer click en **"Ir"**

El sistema procesa todos los eventos de esa fecha y actualiza el ranking automáticamente. Verás un mensaje de confirmación.

---

### Verificar resultados

**Leaderboard público:**
```
/quinielas/mundial-2026/leaderboard/
```

**Ranking por fecha (Fecha 1):**
```
/quinielas/mundial-2026/fechas/1/ranking/
```

**Pronósticos + puntos por partido (ej. México vs Sudáfrica):**
```
/quinielas/mundial-2026/partidos/<id>/resultados/
```
(el `<id>` lo encontrás en el admin del partido)

**En el admin — ver puntuaciones calculadas:**
```
Admin → Scoring → Puntuaciones de evento
```
Filtra por quiniela `mundial-2026`. Deberías ver registros con `codigo_acierto` (EXACT, GOAL_DIFF, WINNER, HIT, MISS) y `puntos` correctos.

---

## Sistema de puntos (referencia rápida)

| Tipo | Acierto | Puntos |
|---|---|---|
| SCORE | Marcador exacto (ej: pronosticaste 2-1, fue 2-1) | **3 pts** |
| SCORE | Misma diferencia de goles y mismo ganador (ej: 3-2 cuando fue 2-1) | **2 pts** |
| SCORE | Solo el ganador correcto | **1 pt** |
| SCORE | Fallo | 0 pts |
| WINNER | Ganador correcto | **3 pts** |
| WINNER | Fallo | 0 pts |
| BTTS | Correcto | **2 pts** |
| BTTS | Fallo | 0 pts |
| OU25 | Correcto | **2 pts** |
| OU25 | Fallo | 0 pts |

**Máximo por partido:** 3 + 3 + 2 + 2 = **10 puntos**  
**Máximo Fecha 1 (25 partidos):** 250 puntos

---

## Checklist del 11/06 (día del primer partido)

- [ ] Verificar que `jugador1` y `drei` hayan pronosticado antes de las 13:00
- [ ] **14:00** — empieza México vs Sudáfrica
- [ ] Anotar el marcador final del partido
- [ ] Ingresar resultados en admin (4 eventos por partido)
- [ ] Repetir para cada partido de Fecha 1 a medida que terminen
- [ ] Después del último partido (17/06 noche): calcular puntos y ranking en admin
- [ ] Revisar leaderboard en `/quinielas/mundial-2026/leaderboard/`

---

## Partidos de Fecha 1 — Jornada 1 (con horarios Colombia)

| Fecha/Hora (COL) | Partido |
|---|---|
| 11/06 14:00 | México vs Sudáfrica |
| 11/06 22:00 | Corea del Sur vs Chequia |
| 12/06 16:00 | Canadá vs Bosnia y Herzegovina |
| 12/06 18:00 | Estados Unidos vs Paraguay |
| 13/06 14:00 | Qatar vs Suiza |
| 13/06 18:00 | Brasil vs Marruecos |
| 13/06 22:00 | Haití vs Escocia |
| 13/06 23:00 | Australia vs Turquía |
| 14/06 12:00 | Alemania vs Curazao |
| 14/06 14:00 | Países Bajos vs Japón |
| 14/06 19:00 | Costa de Marfil vs Ecuador |
| 14/06 19:00 | Suecia vs Túnez |
| 15/06 11:00 | España vs Cabo Verde |
| 15/06 11:00 | Bélgica vs Egipto |
| 15/06 18:00 | Arabia Saudita vs Uruguay |
| 15/06 18:00 | Irán vs Nueva Zelanda |
| 16/06 15:00 | Francia vs Senegal |
| 16/06 18:00 | Irak vs Noruega |
| 16/06 20:00 | Argentina vs Argelia |
| 16/06 20:00 | Austria vs Jordania |
| 17/06 11:00 | Portugal vs RD Congo |
| 17/06 14:00 | Inglaterra vs Croacia |
| 17/06 19:00 | Ghana vs Panamá |
| 17/06 21:00 | Uzbekistán vs Colombia ← **último partido Fecha 1** |

---

## Si algo sale mal

**"Calculé puntos pero los valores son 0"**
→ Ya fue corregido (fix del 10/06). Si vuelve a pasar, revisar que las `ReglaPuntuacion` globales existan en admin.

**"Un jugador no tiene puntuación para un evento"**
→ El jugador no pronosticó antes del plazo. Es correcto — no se asignan puntos.

**"Necesito recalcular por un error en el resultado"**
→ Corrijo el `resultado` en el EventoPartido y vuelvo a correr la acción "Calcular puntos y ranking" en la Fecha. El sistema sobreescribe automáticamente.

**"Quiero agregar más jugadores a la quiniela"**
→ Admin → Quinielas → Mundial 2026 → sección Inscripciones → agregar jugador. Los jugadores nuevos solo pueden pronosticar los partidos cuyo plazo no haya cerrado aún.
