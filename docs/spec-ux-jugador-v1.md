# Spec UX/UI — Pantallas del Jugador v1

**Versión:** 1.0  
**Fecha:** 2026-06-04  
**Alcance:** Dashboard del jugador + Detalle de Fecha con pronósticos + Pantalla de pronosticar  
**Design System:** Stadium Night (dark · mobile-first · 480px max)  
**Branch sugerida:** `feat/ux-jugador-dashboard`

---

## 0. Contexto y objetivo

El jugador es nuestro cliente principal. Hoy sus pantallas son funcionales pero planas: listas sin identidad, sin contexto propio, sin el "enganche" que hace que vuelvas a abrir la app. Esta spec define las mejoras necesarias en tres pantallas críticas:

| Pantalla | Template actual | Problema central |
|---|---|---|
| **Dashboard** | `quinielas/list.html` | Muestra todas las quinielas iguales sin personalización. El jugador no sabe su posición ni qué necesita hacer hoy. |
| **Fecha / Pronósticos** | `predictions/fecha_detail.html` | Partidos planos sin escudos. Estados de eventos indistinguibles. El jugador no sabe de un vistazo qué puede/debe jugar. |
| **Pronosticar** | `predictions/pronosticar_evento.html` | Badges de 3 letras en lugar de escudos. Botones de radio básicos. Experiencia sin identidad visual. |

**Principio guía:** Cada pantalla debe responder a la pregunta "¿qué hago yo, ahora mismo, en este reto?" con información visual instantánea.

---

## 1. PANTALLA 1 — Dashboard del Jugador

### 1.1 Wireframe ASCII

```
╔══════════════════════════════════════════╗
║ ← [back]        Toque         [🔔]      ║  ← header (sin back para home)
╠══════════════════════════════════════════╣
║                                          ║
║  ┌──────────────────────────────────┐    ║
║  │  Hola, andrei 👋                 │    ║  ← hero greeting card
║  │  Miércoles 4 de junio            │    ║
║  │                                  │    ║
║  │  ┌────────┐  ┌────────┐          │    ║
║  │  │ #3     │  │ 247pts │          │    ║  ← stat pills (multi-quiniela suma)
║  │  │ posic. │  │ totales│          │    ║
║  │  └────────┘  └────────┘          │    ║
║  └──────────────────────────────────┘    ║
║                                          ║
║  MIS RETOS ─────────────────────────     ║  ← section label
║                                          ║
║  ┌──────────────────────────────────┐    ║
║  │ 🏆 Copa del Mundo 2026           │    ║  ← reto card
║  │    Mundial Toque · Activo        │    ║
║  │ ─────────────────────────────    │    ║
║  │  #2  ·  124 pts  ·  8 exactos    │    ║
║  │ ─────────────────────────────    │    ║
║  │  📋 Jornada 3 · 3 jugadas abiert.│    ║
║  │                                  │    ║
║  │  [▶ JUGAR AHORA]  [→ Ranking]    │    ║
║  └──────────────────────────────────┘    ║
║                                          ║
║  ┌──────────────────────────────────┐    ║
║  │ 🏆 Champions League              │    ║
║  │    Reto de Oficina · Activo      │    ║
║  │ ─────────────────────────────    │    ║
║  │  #7  ·  89 pts  ·  5 exactos     │    ║
║  │ ─────────────────────────────    │    ║
║  │  ✅ Al día — nada pendiente      │    ║
║  │                                  │    ║
║  │  [→ Ver jornadas]  [→ Ranking]   │    ║
║  └──────────────────────────────────┘    ║
║                                          ║
║  PRÓXIMOS PARTIDOS ─────────────────     ║  ← section label
║                                          ║
║  ┌──────────────────────────────────┐    ║
║  │  [🇦🇷] Argentina   vs  [🇧🇷] Brasil │  ← próximo partido strip
║  │         Hoy · 21:00              │    ║
║  └──────────────────────────────────┘    ║
║  ┌──────────────────────────────────┐    ║
║  │  [⚽] Real Madrid  vs  [⚽] Barça │
║  │         Mañana · 20:45           │    ║
║  └──────────────────────────────────┘    ║
║                                          ║
╠══════════════════════════════════════════╣
║  [Retos]  [Torneos]  [▶]  [🔔]  [👤]   ║  ← bottom nav
╚══════════════════════════════════════════╝
```

**Estado: sin retos inscritos (jugador nuevo)**
```
╔══════════════════════════════════════════╗
║  Hola, andrei 👋                         ║
║  Miércoles 4 de junio                    ║
╠══════════════════════════════════════════╣
║                                          ║
║  ┌──────────────────────────────────┐    ║
║  │  🏟 Todavía no estás en ningún   │    ║
║  │     reto activo.                 │    ║
║  │                                  │    ║
║  │  Pedile al moderador que te una  │    ║
║  │  a un reto para empezar a jugar. │    ║
║  └──────────────────────────────────┘    ║
║                                          ║
║  RETOS DISPONIBLES ─────────────────     ║
║  [lista pública de quinielas activas]    ║
╚══════════════════════════════════════════╝
```

### 1.2 Cambios en la vista — `quinielas/views.py`

```python
# quiniela_list(request) — agregar lógica para jugador autenticado

from django.utils import timezone
from datetime import timedelta
from apps.scoring.infrastructure.models import RankingAcumulado
from apps.predictions.infrastructure.models import EventoPartido, PronosticoEvento
from apps.tournaments.infrastructure.models import Match

def quiniela_list(request):
    quinielas_publicas = Quiniela.objects.filter(status="activa").select_related("tournament")
    total_jugadores = User.objects.filter(groups__name="Jugador").count()

    mis_quinielas = []
    proximos_partidos = []

    if request.user.is_authenticated:
        inscripciones = (
            Inscripcion.objects
            .filter(jugador=request.user, activa=True)
            .select_related("quiniela__tournament")
            .order_by("quiniela__name")
        )

        quiniela_ids = [i.quiniela_id for i in inscripciones]

        # Rankings del usuario en sus quinielas (1 query)
        rankings_map = {
            r.quiniela_id: r
            for r in RankingAcumulado.objects.filter(
                quiniela_id__in=quiniela_ids, usuario=request.user
            )
        }

        # Eventos abiertos sin pronóstico (1 query por quiniela — acceptable)
        for insc in inscripciones:
            q = insc.quiniela
            ranking = rankings_map.get(q.id)

            eventos_abiertos = EventoPartido.objects.filter(
                quiniela=q, estado='abierto'
            )
            eventos_sin_pronostico = eventos_abiertos.exclude(
                pronosticos__usuario=request.user
            ).count()

            # Próxima fecha con eventos abiertos
            from apps.tournaments.infrastructure.models import Fecha
            proxima_fecha = (
                Fecha.objects
                .filter(torneo=q.tournament, partidos__eventos__quiniela=q,
                        partidos__eventos__estado='abierto')
                .order_by('numero')
                .first()
            )

            mis_quinielas.append({
                "quiniela": q,
                "ranking": ranking,  # None si no tiene puntuación aún
                "eventos_pendientes": eventos_sin_pronostico,
                "proxima_fecha_nombre": proxima_fecha.nombre if proxima_fecha else None,
            })

        # Próximos partidos de los torneos del jugador
        now = timezone.now()
        proximos_partidos = list(
            Match.objects
            .filter(
                tournament__quiniela__in=quiniela_ids,
                status='scheduled',
                match_date__gte=now,
                match_date__lte=now + timedelta(hours=48),
            )
            .select_related('home_team', 'away_team', 'tournament')
            .order_by('match_date')
            .distinct()[:8]
        )

    return render(request, "quinielas/list.html", {
        "quinielas": quinielas_publicas,
        "total_jugadores": total_jugadores,
        "mis_quinielas": mis_quinielas,
        "proximos_partidos": proximos_partidos,
    })
```

### 1.3 Nuevo template — `quinielas/list.html` (sección autenticada)

Reemplazar el bloque `{% if user.is_authenticated %}` con:

```html
{% if user.is_authenticated %}

<!-- Hero Greeting -->
<div class="player-hero">
  <div class="player-hero__greeting">
    <span class="player-hero__hola">Hola, {{ user.username }}</span>
    <span class="player-hero__date">{{ "now"|date:"l j \d\e F" }}</span>
  </div>
  {% if mis_quinielas %}
  <div class="player-hero__stats">
    {% with total_pts=mis_quinielas|map_attr:"ranking"|sum_attr:"puntos_total" %}
    <div class="stat-pill">
      <span class="stat-pill__val">{{ total_pts|default:"—" }}</span>
      <span class="stat-pill__label">pts totales</span>
    </div>
    {% endwith %}
    <div class="stat-pill">
      <span class="stat-pill__val">{{ mis_quinielas|length }}</span>
      <span class="stat-pill__label">reto{{ mis_quinielas|length|pluralize:"s" }}</span>
    </div>
  </div>
  {% endif %}
</div>

<!-- Mis Retos -->
{% if mis_quinielas %}
<div class="section-label">Mis Retos</div>

{% for item in mis_quinielas %}
<div class="reto-card {% if item.eventos_pendientes > 0 %}reto-card--pending{% endif %}">
  <div class="reto-card__header">
    <div class="reto-card__icon"><i class="bi bi-trophy-fill"></i></div>
    <div class="reto-card__info">
      <span class="reto-card__name">{{ item.quiniela.name }}</span>
      <span class="reto-card__tournament">{{ item.quiniela.tournament.name }} · {{ item.quiniela.tournament.season }}</span>
    </div>
    {% if item.eventos_pendientes > 0 %}
    <span class="reto-card__badge reto-card__badge--alert">{{ item.eventos_pendientes }} pendiente{{ item.eventos_pendientes|pluralize:"s" }}</span>
    {% endif %}
  </div>

  {% if item.ranking %}
  <div class="reto-card__stats">
    <div class="reto-stat">
      <span class="reto-stat__val">#{{ item.ranking.posicion }}</span>
      <span class="reto-stat__label">posición</span>
    </div>
    <div class="reto-stat__sep">·</div>
    <div class="reto-stat">
      <span class="reto-stat__val">{{ item.ranking.puntos_total }}</span>
      <span class="reto-stat__label">pts</span>
    </div>
    <div class="reto-stat__sep">·</div>
    <div class="reto-stat">
      <span class="reto-stat__val">{{ item.ranking.exactos_total }}</span>
      <span class="reto-stat__label">exactos</span>
    </div>
  </div>
  {% else %}
  <div class="reto-card__no-ranking">
    <i class="bi bi-hourglass-split"></i> Sin puntuación aún
  </div>
  {% endif %}

  <div class="reto-card__context">
    {% if item.proxima_fecha_nombre %}
    <i class="bi bi-calendar3"></i> {{ item.proxima_fecha_nombre }}
    {% endif %}
    {% if item.eventos_pendientes > 0 %}
    · <span style="color:var(--warning);">{{ item.eventos_pendientes }} jugada{{ item.eventos_pendientes|pluralize:"s" }} abierta{{ item.eventos_pendientes|pluralize:"s" }}</span>
    {% elif item.proxima_fecha_nombre %}
    · <span style="color:var(--success);">Al día ✓</span>
    {% endif %}
  </div>

  <div class="reto-card__actions">
    <a href="{% url 'quinielas:fechas_list' slug=item.quiniela.slug %}"
       class="btn {% if item.eventos_pendientes > 0 %}btn-primary{% else %}btn-secondary{% endif %} btn-sm">
      {% if item.eventos_pendientes > 0 %}
      <i class="bi bi-pencil-fill"></i> Jugar ahora
      {% else %}
      <i class="bi bi-calendar3"></i> Ver jornadas
      {% endif %}
    </a>
    <a href="{% url 'quinielas:leaderboard' slug=item.quiniela.slug %}"
       class="btn btn-ghost btn-sm">
      <i class="bi bi-bar-chart-fill"></i> Ranking
    </a>
  </div>
</div>
{% endfor %}

{% else %}
<!-- Empty state: sin retos -->
<div class="empty-retos">
  <div class="empty-retos__icon"><i class="bi bi-shield"></i></div>
  <p class="empty-retos__title">Todavía no estás en ningún reto</p>
  <p class="empty-retos__sub">Pedile al moderador que te una a un reto para empezar a competir.</p>
</div>

<!-- Lista pública de retos disponibles para que vea qué existe -->
{% if quinielas %}
<div class="section-label" style="margin-top: var(--s6);">Retos disponibles</div>
{% for quiniela in quinielas %}
<a href="{% url 'quinielas:detail' slug=quiniela.slug %}" class="group-card">
  <div class="group-card__icon"><i class="bi bi-trophy-fill"></i></div>
  <div class="group-card__content">
    <p class="group-card__name">{{ quiniela.name }}</p>
    <span class="group-card__meta">{{ quiniela.tournament.name }} · {{ quiniela.tournament.season }}</span>
  </div>
  <i class="bi bi-chevron-right group-card__chevron"></i>
</a>
{% endfor %}
{% endif %}
{% endif %}

<!-- Próximos Partidos -->
{% if proximos_partidos %}
<div class="section-label" style="margin-top: var(--s6);">Próximos partidos</div>
<div class="matchday-strip">
  {% for match in proximos_partidos %}
  <div class="matchday-item">
    <div class="matchday-item__team matchday-item__team--home">
      {% if match.home_team.logo_url %}
      <img src="{{ match.home_team.logo_url }}" alt="{{ match.home_team.name }}" class="team-crest team-crest--sm">
      {% else %}
      <div class="team-crest team-crest--sm team-crest--fallback">{{ match.home_team.name|slice:":3"|upper }}</div>
      {% endif %}
      <span class="matchday-item__name">{{ match.home_team.name }}</span>
    </div>
    <div class="matchday-item__center">
      <span class="matchday-item__vs">VS</span>
      <span class="matchday-item__time">{{ match.match_date|date:"d/m H:i" }}</span>
    </div>
    <div class="matchday-item__team matchday-item__team--away">
      <span class="matchday-item__name">{{ match.away_team.name }}</span>
      {% if match.away_team.logo_url %}
      <img src="{{ match.away_team.logo_url }}" alt="{{ match.away_team.name }}" class="team-crest team-crest--sm">
      {% else %}
      <div class="team-crest team-crest--sm team-crest--fallback">{{ match.away_team.name|slice:":3"|upper }}</div>
      {% endif %}
    </div>
  </div>
  {% endfor %}
</div>
{% endif %}

{% else %}
<!-- Vista guest — mantener igual -->
...
{% endif %}
```

---

## 2. PANTALLA 2 — Detalle de Fecha (Partidos + Pronósticos)

### 2.1 Wireframe ASCII — Partido card

```
╔══════════════════════════════════════════╗
║ ← Jornada 3      Mundial Toque    [📊]  ║
╠══════════════════════════════════════════╣
║                                          ║
║  ╔════════════════════════════════════╗  ║
║  ║  [🇦🇷]  Argentina   3 - 1  Francia [🇫🇷] ║  ← partido header (resultado)
║  ║         Finalizado · Grupo A       ║  ║
║  ╠════════════════════════════════════╣  ║
║  ║                                    ║  ║
║  ║  ▌ Ganador del partido    [ABIERTO]║  ║  ← row abierto SIN pronóstico
║  ║  ▌ Mi pronóstico: —                ║  ║    (borde verde pulsante)
║  ║  ▌                    [▶ JUGAR]   ║  ║
║  ║                                    ║  ║
║  ║  ░ Marcador exacto    [EDITANDO]  ║  ║  ← row abierto CON pronóstico
║  ║  ░ Mi pronóstico: 2-1             ║  ║    (borde amber)
║  ║  ░                    [✎ EDITAR]  ║  ║
║  ║                                    ║  ║
║  ║  — Ambos anotan        [CERRADO]  ║  ║  ← row cerrado
║  ║    Mi pronóstico: Sí              ║  ║    (gris, opacidad reducida)
║  ║                                    ║  ║
║  ║  ✦ Más de 2.5 goles  [PUNTUADO]  ║  ║  ← row puntuado
║  ║    Mi jugada: over               ║  ║
║  ║    Resultado: over               ║  ║
║  ║    [🥇 EXACTO +10pts]            ║  ║    (badge dorado)
║  ╚════════════════════════════════════╝  ║
║                                          ║
║  ╔════════════════════════════════════╗  ║
║  ║  [⚽]  España   vs   Alemania [⚽] ║  ║  ← partido SIN resultado
║  ║        Hoy · 18:00 · Grupo C      ║  ║
║  ╠════════════════════════════════════╣  ║
║  ║  ▌ Ganador                        ║  ║
║  ║  ▌ Mi pronóstico: —   [▶ JUGAR]  ║  ║
║  ╚════════════════════════════════════╝  ║
╚══════════════════════════════════════════╝
```

### 2.2 Estados de eventos — guía de color

| Estado | Condición | Visual | Color |
|---|---|---|---|
| **ABIERTO_SIN** | `esta_abierto() AND NOT mi_pronostico` | Borde izq verde pulsante + btn verde | `--green` |
| **ABIERTO_CON** | `esta_abierto() AND mi_pronostico` | Borde izq amber + badge valor + btn ghost | `--warning` |
| **CERRADO** | `estado == 'cerrado'` | Fondo gris, opacidad 0.55, texto muted | `--text-muted` |
| **PUNTUADO_EXACTO** | `estado == 'puntuado' AND codigo == 'exact'` | Badge gold "EXACTO" | `--gold` |
| **PUNTUADO_ACIERTO** | `estado == 'puntuado' AND codigo == 'winner'` | Badge verde "ACIERTO" | `--green` |
| **PUNTUADO_FALLO** | `estado == 'puntuado' AND codigo == 'miss'` | Badge rojo "FALLO" | `--danger` |
| **PUNTUADO_SIN** | `estado == 'puntuado' AND NOT mi_pronostico` | Badge gris "SIN JUGADA" | muted |

> **Nota sobre `codigo_acierto`:** El contexto actual del template **no** incluye este dato. Hay dos opciones:
> - Opción A (recomendada): Agregar `puntuacion` al contexto de `fecha_detail_view` con un query extra.
> - Opción B (rápida): Mostrar solo el resultado sin feedback personal en Fase 1, agregar en Fase 2.

### 2.3 Cambios en la vista — `predictions/views.py`

Para la Fase 1 (sin puntuaciones en contexto), el template puede inferir el estado solo con los datos actuales. Para Fase 2, agregar:

```python
# En fecha_detail_view, después de pronos_map, agregar:
from apps.scoring.infrastructure.models import PuntuacionEvento

puntuaciones_map = {
    p.evento_partido_id: p
    for p in PuntuacionEvento.objects.filter(
        evento_partido_id__in=evento_ids,
        usuario=request.user,
        quiniela=quiniela,
    )
}

# En partidos_con_eventos, agregar puntuacion al dict de cada evento:
"eventos": [
    {
        "evento": e,
        "mi_pronostico": pronos_map.get(e.id),
        "mi_puntuacion": puntuaciones_map.get(e.id),   # nuevo
    }
    for e in eventos_by_partido.get(partido.id, [])
],
```

### 2.4 Nuevo template — `predictions/fecha_detail.html`

```html
{% extends "base.html" %}
{% block title %}{{ fecha.nombre }} — {{ quiniela.name }}{% endblock %}
{% block page_title %}{{ fecha.nombre }}{% endblock %}
{% block nav_quinielas %}active{% endblock %}

{% block header_back %}
<a href="{% url 'quinielas:fechas_list' slug=quiniela.slug %}" class="btn-icon">
  <i class="bi bi-chevron-left"></i>
</a>
{% endblock %}

{% block header_action %}
<a href="{% url 'quinielas:ranking_fecha' slug=quiniela.slug numero=fecha.numero %}" class="btn-icon">
  <i class="bi bi-bar-chart-fill"></i>
</a>
{% endblock %}

{% block content %}

{% for item in partidos_con_eventos %}
{% with partido=item.partido %}
<div class="partido-card">

  <!-- Partido header con escudos -->
  <div class="partido-card__header">
    <div class="partido-team partido-team--home">
      {% if partido.home_team.logo_url %}
      <img src="{{ partido.home_team.logo_url }}" alt="{{ partido.home_team.name }}"
           class="team-crest team-crest--md">
      {% else %}
      <div class="team-crest team-crest--md team-crest--fallback">{{ partido.home_team.name|slice:":3"|upper }}</div>
      {% endif %}
      <span class="partido-team__name">{{ partido.home_team.name }}</span>
    </div>

    <div class="partido-card__center">
      {% if partido.home_score is not None %}
      <span class="partido-score">{{ partido.home_score }}<span class="partido-score__sep">-</span>{{ partido.away_score }}</span>
      <span class="partido-card__status partido-card__status--done">Final</span>
      {% elif partido.status == 'in_progress' %}
      <span class="partido-score partido-score--live">EN VIVO</span>
      {% else %}
      <span class="partido-card__time">{{ partido.match_date|date:"d M" }}</span>
      <span class="partido-card__hour">{{ partido.match_date|date:"H:i" }}</span>
      {% endif %}
    </div>

    <div class="partido-team partido-team--away">
      <span class="partido-team__name">{{ partido.away_team.name }}</span>
      {% if partido.away_team.logo_url %}
      <img src="{{ partido.away_team.logo_url }}" alt="{{ partido.away_team.name }}"
           class="team-crest team-crest--md">
      {% else %}
      <div class="team-crest team-crest--md team-crest--fallback">{{ partido.away_team.name|slice:":3"|upper }}</div>
      {% endif %}
    </div>
  </div>

  <!-- Eventos del partido -->
  {% if item.eventos %}
  <div class="partido-card__events">
    {% for ev_item in item.eventos %}
    {% with ev=ev_item.evento prono=ev_item.mi_pronostico punt=ev_item.mi_puntuacion %}

    {% if ev.esta_abierto %}
      {% if prono %}
      <!-- ABIERTO CON PRONÓSTICO -->
      <div class="ev-row ev-row--editando">
        <div class="ev-row__left">
          <span class="ev-row__name">{{ ev.tipo_evento.nombre }}</span>
          <span class="ev-row__my-pick">
            <i class="bi bi-pencil-fill" style="font-size:10px;margin-right:3px;"></i>
            {% if ev.tipo_evento.codigo == 'WINNER' %}
              {% if prono == 'H' %}{{ partido.home_team.name }}{% elif prono == 'D' %}Empate{% elif prono == 'A' %}{{ partido.away_team.name }}{% else %}{{ prono }}{% endif %}
            {% else %}
              {{ prono }}
            {% endif %}
          </span>
        </div>
        <a href="{% url 'quinielas:pronosticar_evento' slug=quiniela.slug evento_id=ev.id %}"
           class="btn btn-ghost btn-sm ev-row__btn">
          <i class="bi bi-pencil"></i> Editar
        </a>
      </div>
      {% else %}
      <!-- ABIERTO SIN PRONÓSTICO -->
      <div class="ev-row ev-row--abierto">
        <div class="ev-row__left">
          <span class="ev-row__name">{{ ev.tipo_evento.nombre }}</span>
          <span class="ev-row__deadline text-xs">
            <i class="bi bi-clock"></i> Cierra {{ ev.plazo_cierre|date:"d/m H:i" }}
          </span>
        </div>
        <a href="{% url 'quinielas:pronosticar_evento' slug=quiniela.slug evento_id=ev.id %}"
           class="btn btn-primary btn-sm ev-row__btn">
          <i class="bi bi-pencil-fill"></i> Jugar
        </a>
      </div>
      {% endif %}

    {% elif ev.estado == 'puntuado' %}
      <!-- PUNTUADO -->
      <div class="ev-row ev-row--puntuado">
        <div class="ev-row__left">
          <span class="ev-row__name">{{ ev.tipo_evento.nombre }}</span>
          <div class="ev-row__result-detail">
            <span class="text-xs">Resultado: <strong>
              {% if ev.tipo_evento.codigo == 'WINNER' %}
                {% if ev.resultado == 'H' %}{{ partido.home_team.name }}{% elif ev.resultado == 'D' %}Empate{% elif ev.resultado == 'A' %}{{ partido.away_team.name }}{% else %}{{ ev.resultado }}{% endif %}
              {% else %}
                {{ ev.resultado }}
              {% endif %}
            </strong></span>
            {% if prono %}
            <span class="text-xs text-muted">Mi jugada: {{ prono }}</span>
            {% endif %}
          </div>
        </div>
        <div class="ev-row__right">
          {% if punt %}
            {% if punt.codigo_acierto == 'exact' %}
            <span class="outcome-badge outcome-badge--exacto">
              <i class="bi bi-star-fill"></i> Exacto
            </span>
            {% elif punt.codigo_acierto == 'winner' or punt.puntos > 0 %}
            <span class="outcome-badge outcome-badge--acierto">
              <i class="bi bi-check-circle-fill"></i> Acierto
            </span>
            {% else %}
            <span class="outcome-badge outcome-badge--fallo">
              <i class="bi bi-x-circle-fill"></i> Fallo
            </span>
            {% endif %}
          {% elif prono %}
          <span class="outcome-badge outcome-badge--sin-pts">Sin pts</span>
          {% else %}
          <span class="outcome-badge outcome-badge--no-played">No jugaste</span>
          {% endif %}
        </div>
      </div>

    {% else %}
      <!-- CERRADO -->
      <div class="ev-row ev-row--cerrado">
        <div class="ev-row__left">
          <span class="ev-row__name">{{ ev.tipo_evento.nombre }}</span>
          {% if prono %}<span class="ev-row__my-pick">{{ prono }}</span>{% endif %}
        </div>
        <span class="ev-row__closed-badge">Cerrado</span>
      </div>
    {% endif %}

    {% endwith %}
    {% endfor %}
  </div>
  {% endif %}

</div>
{% endwith %}
{% empty %}
<div class="empty-state">
  <i class="bi bi-calendar3 empty-state__icon"></i>
  <p class="empty-state__subtitle">No hay partidos en esta fecha.</p>
</div>
{% endfor %}

{% endblock %}
```

---

## 3. PANTALLA 3 — Pronosticar Evento

### 3.1 Wireframe ASCII — Tipo WINNER

```
╔══════════════════════════════════════════╗
║ ← Ganador del partido       Toque        ║
╠══════════════════════════════════════════╣
║                                          ║
║  ╔════════════════════════════════════╗  ║
║  ║                                    ║  ║
║  ║  [🇦🇷 56px]              [🇫🇷 56px] ║  ║  ← equipo crests grandes
║  ║  Argentina       VS       Francia  ║  ║
║  ║                                    ║  ║
║  ║  ⏰ Cierra el 5/6 a las 20:45      ║  ║  ← deadline
║  ╚════════════════════════════════════╝  ║
║                                          ║
║  ¿Quién gana el partido?                 ║  ← descripción evento
║                                          ║
║  ╔════════════════════════════════════╗  ║
║  ║  [🇦🇷]  Argentina gana            ║  ║  ← choice card (sin seleccionar)
║  ╚════════════════════════════════════╝  ║
║  ╔════════════════════════════════════╗  ║
║  ║  ⚖  Empate                        ║  ║
║  ╚════════════════════════════════════╝  ║
║  ╔════════════════════════════════════╗  ║
║  ║  [🇫🇷]  Francia gana              ║  ║
║  ╚════════════════════════════════════╝  ║
║                                          ║
║  ╔════════════════════════════════════╗  ║  ← choice SELECCIONADO
║  ║  ✓ [🇦🇷]  Argentina gana          ║  ║    (fondo verde glow)
║  ╚════════════════════════════════════╝  ║
║                                          ║
║  [        ✓ Guardar jugada         ]    ║  ← btn full width
╚══════════════════════════════════════════╝
```

### 3.2 Wireframe ASCII — Tipo SCORE

```
╔══════════════════════════════════════════╗
║ ← Marcador exacto           Toque        ║
╠══════════════════════════════════════════╣
║                                          ║
║  [🇦🇷 56px]              [🇫🇷 56px]      ║
║  Argentina       VS       Francia        ║
║  ⏰ Cierra el 5/6 a las 20:45            ║
║                                          ║
║  ¿Cuál será el marcador exacto?          ║
║                                          ║
║  ┌──────────────────────────────────┐    ║
║  │ [🇦🇷]  [ 2 ]  ─  [ 1 ]  [🇫🇷]  │    ║  ← inputs con crests
║  └──────────────────────────────────┘    ║
║                                          ║
║  [        ✓ Guardar jugada         ]    ║
╚══════════════════════════════════════════╝
```

### 3.3 Wireframe ASCII — Tipo BTTS / OU25

```
║  ¿Ambos equipos anotan?                  ║
║                                          ║
║  ╔════════════════════════════════════╗  ║
║  ║  ⚽⚽  Sí, ambos anotan           ║  ║
║  ╚════════════════════════════════════╝  ║
║  ╔════════════════════════════════════╗  ║
║  ║  🚫   No, alguno se queda en 0    ║  ║
║  ╚════════════════════════════════════╝  ║

║  ¿Cuántos goles en total?                ║
║                                          ║
║  ╔════════════════════════════════════╗  ║
║  ║  📈  Más de 2.5 goles              ║  ║
║  ╚════════════════════════════════════╝  ║
║  ╔════════════════════════════════════╗  ║
║  ║  📉  Menos de 2.5 goles           ║  ║
║  ╚════════════════════════════════════╝  ║
```

### 3.4 Cambios en la vista — `predictions/views.py`

La vista `pronosticar_evento_view` **no requiere cambios de contexto** — ya tiene todo lo necesario (`evento.partido.home_team.logo_url`, etc.). Solo es cambio de template.

### 3.5 Nuevo template — `predictions/pronosticar_evento.html`

```html
{% extends "base.html" %}
{% block title %}{{ evento.tipo_evento.nombre }} — Toque{% endblock %}
{% block page_title %}{{ evento.tipo_evento.nombre }}{% endblock %}
{% block nav_predict %}active{% endblock %}

{% block header_back %}
<a href="javascript:history.back()" class="btn-icon"><i class="bi bi-chevron-left"></i></a>
{% endblock %}

{% block content %}

<!-- Match Hero con escudos grandes -->
<div class="predict-match-hero">
  <div class="predict-team">
    {% if evento.partido.home_team.logo_url %}
    <img src="{{ evento.partido.home_team.logo_url }}" alt="{{ evento.partido.home_team.name }}"
         class="team-crest team-crest--lg">
    {% else %}
    <div class="team-crest team-crest--lg team-crest--fallback">{{ evento.partido.home_team.name|slice:":3"|upper }}</div>
    {% endif %}
    <span class="predict-team__name">{{ evento.partido.home_team.name }}</span>
  </div>

  <div class="predict-match-hero__center">
    <span class="predict-vs">VS</span>
    <span class="predict-match-hero__time">
      <i class="bi bi-clock"></i> {{ evento.partido.match_date|date:"d M · H:i" }}
    </span>
    <span class="predict-match-hero__deadline">
      <i class="bi bi-lock"></i> Cierra {{ evento.plazo_cierre|date:"d M · H:i" }}
    </span>
  </div>

  <div class="predict-team predict-team--away">
    {% if evento.partido.away_team.logo_url %}
    <img src="{{ evento.partido.away_team.logo_url }}" alt="{{ evento.partido.away_team.name }}"
         class="team-crest team-crest--lg">
    {% else %}
    <div class="team-crest team-crest--lg team-crest--fallback">{{ evento.partido.away_team.name|slice:":3"|upper }}</div>
    {% endif %}
    <span class="predict-team__name">{{ evento.partido.away_team.name }}</span>
  </div>
</div>

<!-- Pregunta -->
<p class="predict-question">{{ evento.tipo_evento.descripcion }}</p>

<!-- Formulario -->
<form method="post" id="predictForm">
  {% csrf_token %}

  {% if evento.tipo_evento.codigo == 'SCORE' %}
  <!-- SCORE: inputs con escudos -->
  <div class="predict-score-row">
    {% if evento.partido.home_team.logo_url %}
    <img src="{{ evento.partido.home_team.logo_url }}" class="team-crest team-crest--sm">
    {% else %}
    <div class="team-crest team-crest--sm team-crest--fallback">{{ evento.partido.home_team.name|slice:":3"|upper }}</div>
    {% endif %}

    <input type="number" name="home" id="home" min="0" max="20" inputmode="numeric"
           class="predict-score-input" value="{{ score_home|default:'' }}" required>
    <span class="predict-score-sep">—</span>
    <input type="number" name="away" id="away" min="0" max="20" inputmode="numeric"
           class="predict-score-input" value="{{ score_away|default:'' }}" required>

    {% if evento.partido.away_team.logo_url %}
    <img src="{{ evento.partido.away_team.logo_url }}" class="team-crest team-crest--sm">
    {% else %}
    <div class="team-crest team-crest--sm team-crest--fallback">{{ evento.partido.away_team.name|slice:":3"|upper }}</div>
    {% endif %}
  </div>

  {% else %}
  <!-- Choices: WINNER / BTTS / OU25 -->
  <div class="predict-choices">
    {% for choice in evento.tipo_evento.config.choices %}
    <label class="predict-choice {% if pronostico_existente.valor == choice %}predict-choice--selected{% endif %}"
           data-value="{{ choice }}">
      <input type="radio" name="valor" value="{{ choice }}"
             {% if pronostico_existente.valor == choice %}checked{% endif %}
             required style="display:none;">

      <span class="predict-choice__icon">
        {% if evento.tipo_evento.codigo == 'WINNER' %}
          {% if choice == 'H' %}
            {% if evento.partido.home_team.logo_url %}
            <img src="{{ evento.partido.home_team.logo_url }}" class="team-crest team-crest--sm">
            {% else %}
            <div class="team-crest team-crest--sm team-crest--fallback">{{ evento.partido.home_team.name|slice:":3"|upper }}</div>
            {% endif %}
          {% elif choice == 'D' %}
            <i class="bi bi-dash-circle" style="font-size:28px;color:var(--text-secondary);"></i>
          {% elif choice == 'A' %}
            {% if evento.partido.away_team.logo_url %}
            <img src="{{ evento.partido.away_team.logo_url }}" class="team-crest team-crest--sm">
            {% else %}
            <div class="team-crest team-crest--sm team-crest--fallback">{{ evento.partido.away_team.name|slice:":3"|upper }}</div>
            {% endif %}
          {% endif %}
        {% elif evento.tipo_evento.codigo == 'BTTS' %}
          {% if choice == 'yes' %}<i class="bi bi-check2-circle" style="font-size:24px;color:var(--green);"></i>
          {% else %}<i class="bi bi-x-circle" style="font-size:24px;color:var(--danger);"></i>{% endif %}
        {% elif evento.tipo_evento.codigo == 'OU25' %}
          {% if choice == 'over' %}<i class="bi bi-graph-up-arrow" style="font-size:24px;color:var(--green);"></i>
          {% else %}<i class="bi bi-graph-down-arrow" style="font-size:24px;color:var(--danger);"></i>{% endif %}
        {% endif %}
      </span>

      <span class="predict-choice__label">
        {% if evento.tipo_evento.codigo == 'WINNER' %}
          {% if choice == 'H' %}{{ evento.partido.home_team.name }} gana
          {% elif choice == 'D' %}Empate
          {% elif choice == 'A' %}{{ evento.partido.away_team.name }} gana
          {% else %}{{ choice }}{% endif %}
        {% elif evento.tipo_evento.codigo == 'BTTS' %}
          {% if choice == 'yes' %}Sí, ambos anotan{% else %}No, alguno se queda en 0{% endif %}
        {% elif evento.tipo_evento.codigo == 'OU25' %}
          {% if choice == 'over' %}Más de 2.5 goles{% else %}Menos de 2.5 goles{% endif %}
        {% else %}{{ choice }}{% endif %}
      </span>

      <span class="predict-choice__check"><i class="bi bi-check-circle-fill"></i></span>
    </label>
    {% endfor %}
  </div>
  {% endif %}

  <button type="submit" class="btn btn-primary predict-submit">
    <i class="bi bi-check-circle-fill"></i>
    {% if pronostico_existente %}Actualizar jugada{% else %}Guardar jugada{% endif %}
  </button>
</form>

{% endblock %}

{% block extra_js %}
<script>
document.querySelectorAll('.predict-choice').forEach(function(card) {
  card.addEventListener('click', function() {
    document.querySelectorAll('.predict-choice').forEach(function(c) {
      c.classList.remove('predict-choice--selected');
    });
    this.classList.add('predict-choice--selected');
    this.querySelector('input[type=radio]').checked = true;
  });
});
</script>
{% endblock %}
```

---

## 4. CSS — Nuevos componentes a agregar en `main.css`

```css
/* ── Team Crest ──────────────────────────────────────────── */
.team-crest {
  border-radius: var(--r-full);
  object-fit: contain;
  flex-shrink: 0;
  background: var(--bg-elevated);
}
.team-crest--sm  { width: 32px; height: 32px; }
.team-crest--md  { width: 40px; height: 40px; }
.team-crest--lg  { width: 56px; height: 56px; }

.team-crest--fallback {
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-display);
  font-weight: var(--fw-black);
  font-size: var(--text-xs);
  letter-spacing: 0.03em;
  background: linear-gradient(135deg, var(--bg-elevated), var(--bg-hover));
  color: var(--text-secondary);
  border: 1px solid var(--border);
}

/* ── Player Hero ─────────────────────────────────────────── */
.player-hero {
  padding: var(--s4) var(--s4) var(--s5);
  background: linear-gradient(135deg, var(--bg-elevated) 0%, var(--bg-surface) 100%);
  border-radius: var(--r-xl);
  margin-bottom: var(--s5);
  border: 1px solid var(--border);
  position: relative;
  overflow: hidden;
}
.player-hero::after {
  content: '';
  position: absolute;
  top: -20px; right: -20px;
  width: 120px; height: 120px;
  background: radial-gradient(circle, var(--green-glow) 0%, transparent 70%);
  pointer-events: none;
}
.player-hero__hola {
  display: block;
  font-family: var(--font-display);
  font-size: var(--text-2xl);
  font-weight: var(--fw-black);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-primary);
}
.player-hero__date {
  display: block;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-top: 2px;
  text-transform: capitalize;
}
.player-hero__stats {
  display: flex;
  gap: var(--s3);
  margin-top: var(--s4);
}

/* ── Stat Pill ───────────────────────────────────────────── */
.stat-pill {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: var(--bg-base);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: var(--s2) var(--s4);
  min-width: 72px;
}
.stat-pill__val {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: var(--fw-black);
  color: var(--green);
  line-height: 1;
}
.stat-pill__label {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-top: 2px;
}

/* ── Section Label ───────────────────────────────────────── */
.section-label {
  font-family: var(--font-display);
  font-size: var(--text-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: var(--s3);
  padding-left: 2px;
}

/* ── Reto Card ───────────────────────────────────────────── */
.reto-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: var(--s4);
  margin-bottom: var(--s3);
  transition: border-color 0.2s;
}
.reto-card--pending {
  border-color: rgba(255,165,2,0.35);
  box-shadow: 0 0 0 1px rgba(255,165,2,0.1), inset 0 0 20px rgba(255,165,2,0.04);
}
.reto-card__header {
  display: flex;
  align-items: center;
  gap: var(--s3);
  margin-bottom: var(--s3);
}
.reto-card__icon {
  width: 36px; height: 36px;
  border-radius: var(--r-md);
  background: var(--gold-dim);
  display: flex; align-items: center; justify-content: center;
  color: var(--gold);
  font-size: 16px;
  flex-shrink: 0;
}
.reto-card__info { flex: 1; min-width: 0; }
.reto-card__name {
  display: block;
  font-weight: var(--fw-semibold);
  font-size: var(--text-base);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.reto-card__tournament {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}
.reto-card__badge {
  flex-shrink: 0;
  font-size: var(--text-xs);
  font-weight: var(--fw-semibold);
  padding: 3px 8px;
  border-radius: var(--r-full);
}
.reto-card__badge--alert {
  background: rgba(255,165,2,0.15);
  color: var(--warning);
  border: 1px solid rgba(255,165,2,0.3);
}
.reto-card__stats {
  display: flex;
  align-items: center;
  gap: var(--s2);
  padding: var(--s3) 0;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  margin-bottom: var(--s3);
}
.reto-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.reto-stat__val {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: var(--fw-black);
  color: var(--text-primary);
  line-height: 1;
}
.reto-stat__label {
  font-size: var(--text-xs);
  color: var(--text-muted);
}
.reto-stat__sep { color: var(--border); font-size: var(--text-lg); }
.reto-card__no-ranking {
  font-size: var(--text-xs);
  color: var(--text-muted);
  padding: var(--s2) 0;
  border-top: 1px solid var(--border);
  margin-bottom: var(--s3);
}
.reto-card__context {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin-bottom: var(--s3);
}
.reto-card__actions {
  display: flex;
  gap: var(--s2);
}

/* ── Empty Retos ─────────────────────────────────────────── */
.empty-retos {
  text-align: center;
  padding: var(--s8) var(--s4);
  background: var(--bg-surface);
  border: 1px dashed var(--border);
  border-radius: var(--r-xl);
  margin-bottom: var(--s4);
}
.empty-retos__icon {
  font-size: 40px;
  color: var(--text-muted);
  display: block;
  margin-bottom: var(--s3);
}
.empty-retos__title {
  font-weight: var(--fw-semibold);
  margin-bottom: var(--s2);
}
.empty-retos__sub {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.5;
}

/* ── Matchday Strip ──────────────────────────────────────── */
.matchday-strip { display: flex; flex-direction: column; gap: var(--s2); }
.matchday-item {
  display: flex;
  align-items: center;
  gap: var(--s3);
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: var(--s3) var(--s4);
}
.matchday-item__team {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--s2);
}
.matchday-item__team--away { flex-direction: row-reverse; }
.matchday-item__name {
  font-size: var(--text-sm);
  font-weight: var(--fw-medium);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.matchday-item__center {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
  min-width: 64px;
}
.matchday-item__vs {
  font-family: var(--font-display);
  font-size: var(--text-sm);
  font-weight: var(--fw-black);
  color: var(--text-muted);
}
.matchday-item__time {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

/* ── Partido Card ────────────────────────────────────────── */
.partido-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  overflow: hidden;
  margin-bottom: var(--s4);
}
.partido-card__header {
  display: flex;
  align-items: center;
  gap: var(--s2);
  padding: var(--s4);
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border);
}
.partido-team {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--s2);
  text-align: center;
}
.partido-team--away { flex-direction: column; }
.partido-team__name {
  font-size: var(--text-xs);
  font-weight: var(--fw-semibold);
  color: var(--text-secondary);
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.partido-card__center {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 72px;
}
.partido-score {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: var(--fw-black);
  line-height: 1;
}
.partido-score__sep { margin: 0 4px; color: var(--text-muted); }
.partido-score--live { color: var(--danger); animation: pulse 1.2s infinite; }
.partido-card__time {
  font-size: var(--text-sm);
  font-weight: var(--fw-semibold);
  color: var(--text-primary);
}
.partido-card__hour {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}
.partido-card__status--done {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-top: 2px;
}

/* ── Evento Row ──────────────────────────────────────────── */
.partido-card__events { padding: 0 var(--s4); }

.ev-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s3);
  padding: var(--s3) 0;
  border-top: 1px solid var(--border-subtle);
  position: relative;
}
.ev-row::before {
  content: '';
  position: absolute;
  left: calc(-1 * var(--s4));
  top: 0; bottom: 0;
  width: 3px;
  border-radius: 0 2px 2px 0;
}
.ev-row__left { flex: 1; min-width: 0; }
.ev-row__name {
  display: block;
  font-size: var(--text-sm);
  font-weight: var(--fw-medium);
}
.ev-row__deadline, .ev-row__result-detail {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin-top: 2px;
}
.ev-row__my-pick {
  display: inline-flex;
  align-items: center;
  font-size: var(--text-xs);
  color: var(--warning);
  font-weight: var(--fw-medium);
  margin-top: 2px;
}
.ev-row__right { flex-shrink: 0; }
.ev-row__btn { flex-shrink: 0; }
.ev-row__closed-badge {
  font-size: var(--text-xs);
  color: var(--text-muted);
  background: var(--bg-elevated);
  padding: 2px 8px;
  border-radius: var(--r-full);
}

/* Estado: ABIERTO sin pronóstico */
.ev-row--abierto::before { background: var(--green); }
@keyframes borderPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.ev-row--abierto::before { animation: borderPulse 2s ease-in-out infinite; }

/* Estado: ABIERTO con pronóstico */
.ev-row--editando::before { background: var(--warning); }

/* Estado: CERRADO */
.ev-row--cerrado {
  opacity: 0.55;
  pointer-events: none;
}
.ev-row--cerrado::before { background: var(--text-muted); }

/* Estado: PUNTUADO */
.ev-row--puntuado::before { background: var(--gold); }

/* ── Outcome Badge ───────────────────────────────────────── */
.outcome-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
  font-weight: var(--fw-bold);
  padding: 3px 8px;
  border-radius: var(--r-full);
  white-space: nowrap;
  font-family: var(--font-display);
  letter-spacing: 0.05em;
}
.outcome-badge--exacto {
  background: var(--gold-dim);
  color: var(--gold);
  border: 1px solid rgba(255,201,71,0.4);
}
.outcome-badge--acierto {
  background: var(--green-glow);
  color: var(--green);
  border: 1px solid rgba(0,230,118,0.3);
}
.outcome-badge--fallo {
  background: rgba(255,71,87,0.1);
  color: var(--danger);
  border: 1px solid rgba(255,71,87,0.25);
}
.outcome-badge--sin-pts {
  background: var(--bg-elevated);
  color: var(--text-muted);
}
.outcome-badge--no-played {
  background: var(--bg-elevated);
  color: var(--text-muted);
  font-style: italic;
}

/* ── Predict: Match Hero ─────────────────────────────────── */
.predict-match-hero {
  display: flex;
  align-items: center;
  gap: var(--s3);
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--r-xl);
  padding: var(--s5) var(--s4);
  margin-bottom: var(--s4);
  position: relative;
  overflow: hidden;
}
.predict-match-hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at center, var(--green-glow) 0%, transparent 65%);
  pointer-events: none;
}
.predict-team {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--s2);
  text-align: center;
}
.predict-team--away { flex-direction: column; }
.predict-team__name {
  font-size: var(--text-xs);
  font-weight: var(--fw-semibold);
  color: var(--text-secondary);
  max-width: 80px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.predict-match-hero__center {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  min-width: 72px;
}
.predict-vs {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: var(--fw-black);
  color: var(--text-primary);
  letter-spacing: 0.08em;
}
.predict-match-hero__time,
.predict-match-hero__deadline {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  text-align: center;
}

/* ── Predict: Question ───────────────────────────────────── */
.predict-question {
  font-size: var(--text-md);
  font-weight: var(--fw-semibold);
  color: var(--text-primary);
  margin-bottom: var(--s4);
  text-align: center;
}

/* ── Predict: Choices ────────────────────────────────────── */
.predict-choices {
  display: flex;
  flex-direction: column;
  gap: var(--s2);
  margin-bottom: var(--s4);
}
.predict-choice {
  display: flex;
  align-items: center;
  gap: var(--s3);
  padding: var(--s4);
  min-height: 72px;
  background: var(--bg-surface);
  border: 1.5px solid var(--border);
  border-radius: var(--r-lg);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
  position: relative;
}
.predict-choice:hover {
  border-color: rgba(0,230,118,0.3);
  background: var(--bg-elevated);
}
.predict-choice__icon {
  flex-shrink: 0;
  width: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.predict-choice__label {
  flex: 1;
  font-size: var(--text-base);
  font-weight: var(--fw-medium);
  color: var(--text-primary);
}
.predict-choice__check {
  flex-shrink: 0;
  color: transparent;
  font-size: 20px;
  transition: color 0.15s;
}

/* Estado SELECCIONADO */
.predict-choice--selected {
  border-color: var(--green);
  background: var(--green-glow);
  box-shadow: var(--glow-green);
}
.predict-choice--selected .predict-choice__label {
  color: var(--green);
  font-weight: var(--fw-bold);
}
.predict-choice--selected .predict-choice__check {
  color: var(--green);
}

/* ── Predict: Score Row ──────────────────────────────────── */
.predict-score-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--s3);
  background: var(--bg-surface);
  border: 1.5px solid var(--border);
  border-radius: var(--r-lg);
  padding: var(--s5) var(--s4);
  margin-bottom: var(--s4);
}
.predict-score-input {
  width: 72px;
  height: 72px;
  text-align: center;
  font-family: var(--font-display);
  font-size: var(--text-3xl);
  font-weight: var(--fw-black);
  color: var(--text-primary);
  background: var(--bg-elevated);
  border: 1.5px solid var(--border);
  border-radius: var(--r-md);
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
  -moz-appearance: textfield;
}
.predict-score-input:focus {
  border-color: var(--green);
  box-shadow: 0 0 0 3px var(--green-glow);
}
.predict-score-input::-webkit-outer-spin-button,
.predict-score-input::-webkit-inner-spin-button { -webkit-appearance: none; }
.predict-score-sep {
  font-family: var(--font-display);
  font-size: var(--text-2xl);
  font-weight: var(--fw-black);
  color: var(--text-muted);
}

/* ── Predict: Submit ─────────────────────────────────────── */
.predict-submit {
  width: 100%;
  height: 56px;
  font-size: var(--text-md);
  justify-content: center;
  font-family: var(--font-display);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
```

---

## 5. Plan de implementación — Fases

### Fase 1 — Escudos + Estados de color en fecha_detail (2-3h)

> **Impacto visual máximo con menor riesgo.** Solo cambian templates y CSS. Sin cambios en views.

1. Agregar todos los CSS nuevos a `main.css`
2. Reescribir `predictions/fecha_detail.html` con:
   - `partido-card`, `partido-team`, `team-crest`
   - `ev-row--abierto`, `ev-row--editando`, `ev-row--cerrado`, `ev-row--puntuado`
   - Sin `mi_puntuacion` aún (ignorar el feedback de exacto/acierto/fallo)
3. Reescribir `predictions/pronosticar_evento.html` con:
   - `predict-match-hero` con escudos
   - `predict-choices` con crest para WINNER
   - `predict-score-row` con crest en SCORE
   - JS para selection state

**Criterio de éxito:** Los partidos muestran escudos (o fallback de 3 letras). Los eventos abiertos tienen borde verde pulsante. El formulario de pronosticar muestra el equipo con su escudo o badge.

---

### Fase 2 — Dashboard personalizado (3-4h)

> **Cambio en view + nuevo template.** Requiere modificar `quinielas_list`.

1. Modificar `quiniela_list` view para pasar `mis_quinielas` y `proximos_partidos`
2. Reescribir la sección autenticada de `quinielas/list.html` con:
   - `player-hero`
   - `reto-card` con stats del ranking
   - `matchday-strip` de próximos partidos
3. Manejar el caso de 0 quinielas inscritas

**Criterio de éxito:** Al loguearse, el jugador ve sus puntos, posición y un botón de "Jugar ahora" en cada reto con eventos abiertos.

---

### Fase 3 — Feedback de puntuación (1-2h)

> Agrega `mi_puntuacion` al contexto de `fecha_detail_view` para mostrar exacto/acierto/fallo.

1. Modificar `fecha_detail_view` para incluir `PuntuacionEvento` en el contexto
2. Habilitar las `outcome-badge` en el template

**Criterio de éxito:** En eventos puntuados, el jugador ve si fue "Exacto", "Acierto" o "Fallo" con los badges de colores.

---

## 6. Notas de implementación

### Banderas / Escudos
- El modelo `Team.logo_url` ya existe y puede contener URLs de logos (ej: API-Football sirve URLs tipo `https://media.api-sports.io/football/teams/XXX.png`).
- El fallback de 3 letras aplica automáticamente cuando `logo_url` está vacío.
- **No se requiere ninguna librería externa** de banderas. Si en el futuro se quiere mejorar la experiencia para selecciones nacionales, se puede agregar el campo `country_code` al modelo `Team` y usar emojis de bandera o SVG de `flagcdn.com`.

### Compatibilidad
- Todos los cambios son backward-compatible: si `logo_url` está vacío, se muestra el badge de texto. Si `mis_quinielas` está vacío, el dashboard hace fallback a la lista pública.
- No se agregan dependencias nuevas (sin HTMX, sin Alpine, sin librerías JS externas).

### Performance
- La query de `proximos_partidos` usa `.distinct()` para evitar duplicados por múltiples quinielas sobre el mismo torneo.
- Las queries de rankings son O(quinielas del usuario) — típicamente 1-5, sin problema.

### Branch y PR
```
feat/ux-jugador-dashboard
├── Fase 1: feat: escudos de equipos y estados visuales en pronósticos
├── Fase 2: feat: dashboard personalizado del jugador
└── Fase 3: feat: feedback de puntuación en partidos (exacto/acierto/fallo)
```
