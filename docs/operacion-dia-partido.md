# Guía de Operación — Día de Partido

Manual para registrar resultados y calcular puntos en Toque durante el Mundial 2026.

---

## Estado actual (al 11/06/2026)

| Elemento | Valor |
|---|---|
| Quiniela activa | **Mundial 2026** (slug: `mundial-2026`) |
| Jugadores inscritos | `jugador1`, `drei`, `admin` |
| Fecha 1 (Jornada 1) | 25 partidos — 11 al 17 de junio |
| Primer partido | **México vs Sudáfrica** — 11/06 a las 14:00 hora Colombia |
| Pronósticos cerraron | 13:00 hora Colombia (ya cerrados para el primer partido) |
| URL producción | https://polla-millonaria-production.up.railway.app |
| Admin | https://polla-millonaria-production.up.railway.app/admin/ |

> **Nota:** Para el primer partido (México vs Sudáfrica) ya hay un resultado de PRUEBA cargado (2-1 México gana) para verificar el sistema. El admin debe sobrescribir este resultado con el real después del partido.

---

## Flujo completo de un partido

### PASO 1 — Después del partido: Registrar resultados

Ir a:
```
Admin → Predictions → Eventos de partido
```

Filtra por partido usando el buscador. Para México vs Sudáfrica, busca "México". Verás 4 eventos (uno por tipo). Para cada uno, edita el campo **Resultado**.

#### Valores a ingresar según el marcador final

Si el partido terminó **2-1** (México gana):

| Tipo de evento | Campo "Resultado" | Lógica |
|---|---|---|
| **SCORE** | `2-1` | `goles_local-goles_visitante` sin espacios |
| **WINNER** | `H` | `H`=local gana, `D`=empate, `A`=visitante gana |
| **BTTS** | `yes` | `yes` si ambos equipos anotaron ≥1 gol; `no` si alguno quedó en 0 |
| **OU25** | `over` | `over` si total de goles ≥3; `under` si total es 0, 1 o 2 |

#### Tabla de referencia rápida

| Marcador | SCORE | WINNER | BTTS | OU25 |
|---|---|---|---|---|
| 0-0 | `0-0` | `D` | `no` | `under` |
| 1-0 | `1-0` | `H` | `no` | `under` |
| 1-1 | `1-1` | `D` | `yes` | `under` |
| 2-0 | `2-0` | `H` | `no` | `under` |
| 2-1 | `2-1` | `H` | `yes` | `over` |
| 3-0 | `3-0` | `H` | `no` | `over` |
| 3-1 | `3-1` | `H` | `yes` | `over` |
| 0-2 | `0-2` | `A` | `no` | `under` |
| 1-2 | `1-2` | `A` | `yes` | `over` |
| 2-2 | `2-2` | `D` | `yes` | `over` |

**Regla BTTS:** si hay algún `0` en el marcador → `no`. Si ambos tienen ≥1 → `yes`.  
**Regla OU25:** suma los goles. ≥3 → `over`. 0, 1 o 2 → `under`.

#### Cómo guardar en el admin

1. Abre el EventoPartido (ej: `SCORE — México vs Sudáfrica`)
2. Escribe el valor en el campo **Resultado**
3. Guarda con el botón "Guardar"
4. Repite para los otros 3 eventos del mismo partido

---

### PASO 2 — Calcular puntos y ranking

Ir a:
```
Admin → Tournaments → Fechas
```

1. Marcar el checkbox de **"Jornada 1 — Fase de Grupos"**
2. En el menú **Acción**, seleccionar **"▶ Calcular puntos y recalcular rankings"**
3. Hacer click en **"Ir"**

#### Qué significa cada mensaje del admin

| Color | Mensaje | Qué pasó |
|---|---|---|
| 🟢 Verde | `✓ N evento(s) puntuados en X quiniela(s)` | **OK** — se calcularon puntos correctamente |
| 🟡 Amarillo | `⚠ Pipeline ejecutado pero sin puntuaciones` | **Falta resultado** — revisa el Paso 1 primero |
| 🔴 Rojo | `✗ Error en Job #N` | Error técnico — revisar con el dev |

> **Importante:** Si ves el mensaje amarillo, significa que los eventos aún no tienen resultado registrado. Vuelve al Paso 1 y verifica que guardaste el campo "Resultado" en cada EventoPartido del partido.

Podés calcular **parcialmente** después de cada partido — el sistema es idempotente (correrlo dos veces no duplica puntos).

---

### PASO 3 — Verificar resultados

**Leaderboard acumulado:**
```
/quinielas/mundial-2026/leaderboard/
```

**Ranking por fecha (Jornada 1):**
```
/quinielas/mundial-2026/fechas/1/ranking/
```

**Pronósticos + puntos por partido (México vs Sudáfrica):**
```
/quinielas/mundial-2026/partidos/10/resultados/
```

> El número al final (`10`) es el ID interno del partido en la BD. Cada partido tiene un ID diferente. Para encontrar el ID de otros partidos, ve a `Admin → Tournaments → Matches` y busca el partido — el ID aparece en la URL al editar.

---

## Sistema de puntos (referencia rápida)

| Tipo | Acierto | Puntos |
|---|---|---|
| SCORE | Marcador exacto (pronosticaste 2-1, fue 2-1) | **3 pts** |
| SCORE | Misma diferencia de goles y mismo ganador (3-2 cuando fue 2-1) | **2 pts** |
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

- [x] ~~Verificar que jugadores hayan pronosticado~~ (plazo cerró a las 13:00)
- [ ] **~14:00** — empieza México vs Sudáfrica
- [ ] Anotar el marcador final
- [ ] Ir a admin → Predictions → Eventos de partido → buscar "México vs Sudáfrica"
- [ ] Editar los 4 eventos y guardar el resultado real (sobreescribir el de prueba)
- [ ] Ir a admin → Tournaments → Fechas → seleccionar Jornada 1 → Calcular puntos y ranking
- [ ] Confirmar mensaje verde ✓ en el admin
- [ ] Verificar ranking en `/quinielas/mundial-2026/leaderboard/`
- [ ] Repetir los pasos de resultado+cálculo para cada partido de la jornada

---

## Partidos de Fecha 1 — Jornada 1 (horarios Colombia UTC-5)

| Fecha/Hora (COL) | Partido | Match ID en BD |
|---|---|---|
| 11/06 14:00 | México vs Sudáfrica | `10` |
| 11/06 22:00 | Corea del Sur vs Chequia | `11` |
| 12/06 16:00 | Canadá vs Bosnia y Herzegovina | `12` |
| 12/06 18:00 | Estados Unidos vs Paraguay | `13` |
| 13/06 14:00 | Qatar vs Suiza | `14` |
| 13/06 18:00 | Brasil vs Marruecos | `15` |
| 13/06 22:00 | Haití vs Escocia | `16` |
| 13/06 23:00 | Australia vs Turquía | `17` |
| 14/06 12:00 | Alemania vs Curazao | `18` |
| 14/06 14:00 | Países Bajos vs Japón | `19` |
| 14/06 19:00 | Costa de Marfil vs Ecuador | `20` |
| 14/06 19:00 | Suecia vs Túnez | `21` |
| 15/06 11:00 | España vs Cabo Verde | `22` |
| 15/06 11:00 | Bélgica vs Egipto | `23` |
| 15/06 18:00 | Arabia Saudita vs Uruguay | `24` |
| 15/06 18:00 | Irán vs Nueva Zelanda | `25` |
| 16/06 15:00 | Francia vs Senegal | `26` |
| 16/06 18:00 | Irak vs Noruega | `27` |
| 16/06 20:00 | Argentina vs Argelia | `28` |
| 16/06 20:00 | Austria vs Jordania | `29` |
| 17/06 11:00 | Portugal vs RD Congo | `30` |
| 17/06 14:00 | Inglaterra vs Croacia | `31` |
| 17/06 19:00 | Ghana vs Panamá | `32` |
| 17/06 21:00 | Uzbekistán vs Colombia | `33` |

> Los Match IDs aproximados — si necesitás la URL exacta de resultados para cada partido, ve a `Admin → Matches` y busca el partido para obtener su ID real.

---

## Preguntas frecuentes

**"Calculé pero el ranking sigue vacío / mensaje amarillo ⚠"**
→ Los EventoPartido aún no tienen `resultado` guardado. Ve a `Admin → Predictions → Eventos de partido`, busca el partido y verifica que los 4 eventos tengan el campo "Resultado" completo. Luego vuelve a calcular.

**"Un jugador no tiene puntuación para un evento"**
→ El jugador no pronosticó antes del plazo de cierre. El sistema no asigna puntos para pronósticos no realizados.

**"Necesito corregir un resultado mal ingresado"**
→ Edita el campo "Resultado" en el EventoPartido y vuelve a correr la acción "Calcular puntos y ranking" en la Fecha. El sistema sobreescribe automáticamente.

**"La URL /partidos/1/resultados/ da 404"**
→ El partido con ID 1 en la BD es de un torneo diferente (torneo legacy). Usa los IDs de la tabla de arriba o busca el ID correcto en `Admin → Matches`.

**"Quiero agregar más jugadores"**
→ Admin → Quinielas → Mundial 2026 → sección Inscripciones. Solo pueden pronosticar partidos cuyo plazo no haya cerrado.
