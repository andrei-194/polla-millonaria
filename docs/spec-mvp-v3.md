# Spec Técnico — MVP v3.0: Eventos, Puntuación y Leaderboard

**Versión:** 3.0  
**Fecha:** 2026-06-02  
**Autor:** Andrés Rodríguez  
**Scope:** Tres módulos interdependientes que conforman el core competitivo del sistema

---

## Índice

1. [Contexto y Problema](#1-contexto-y-problema)
2. [Módulo A — Eventos de Apuesta Escalables](#2-módulo-a--eventos-de-apuesta-escalables)
3. [Módulo B — Motor de Puntuación Riguroso](#3-módulo-b--motor-de-puntuación-riguroso)
4. [Módulo C — Ranking por Fecha y Acumulado](#4-módulo-c--ranking-por-fecha-y-acumulado)
5. [Integración entre módulos](#5-integración-entre-módulos)
6. [Modelos Django — Resumen](#6-modelos-django--resumen)
7. [Flujo de datos completo](#7-flujo-de-datos-completo)
8. [Endpoints nuevos](#8-endpoints-nuevos)
9. [Orden de implementación](#9-orden-de-implementación)
10. [Decisiones de diseño](#10-decisiones-de-diseño)

---

## 1. Contexto y Problema

### Estado actual (v2.0)

El sistema permite a un jugador pronosticar únicamente el **marcador exacto** de un partido (`home_goals` + `away_goals`). El `Score` registra 4 tipos de acierto (exact / goal_diff / winner / miss) con puntos fijos.

### Tres problemas identificados

| # | Problema | Impacto en usuario |
|---|----------|--------------------|
| P1 | Solo existe un tipo de evento (marcador). La variedad de apuestas es nula. | El jugador se aburre rápido; la quiniela pierde engagement. |
| P2 | El sistema de puntuación es frágil: no tolera recálculos, no es auditable, no es configurable por quiniela. | Resultados incorrectos si se corrige un marcador; imposible ajustar puntos por torneo. |
| P3 | No existe concepto de "fecha" (jornada) ni ranking acumulado. Los jugadores no saben si van ganando semana a semana. | Pérdida del componente competitivo central del producto. |

### Principio rector de esta versión

> **Un sistema que hace una cosa bien:** registrar quién acertó qué, cuántos puntos ganó, y ordenar a los jugadores — de forma transparente, reproducible y auditable.

---

## 2. Módulo A — Eventos de Apuesta Escalables

### 2.1 Concepto

Un **EventoApuesta** es una pregunta sobre un partido que el superadmin activa para una quiniela. El jugador responde antes del cierre del plazo. Cuando hay resultado, el motor de puntuación evalúa la respuesta.

El sistema arranca con **4 tipos de evento base** pero está diseñado para agregar nuevos tipos sin tocar código existente — solo datos.

### 2.2 Tipos de evento (MVP — 4 iniciales)

| Código | Nombre | Pregunta al jugador | Respuesta posible | Puntos base |
|--------|--------|--------------------|--------------------|-------------|
| `SCORE` | Marcador Exacto | ¿Cuál será el marcador? | `"2-1"` (goles local-visitante) | 3 pts exacto / 2 pts dif / 1 pt ganador |
| `WINNER` | Ganador del Partido | ¿Quién gana? | `"H"` (local) / `"D"` (empate) / `"A"` (visitante) | 3 pts acierto / 0 fallo |
| `BTTS` | Ambos Anotan | ¿Anotan ambos equipos? | `"yes"` / `"no"` | 2 pts acierto / 0 fallo |
| `OU25` | Más/Menos 2.5 Goles | ¿Más o menos de 2.5 goles totales? | `"over"` / `"under"` | 2 pts acierto / 0 fallo |

> **Cómo escalar:** Para agregar un nuevo tipo (ej. "Primer equipo en marcar"), el superadmin crea un nuevo `TipoEvento` en el admin con su código, descripción y configuración de puntos. No se toca código Python.

### 2.3 Modelos de dominio

#### `TipoEvento` — Registro de tipos disponibles

```python
# apps/predictions/domain/entities.py

@dataclass
class TipoEvento:
    codigo: str          # "SCORE", "WINNER", "BTTS", "OU25"
    nombre: str          # "Marcador Exacto"
    descripcion: str     # explicación breve al jugador
    # JSON: define qué respuestas son válidas y cómo evaluarlas
    # Ejemplo WINNER: {"choices": ["H", "D", "A"]}
    # Ejemplo OU25: {"choices": ["over", "under"], "threshold": 2.5}
    config: dict
    activo: bool = True
    id: uuid.UUID = field(default_factory=uuid.uuid4)
```

#### `EventoPartido` — Evento concreto activado para un partido en una quiniela

```python
@dataclass
class EventoPartido:
    partido_id: uuid.UUID
    quiniela_id: uuid.UUID
    tipo_evento_id: uuid.UUID
    estado: EventoEstado   # ABIERTO | CERRADO | PUNTUADO | CANCELADO
    resultado: Optional[str]   # valor final una vez resuelto el partido
    plazo_cierre: datetime     # cuándo deja de aceptar pronósticos
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    creado_en: datetime = field(default_factory=datetime.utcnow)
```

#### `PronosticoEvento` — Respuesta del jugador a un evento

```python
@dataclass
class PronosticoEvento:
    usuario_id: uuid.UUID
    evento_partido_id: uuid.UUID
    valor: str           # "2-1", "H", "yes", "over", etc.
    enviado_en: datetime = field(default_factory=datetime.utcnow)
    id: uuid.UUID = field(default_factory=uuid.uuid4)
```

### 2.4 Modelos Django (infrastructure)

```python
# apps/predictions/infrastructure/models.py

class TipoEvento(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    config = models.JSONField(default=dict)   # choices válidos, threshold, etc.
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "predictions_tipo_evento"
        verbose_name = "Tipo de Evento"


class EventoPartido(models.Model):
    class Estado(models.TextChoices):
        ABIERTO   = "abierto",   "Abierto"
        CERRADO   = "cerrado",   "Cerrado"
        PUNTUADO  = "puntuado",  "Puntuado"
        CANCELADO = "cancelado", "Cancelado"

    partido     = models.ForeignKey("tournaments.Match", on_delete=models.CASCADE,
                                     related_name="eventos")
    quiniela    = models.ForeignKey("quinielas.Quiniela", on_delete=models.CASCADE,
                                     related_name="eventos")
    tipo_evento = models.ForeignKey(TipoEvento, on_delete=models.PROTECT,
                                     related_name="eventos")
    estado      = models.CharField(max_length=20, choices=Estado.choices,
                                    default=Estado.ABIERTO)
    resultado   = models.CharField(max_length=50, blank=True, null=True)
    plazo_cierre = models.DateTimeField()

    class Meta:
        db_table = "predictions_evento_partido"
        unique_together = ("partido", "quiniela", "tipo_evento")
        verbose_name = "Evento de Partido"


class PronosticoEvento(models.Model):
    usuario       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                       related_name="pronosticos_eventos")
    evento_partido = models.ForeignKey(EventoPartido, on_delete=models.CASCADE,
                                        related_name="pronosticos")
    valor         = models.CharField(max_length=50)
    enviado_en    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "predictions_pronostico_evento"
        unique_together = ("usuario", "evento_partido")
        verbose_name = "Pronóstico de Evento"
```

> **Nota:** El modelo `Prediction` existente (`home_goals` + `away_goals`) se mantiene como retrocompatibilidad durante la transición. El tipo `SCORE` del nuevo sistema reemplazará su funcionalidad a mediano plazo. No eliminar hasta migrar datos.

### 2.5 Lógica de cierre de plazo

```python
# apps/predictions/domain/entities.py

@dataclass
class EventoPartido:
    ...
    def esta_abierto(self) -> bool:
        from datetime import datetime, timezone
        return (
            self.estado == EventoEstado.ABIERTO
            and datetime.now(timezone.utc) < self.plazo_cierre
        )
```

El `plazo_cierre` se calcula al crear el `EventoPartido`:
```
plazo_cierre = partido.match_date - timedelta(minutes=PREDICTION_DEADLINE_MINUTES)
```

### 2.6 Validación de respuestas

Cada `TipoEvento` tiene un `config` JSON que define las respuestas válidas. El servicio de aplicación valida antes de guardar:

```python
# apps/predictions/application/services.py

class PredictionService:
    def validar_valor(self, tipo_evento: TipoEvento, valor: str) -> bool:
        if "choices" in tipo_evento.config:
            return valor in tipo_evento.config["choices"]
        if tipo_evento.codigo == "SCORE":
            # formato "X-Y" donde X, Y son enteros >= 0
            import re
            return bool(re.match(r"^\d{1,2}-\d{1,2}$", valor))
        return False
```

### 2.7 Panel del Superadmin — Gestión de eventos

El superadmin activa eventos para una quiniela + partido desde el panel `/admin/`:

1. Ve la lista de `EventoPartido` filtrable por quiniela y partido.
2. Puede crear múltiples `EventoPartido` para el mismo partido (uno por tipo de evento).
3. Puede marcar un evento como `CANCELADO` si el partido se pospone.
4. Puede ingresar el `resultado` manualmente o dejar que el sistema lo calcule automáticamente desde la API.

---

## 3. Módulo B — Motor de Puntuación Riguroso

### 3.1 Principios de diseño

| Principio | Implementación |
|-----------|---------------|
| **Idempotente** | Recalcular el mismo evento siempre produce el mismo resultado. Upsert, no insert. |
| **Auditable** | Cada `PuntuacionEvento` registra qué valor pronosticó, qué resultado hubo, qué regla aplicó y cuántos puntos dio. |
| **Configurable por quiniela** | Los puntos por tipo de acierto se pueden sobreescribir en `ConfiguracionPuntos`. Si no hay config específica, usa defaults globales. |
| **Atómico** | Todo el cálculo de un evento ocurre en una transacción. Nunca hay estado parcial. |
| **Sin efectos secundarios en recálculo** | Re-ejecutar `calcular_puntos_evento(evento_id)` no crea duplicados ni envía notificaciones duplicadas. |

### 3.2 Reglas de puntuación por tipo de evento

#### Tipo `SCORE` (marcador exacto)

| Condición | Puntos | Código de acierto |
|-----------|--------|-------------------|
| Marcador exacto (ej: 2-1 = 2-1) | 3 | `EXACT` |
| Diferencia de goles exacta + ganador correcto (ej: 3-1 pronos, 2-0 real → +1 diferencia, mismo ganador) | 2 | `GOAL_DIFF` |
| Solo ganador correcto (o empate correcto) | 1 | `WINNER` |
| Ninguno de los anteriores | 0 | `MISS` |

> **Definición de GOAL_DIFF:** `(home_pronos - away_pronos) == (home_real - away_real)` Y el ganador es el mismo.

#### Tipos binarios (`WINNER`, `BTTS`, `OU25`)

| Condición | Puntos | Código de acierto |
|-----------|--------|-------------------|
| Valor correcto | `puntos_acierto` (configurable, default 2-3) | `HIT` |
| Valor incorrecto | 0 | `MISS` |

### 3.3 Modelos de dominio

#### `ReglaPuntuacion` — Lookup table de puntos

```python
@dataclass
class ReglaPuntuacion:
    tipo_evento_id: uuid.UUID
    quiniela_id: Optional[uuid.UUID]   # None = regla global/default
    codigo_acierto: str                # "EXACT", "GOAL_DIFF", "WINNER", "HIT", "MISS"
    puntos: int
```

#### `PuntuacionEvento` — Registro de puntos ganados

```python
@dataclass
class PuntuacionEvento:
    usuario_id: uuid.UUID
    evento_partido_id: uuid.UUID
    quiniela_id: uuid.UUID
    valor_pronosticado: str    # qué dijo el jugador
    valor_resultado: str       # qué pasó realmente
    codigo_acierto: str        # "EXACT", "HIT", "MISS", etc.
    puntos: int
    calculado_en: datetime
    id: uuid.UUID = field(default_factory=uuid.uuid4)
```

### 3.4 Modelos Django (infrastructure)

```python
# apps/scoring/infrastructure/models.py

class ReglaPuntuacion(models.Model):
    tipo_evento  = models.ForeignKey("predictions.TipoEvento", on_delete=models.CASCADE,
                                      related_name="reglas")
    quiniela     = models.ForeignKey("quinielas.Quiniela", on_delete=models.CASCADE,
                                      null=True, blank=True, related_name="reglas_puntos")
    codigo_acierto = models.CharField(max_length=20)   # EXACT, GOAL_DIFF, WINNER, HIT, MISS
    puntos         = models.SmallIntegerField()

    class Meta:
        db_table = "scoring_regla_puntuacion"
        unique_together = ("tipo_evento", "quiniela", "codigo_acierto")
        verbose_name = "Regla de Puntuación"

    def __str__(self):
        scope = f"[{self.quiniela}]" if self.quiniela else "[global]"
        return f"{self.tipo_evento.codigo} {scope} {self.codigo_acierto} → {self.puntos}pts"


class PuntuacionEvento(models.Model):
    usuario            = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                            related_name="puntuaciones")
    evento_partido     = models.ForeignKey("predictions.EventoPartido", on_delete=models.CASCADE,
                                            related_name="puntuaciones")
    quiniela           = models.ForeignKey("quinielas.Quiniela", on_delete=models.CASCADE,
                                            related_name="puntuaciones")
    valor_pronosticado = models.CharField(max_length=50)
    valor_resultado    = models.CharField(max_length=50)
    codigo_acierto     = models.CharField(max_length=20)
    puntos             = models.SmallIntegerField(default=0)
    calculado_en       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scoring_puntuacion_evento"
        unique_together = ("usuario", "evento_partido")
        verbose_name = "Puntuación de Evento"
```

> **Nota:** El modelo `Score` existente se mantiene durante la transición. `PuntuacionEvento` es el reemplazo definitivo. Migración de datos en sprint 2.

### 3.5 Motor de puntuación — Algoritmo

```python
# apps/scoring/application/services.py

class ScoringService:

    def calcular_puntos_evento(self, evento_partido_id: uuid.UUID) -> list[PuntuacionEvento]:
        """
        Idempotente: puede llamarse múltiples veces sin efectos secundarios.
        Usa upsert (update_or_create) para cada puntuación.
        """
        with transaction.atomic():
            evento = self._repo.get_evento_partido(evento_partido_id)

            if not evento.resultado:
                raise EventoSinResultadoError(evento_partido_id)

            pronosticos = self._repo.get_pronosticos_evento(evento_partido_id)
            resultados = []

            for pronostico in pronosticos:
                codigo_acierto = self._evaluar(
                    tipo_evento=evento.tipo_evento,
                    valor_pronosticado=pronostico.valor,
                    valor_resultado=evento.resultado,
                )
                puntos = self._resolver_puntos(
                    tipo_evento_id=evento.tipo_evento_id,
                    quiniela_id=evento.quiniela_id,
                    codigo_acierto=codigo_acierto,
                )
                # UPSERT — garantiza idempotencia
                puntuacion = self._repo.upsert_puntuacion(
                    usuario_id=pronostico.usuario_id,
                    evento_partido_id=evento_partido_id,
                    quiniela_id=evento.quiniela_id,
                    valor_pronosticado=pronostico.valor,
                    valor_resultado=evento.resultado,
                    codigo_acierto=codigo_acierto,
                    puntos=puntos,
                )
                resultados.append(puntuacion)

            # Marcar evento como PUNTUADO
            self._repo.marcar_evento_puntuado(evento_partido_id)

            return resultados

    def _evaluar(self, tipo_evento, valor_pronosticado: str, valor_resultado: str) -> str:
        if tipo_evento.codigo == "SCORE":
            return self._evaluar_score(valor_pronosticado, valor_resultado)
        # Tipos binarios: choices simples
        return "HIT" if valor_pronosticado == valor_resultado else "MISS"

    def _evaluar_score(self, pronostico: str, resultado: str) -> str:
        ph, pa = map(int, pronostico.split("-"))
        rh, ra = map(int, resultado.split("-"))

        if ph == rh and pa == ra:
            return "EXACT"

        def ganador(h, a):
            if h > a: return "H"
            if a > h: return "A"
            return "D"

        if (ph - pa) == (rh - ra) and ganador(ph, pa) == ganador(rh, ra):
            return "GOAL_DIFF"

        if ganador(ph, pa) == ganador(rh, ra):
            return "WINNER"

        return "MISS"

    def _resolver_puntos(self, tipo_evento_id, quiniela_id, codigo_acierto) -> int:
        # Busca regla específica de quiniela primero, luego global
        regla = self._repo.get_regla(tipo_evento_id, quiniela_id, codigo_acierto)
        if regla is None:
            regla = self._repo.get_regla(tipo_evento_id, None, codigo_acierto)
        return regla.puntos if regla else 0
```

### 3.6 Datos iniciales — Reglas globales por defecto

Al correr migraciones, se insertan las reglas globales:

```python
# apps/scoring/migrations/XXXX_seed_reglas_globales.py

REGLAS_DEFAULTS = [
    # SCORE
    ("SCORE", "EXACT",     3),
    ("SCORE", "GOAL_DIFF", 2),
    ("SCORE", "WINNER",    1),
    ("SCORE", "MISS",      0),
    # WINNER (1X2)
    ("WINNER", "HIT",  3),
    ("WINNER", "MISS", 0),
    # BTTS
    ("BTTS", "HIT",  2),
    ("BTTS", "MISS", 0),
    # OU25
    ("OU25", "HIT",  2),
    ("OU25", "MISS", 0),
]
```

### 3.7 Trigger del cálculo

El cálculo se dispara en dos momentos:
1. **Automático:** cuando `sync_results` actualiza el resultado de un partido y detecta que todos los eventos asociados tienen resultado → encola `calcular_puntos_evento` en django-q2.
2. **Manual:** superadmin puede forzar desde el panel `/admin/` → acción "Calcular puntos" en `EventoPartido`.

---

## 4. Módulo C — Ranking por Fecha y Acumulado

### 4.1 Concepto de "Fecha" (Jornada)

Una **Fecha** (o jornada) agrupa los partidos de una misma semana/ronda de un torneo. Los jugadores compiten por quién acumula más puntos en esa fecha. Al final de la quiniela, se suman todos los puntos de todas las fechas para el ranking general.

### 4.2 Modelo de dominio — `Fecha`

```python
# apps/tournaments/domain/entities.py

@dataclass
class Fecha:
    torneo_id: uuid.UUID
    numero: int           # 1, 2, 3... número de jornada
    nombre: str           # "Jornada 1", "Cuartos de Final"
    fecha_inicio: date
    fecha_fin: date
    id: uuid.UUID = field(default_factory=uuid.uuid4)
```

El modelo `Match` se actualiza para incluir `fecha_id`:
```python
# Nuevo campo en Match
fecha_id: Optional[uuid.UUID] = None
```

### 4.3 Modelos Django — `Fecha` y actualización de `Match`

```python
# apps/tournaments/infrastructure/models.py (nuevos/modificados)

class Fecha(models.Model):
    torneo   = models.ForeignKey("tournaments.Tournament", on_delete=models.CASCADE,
                                  related_name="fechas")
    numero   = models.PositiveSmallIntegerField()
    nombre   = models.CharField(max_length=100)   # "Jornada 1", "Cuartos de Final"
    fecha_inicio = models.DateField()
    fecha_fin    = models.DateField()

    class Meta:
        db_table = "tournaments_fecha"
        unique_together = ("torneo", "numero")
        ordering = ["numero"]
        verbose_name = "Fecha / Jornada"


# En Match — agregar campo:
class Match(models.Model):
    ...
    fecha = models.ForeignKey(Fecha, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name="partidos")
```

### 4.4 Modelo de Ranking — `RankingFecha`

Snapshot materializado del ranking de jugadores por fecha en una quiniela.

```python
class RankingFecha(models.Model):
    quiniela  = models.ForeignKey("quinielas.Quiniela", on_delete=models.CASCADE,
                                   related_name="rankings_fecha")
    fecha     = models.ForeignKey("tournaments.Fecha", on_delete=models.CASCADE,
                                   related_name="rankings")
    usuario   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name="rankings_fecha")
    puntos    = models.SmallIntegerField(default=0)
    posicion  = models.PositiveSmallIntegerField(default=0)
    calculado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scoring_ranking_fecha"
        unique_together = ("quiniela", "fecha", "usuario")
        ordering = ["posicion"]
        verbose_name = "Ranking por Fecha"
```

### 4.5 Modelo de Ranking — `RankingAcumulado`

Snapshot materializado del ranking general (todos los puntos históricos).

```python
class RankingAcumulado(models.Model):
    quiniela  = models.ForeignKey("quinielas.Quiniela", on_delete=models.CASCADE,
                                   related_name="ranking_acumulado")
    usuario   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name="ranking_acumulado")
    puntos_total    = models.SmallIntegerField(default=0)
    posicion        = models.PositiveSmallIntegerField(default=0)
    fechas_jugadas  = models.PositiveSmallIntegerField(default=0)
    exactos_total   = models.PositiveSmallIntegerField(default=0)
    aciertos_total  = models.PositiveSmallIntegerField(default=0)
    calculado_en    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scoring_ranking_acumulado"
        unique_together = ("quiniela", "usuario")
        ordering = ["posicion"]
        verbose_name = "Ranking Acumulado"
```

> **Por qué snapshots materializados en lugar de vistas calculadas en tiempo real:**
> - Las consultas de ranking son frecuentes y lentas si calculan en tiempo real con muchos jugadores.
> - Los datos cambian solo cuando hay resultados nuevos (no continuamente).
> - El snapshot permite mostrar rankings instantáneamente sin JOIN pesados.
> - Se recalcula después de cada cálculo de puntuación — proceso controlado.

### 4.6 Servicio de ranking

```python
# apps/scoring/application/services.py

class RankingService:

    def recalcular_ranking_fecha(self, quiniela_id: uuid.UUID, fecha_id: uuid.UUID) -> None:
        """Recalcula y materializa el ranking de jugadores para una fecha."""
        with transaction.atomic():
            # Suma de puntos por usuario en los eventos de los partidos de esta fecha
            puntos_por_usuario = self._repo.get_puntos_por_fecha(quiniela_id, fecha_id)

            # Ordenar y asignar posiciones (con manejo de empates)
            ranking = self._asignar_posiciones(puntos_por_usuario)

            # Upsert — idempotente
            for entrada in ranking:
                self._repo.upsert_ranking_fecha(
                    quiniela_id=quiniela_id,
                    fecha_id=fecha_id,
                    usuario_id=entrada.usuario_id,
                    puntos=entrada.puntos,
                    posicion=entrada.posicion,
                )

    def recalcular_ranking_acumulado(self, quiniela_id: uuid.UUID) -> None:
        """Recalcula el ranking general sumando todos los puntos históricos."""
        with transaction.atomic():
            stats_por_usuario = self._repo.get_stats_acumuladas(quiniela_id)
            ranking = self._asignar_posiciones(stats_por_usuario)

            for entrada in ranking:
                self._repo.upsert_ranking_acumulado(
                    quiniela_id=quiniela_id,
                    usuario_id=entrada.usuario_id,
                    puntos_total=entrada.puntos,
                    posicion=entrada.posicion,
                    fechas_jugadas=entrada.fechas_jugadas,
                    exactos_total=entrada.exactos_total,
                    aciertos_total=entrada.aciertos_total,
                )

    def _asignar_posiciones(self, puntos_por_usuario: list) -> list:
        """
        Ordena por puntos descendente.
        En empate: misma posición, el siguiente toma la posición correcta (dense rank).
        """
        sorted_list = sorted(puntos_por_usuario, key=lambda x: x.puntos, reverse=True)
        posicion = 1
        for i, entrada in enumerate(sorted_list):
            if i > 0 and sorted_list[i-1].puntos != entrada.puntos:
                posicion = i + 1
            entrada.posicion = posicion
        return sorted_list
```

### 4.7 Trigger del recálculo de rankings

Cadena de eventos después de que llega un resultado:

```
API externa / entrada manual
        ↓
partido.estado = FINISHED
partido.resultado registrado
        ↓
[django-q2 task] calcular_puntos_evento(evento_id) para cada evento del partido
        ↓  (al completarse todos los eventos del partido)
[django-q2 task] recalcular_ranking_fecha(quiniela_id, fecha_id)
        ↓  (al completarse todos los partidos de la fecha)
[django-q2 task] recalcular_ranking_acumulado(quiniela_id)
        ↓
Notificación: "Fecha X finalizada — tu posición: #N con X puntos"
```

### 4.8 Vistas de ranking

#### Ranking por fecha — Vista pública / jugadores

```
GET /quinielas/<slug>/fechas/<fecha_numero>/ranking/
```

Muestra tabla con: posición, avatar, nombre, puntos en la fecha. Los primeros 3 lugares con badge destacado. Para usuarios públicos: top 10. Para jugadores inscritos: completo.

#### Ranking acumulado — Vista del leaderboard principal

```
GET /quinielas/<slug>/leaderboard/
```

Tabla principal de la quiniela. Columnas: posición, jugador, pts totales, exactos, aciertos, fechas jugadas. Con filtro por fecha específica.

#### Historial personal

```
GET /quinielas/<slug>/mi-historial/
```

Vista privada del jugador: tabla de sus puntos fecha por fecha, eventos acertados/fallados, evolución de posición.

---

## 5. Integración entre módulos

### 5.1 Cadena de responsabilidades

```
SuperAdmin activa EventoPartido (Módulo A)
        ↓
Jugador envía PronosticoEvento dentro del plazo (Módulo A)
        ↓
Sistema recibe resultado del partido
        ↓
EventoPartido.resultado = valor real
EventoPartido.estado = PUNTUADO
        ↓
ScoringService.calcular_puntos_evento() → crea PuntuacionEvento (Módulo B)
        ↓
RankingService.recalcular_ranking_fecha() → actualiza RankingFecha (Módulo C)
        ↓
RankingService.recalcular_ranking_acumulado() → actualiza RankingAcumulado (Módulo C)
        ↓
Notificación al jugador con resultado y nueva posición
```

### 5.2 Invariantes del sistema

| Invariante | Dónde se garantiza |
|------------|--------------------|
| No se puede pronosticar después del `plazo_cierre` | `EventoPartido.esta_abierto()` en capa de dominio |
| No se puede ver pronósticos ajenos antes del cierre | Verificación en vista antes de serializar |
| Los puntos solo se calculan si `EventoPartido.resultado is not None` | `ScoringService` lanza `EventoSinResultadoError` |
| Los rankings siempre son coherentes con `PuntuacionEvento` | `RankingService` siempre reconstruye desde cero con upsert |
| Recalcular no duplica puntos | UNIQUE constraint en `(usuario, evento_partido)` + upsert |

---

## 6. Modelos Django — Resumen

### Nuevos modelos a crear

| App | Modelo | Propósito |
|-----|--------|-----------|
| `predictions` | `TipoEvento` | Catálogo de tipos de evento (SCORE, WINNER, BTTS, OU25...) |
| `predictions` | `EventoPartido` | Evento activado para un partido en una quiniela |
| `predictions` | `PronosticoEvento` | Respuesta del jugador a un evento |
| `tournaments` | `Fecha` | Agrupación de partidos por jornada |
| `scoring` | `ReglaPuntuacion` | Puntos por tipo de evento y código de acierto |
| `scoring` | `PuntuacionEvento` | Registro de puntos obtenidos por evento |
| `scoring` | `RankingFecha` | Snapshot de ranking por fecha |
| `scoring` | `RankingAcumulado` | Snapshot de ranking general |

### Modelos modificados

| App | Modelo | Cambio |
|-----|--------|--------|
| `tournaments` | `Match` | Agregar FK a `Fecha` (nullable) |

### Modelos que se mantienen (retrocompatibilidad)

| App | Modelo | Acción |
|-----|--------|--------|
| `predictions` | `Prediction` | Mantener hasta migrar datos a `PronosticoEvento` con tipo `SCORE` |
| `scoring` | `Score` | Mantener hasta migrar datos a `PuntuacionEvento` |

---

## 7. Flujo de datos completo

```
[SuperAdmin]
  → Crea Fecha (jornada) en el torneo
  → Activa EventoPartido por cada tipo de evento para cada partido de la fecha
  → Panel admin muestra: partido / tipo evento / estado / resultado

[Jugador]
  → Ve los partidos de la quiniela agrupados por Fecha
  → Para cada partido: puede pronosticar cada EventoPartido activo
  → Al enviar: sistema valida plazo + valor válido según tipo
  → Vista "mis pronósticos": muestra valor enviado + (si cerrado) resultado + puntos

[Sistema — al recibir resultado de la API]
  → Actualiza Match.home_score / Match.away_score / Match.status = FINISHED
  → Para cada EventoPartido del partido:
      - Calcula resultado del evento según su tipo (ej. BTTS: ¿0+2=2 → sí → "yes")
      - Guarda EventoPartido.resultado
      - Encola calcular_puntos_evento()
  → calcular_puntos_evento() →  PuntuacionEvento (upsert por jugador)
  → Si todos los partidos de la Fecha están PUNTUADOS:
      - recalcular_ranking_fecha()
      - recalcular_ranking_acumulado()
      - Enviar notificaciones

[Usuario Público]
  → Ve top 10 del RankingAcumulado en /quinielas/<slug>/
  → No puede ver pronósticos de otros jugadores
```

---

## 8. Endpoints nuevos

### Predictions — Gestión de eventos

```
# Admin / SuperAdmin
GET  /admin/predictions/tipoevento/          → lista tipos de evento
POST /admin/predictions/eventopartido/add/   → activar evento para un partido

# Jugador
GET  /quinielas/<slug>/fechas/               → lista de fechas con estado
GET  /quinielas/<slug>/fechas/<num>/         → detalle de fecha: partidos + eventos
POST /quinielas/<slug>/eventos/<evento_id>/pronosticar/   → enviar pronóstico
GET  /quinielas/<slug>/mis-pronosticos/      → historial de pronósticos del jugador
```

### Scoring — Rankings

```
GET /quinielas/<slug>/leaderboard/                     → ranking acumulado (público: top 10 / inscrito: completo)
GET /quinielas/<slug>/fechas/<num>/ranking/            → ranking de la fecha (público: top 10 / inscrito: completo)
GET /quinielas/<slug>/mi-historial/                    → historial personal del jugador (solo inscrito)
GET /quinielas/<slug>/partidos/<match_id>/resultados/  → pronósticos + puntos de todos (tras cierre de plazo)
```

### Admin — Forzar cálculos

```
POST /admin/scoring/puntuacionevento/calcular/<evento_id>/   → forzar cálculo manual
POST /admin/scoring/rankingfecha/recalcular/                 → recalcular ranking de fecha
POST /admin/scoring/rankingacumulado/recalcular/             → recalcular ranking general
```

---

## 9. Orden de implementación

### Sprint 1 — Cimientos (sin romper lo existente)

1. Crear modelo `Fecha` en `tournaments` + migración + admin.
2. Agregar FK `fecha` a `Match` (nullable) + migración.
3. Crear modelos `TipoEvento`, `EventoPartido`, `PronosticoEvento` en `predictions` + migraciones.
4. Seed de datos: 4 `TipoEvento` iniciales (SCORE, WINNER, BTTS, OU25).
5. Crear modelos `ReglaPuntuacion`, `PuntuacionEvento` en `scoring` + migraciones.
6. Seed de datos: reglas globales por defecto.

### Sprint 2 — Lógica de negocio

7. `PredictionService.validar_y_guardar_pronostico()` — con validación de plazo y valor.
8. `ScoringService.calcular_puntos_evento()` — motor de puntuación idempotente.
9. `ScoringService._evaluar_score()` y `_evaluar_binario()` — evaluadores por tipo.
10. Tests unitarios del motor de puntuación (sin Django, solo lógica de dominio).

### Sprint 3 — Rankings

11. Crear modelos `RankingFecha`, `RankingAcumulado` + migraciones.
12. `RankingService.recalcular_ranking_fecha()`.
13. `RankingService.recalcular_ranking_acumulado()` con dense rank en empates.
14. Integración con la cadena de tareas django-q2.

### Sprint 4 — Vistas y UX

15. Vistas de jugador: fechas, eventos por partido, enviar pronóstico.
16. Vista leaderboard con tabs (acumulado / por fecha).
17. Vista "mi historial" — puntos fecha por fecha, evolución.
18. Vista "resultados del partido" — pronósticos de todos tras cierre.
19. Panel admin: acciones manuales de cálculo.
20. Notificaciones post-fecha.

---

## 10. Decisiones de diseño

### ¿Por qué `PronosticoEvento.valor` es `CharField` y no campos separados?

El `valor` (`"2-1"`, `"H"`, `"yes"`, `"over"`) es un string simple que cada `TipoEvento` sabe cómo validar e interpretar. Usar campos separados por tipo requeriría una tabla por tipo o columnas nullable — más complejidad sin beneficio real. El string es suficientemente estructurado para todos los tipos MVP.

### ¿Por qué snapshots materializados para rankings y no vistas SQL en tiempo real?

El ranking se consulta en cada página de la quiniela. Con 50+ jugadores y 10+ fechas, calcular en tiempo real implica un SUM+GROUP BY+ORDER BY en cada request. Los snapshots se actualizan solo cuando hay nuevos resultados (eventos controlados). El trade-off es clarísimo: latencia de lectura ~0ms vs. costo de escritura despreciable.

### ¿Por qué el tipo `SCORE` coexiste con el `Prediction` existente?

Para no romper el MVP actual mientras se desarrolla el nuevo sistema. Los dos modelos conviven hasta que todos los pronósticos existentes se migren a `PronosticoEvento`. La migración es un script de management command que corre una sola vez.

### ¿Por qué `ReglaPuntuacion` con lookup table y no hardcoded?

El superadmin puede querer ajustar los puntos de una quiniela específica sin deployar código. Por ejemplo, una quiniela "premium" donde el marcador exacto vale 5 puntos. La jerarquía (regla de quiniela > regla global) resuelve el caso de uso sin complejidad excesiva.

### Manejo de empates en el ranking

Se usa **dense rank**: si tres jugadores tienen 10 puntos, los tres son posición 1 y el siguiente es posición 2 (no posición 4). Es la convención más justa y esperada por los usuarios.

---

*Este documento es el spec de referencia para los sprints de implementación del core competitivo de Polla Futbolera v3.0. Cualquier decisión de implementación no cubierta aquí debe seguir los principios de la arquitectura hexagonal documentados en spec.md v2.0: el dominio no conoce Django ni la base de datos.*
