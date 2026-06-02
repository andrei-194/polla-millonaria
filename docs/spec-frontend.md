# Spec Frontend — Polla Futbolera

**Versión:** 1.0  
**Fecha:** 2026-06-02  
**Stack:** Django Templates + Bootstrap 5 (custom theme) + CSS custom  
**Paradigma:** Mobile-first · App shell pattern · Sin frameworks JS pesados

---

## 1. Principios de Diseño

| Principio | Descripción |
|---|---|
| **Mobile-first** | Diseñado para pantalla de celular, usable en desktop |
| **App shell** | La UI se siente como una app nativa, no un sitio web |
| **Minimalismo funcional** | Cada elemento tiene un propósito. Sin decoración vacía |
| **Legibilidad** | Tipografía clara, jerarquía visual obvia, sin texto pequeño innecesario |
| **Tap targets grandes** | Mínimo 48px de altura en botones e ítems interactivos |
| **Feedback inmediato** | Toda acción del usuario tiene respuesta visual |

---

## 2. Sistema de Diseño

### 2.1 Paleta de colores

Temática fútbol: campo verde, noche de estadio, trofeo dorado.

```css
:root {
  /* Primarios */
  --color-primary:       #0d3b2e;   /* Verde oscuro estadio */
  --color-primary-light: #1a6b4a;   /* Verde campo activo */
  --color-accent:        #4ade80;   /* Verde lima para CTAs y estados activos */

  /* Neutros */
  --color-bg:            #f0f4f0;   /* Fondo general (verde muy claro) */
  --color-surface:       #ffffff;   /* Superficie de tarjetas */
  --color-border:        #e2e8e2;   /* Bordes sutiles */

  /* Texto */
  --color-text-primary:  #0d1f17;   /* Casi negro verdoso */
  --color-text-secondary:#5a6b60;   /* Gris verdoso para subtextos */
  --color-text-inverse:  #ffffff;   /* Texto sobre fondos oscuros */

  /* Semánticos */
  --color-success:       #16a34a;   /* Verde confirmación */
  --color-warning:       #d97706;   /* Ámbar para deadlines próximos */
  --color-danger:        #dc2626;   /* Rojo errores y plazo cerrado */
  --color-gold:          #f59e0b;   /* Oro para podio y trofeos */

  /* Overlay */
  --color-overlay:       rgba(13, 59, 46, 0.7);
}
```

### 2.2 Tipografía

```css
:root {
  --font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;

  /* Escala tipográfica */
  --text-xs:   0.75rem;   /* 12px — etiquetas, badges */
  --text-sm:   0.875rem;  /* 14px — texto secundario */
  --text-base: 1rem;      /* 16px — cuerpo */
  --text-lg:   1.125rem;  /* 18px — subtítulos */
  --text-xl:   1.25rem;   /* 20px — títulos de sección */
  --text-2xl:  1.5rem;    /* 24px — títulos de página */
  --text-3xl:  2rem;      /* 32px — marcadores de partido */

  --font-normal:   400;
  --font-medium:   500;
  --font-semibold: 600;
  --font-bold:     700;
}
```

Cargar Inter desde Google Fonts en el `<head>` del `base.html`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

### 2.3 Espaciado y radios

```css
:root {
  /* Espaciado (múltiplos de 4px) */
  --space-1:  0.25rem;   /* 4px */
  --space-2:  0.5rem;    /* 8px */
  --space-3:  0.75rem;   /* 12px */
  --space-4:  1rem;      /* 16px */
  --space-5:  1.25rem;   /* 20px */
  --space-6:  1.5rem;    /* 24px */
  --space-8:  2rem;      /* 32px */

  /* Border radius */
  --radius-sm:   8px;    /* inputs, badges */
  --radius-md:   12px;   /* botones, componentes pequeños */
  --radius-lg:   16px;   /* tarjetas */
  --radius-xl:   24px;   /* bottom sheet, modals */
  --radius-full: 9999px; /* pills, avatares */

  /* Sombras */
  --shadow-sm:  0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04);
  --shadow-md:  0 4px 12px rgba(0,0,0,0.10), 0 2px 4px rgba(0,0,0,0.06);
  --shadow-lg:  0 8px 24px rgba(0,0,0,0.12);
}
```

---

## 3. Layout General — App Shell

### 3.1 Contenedor centrado (efecto "app en el móvil")

La app se centra en una columna de máximo 480px en pantallas grandes, simulando un teléfono. En móvil ocupa el 100%.

```css
/* base.html */
body {
  background-color: #1a2e22;   /* fondo oscuro alrededor del "teléfono" */
}

.app-shell {
  max-width: 480px;
  min-height: 100dvh;
  margin: 0 auto;
  background-color: var(--color-bg);
  position: relative;
  overflow-x: hidden;
}
```

En desktop esto crea el efecto de ver la app dentro de un dispositivo móvil.

### 3.2 Estructura del HTML base

```html
<body>
  <div class="app-shell">

    <!-- Header de página (dinámico por pantalla) -->
    <header class="app-header">
      <button class="btn-icon btn-back" id="backBtn">   <!-- solo en sub-páginas -->
        <i class="bi bi-chevron-left"></i>
      </button>
      <h1 class="app-header__title">{% block page_title %}{% endblock %}</h1>
      <button class="btn-icon" id="headerAction">      <!-- acción contextual -->
        {% block header_action %}{% endblock %}
      </button>
    </header>

    <!-- Mensajes flash -->
    {% if messages %}
    <div class="toast-container">
      {% for message in messages %}
      <div class="app-toast app-toast--{{ message.tags }}">
        {{ message }}
      </div>
      {% endfor %}
    </div>
    {% endif %}

    <!-- Contenido principal -->
    <main class="app-content">
      {% block content %}{% endblock %}
    </main>

    <!-- Navegación inferior (solo para usuarios autenticados) -->
    {% if user.is_authenticated %}
    <nav class="bottom-nav">
      <a href="{% url 'groups:list' %}" class="bottom-nav__item {% block nav_groups %}{% endblock %}">
        <i class="bi bi-shield-fill"></i>
        <span>Grupos</span>
      </a>
      <a href="{% url 'tournaments:list' %}" class="bottom-nav__item {% block nav_tournaments %}{% endblock %}">
        <i class="bi bi-trophy-fill"></i>
        <span>Torneos</span>
      </a>
      <a href="#" class="bottom-nav__item bottom-nav__item--center {% block nav_predict %}{% endblock %}">
        <div class="bottom-nav__fab">
          <i class="bi bi-pencil-fill"></i>
        </div>
        <span>Pronosticar</span>
      </a>
      <a href="{% url 'scoring:leaderboard' %}" class="bottom-nav__item {% block nav_ranking %}{% endblock %}">
        <i class="bi bi-bar-chart-fill"></i>
        <span>Ranking</span>
      </a>
      <a href="{% url 'notifications:list' %}" class="bottom-nav__item {% block nav_notifications %}{% endblock %}">
        <i class="bi bi-bell-fill"></i>
        <span>Alertas</span>
      </a>
    </nav>
    {% endif %}

  </div>
</body>
```

### 3.3 Header de app

```css
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-4);
  background-color: var(--color-primary);
  color: var(--color-text-inverse);
  min-height: 56px;
}

.app-header__title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  margin: 0;
  flex: 1;
  text-align: center;
}
```

### 3.4 Navegación inferior (Bottom Nav)

```css
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 480px;
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: var(--space-2) 0 env(safe-area-inset-bottom, 8px);
  z-index: 200;
  box-shadow: 0 -4px 12px rgba(0,0,0,0.08);
}

.bottom-nav__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: var(--space-2) var(--space-3);
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  min-width: 60px;
  transition: color 0.15s;
}

.bottom-nav__item i {
  font-size: 1.375rem;
}

.bottom-nav__item.active,
.bottom-nav__item:hover {
  color: var(--color-accent);
}

/* Botón central FAB */
.bottom-nav__item--center {
  position: relative;
  top: -12px;
}

.bottom-nav__fab {
  width: 52px;
  height: 52px;
  background: var(--color-primary-light);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.25rem;
  box-shadow: var(--shadow-md);
}

/* Indicador de tab activo */
.bottom-nav__item.active i {
  position: relative;
}
.bottom-nav__item.active::before {
  content: '';
  position: absolute;
  top: 0;
  width: 32px;
  height: 3px;
  background: var(--color-accent);
  border-radius: 0 0 var(--radius-sm) var(--radius-sm);
}
```

En cada template se activa el tab correspondiente:
```django
{# En groups/list.html #}
{% block nav_groups %}active{% endblock %}
```

### 3.5 Espaciado del contenido principal

```css
.app-content {
  padding: var(--space-4);
  padding-bottom: calc(80px + env(safe-area-inset-bottom, 8px));
  /* 80px = altura del bottom nav */
}
```

---

## 4. Componentes

### 4.1 Tarjetas (Cards)

```css
.card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.card--interactive {
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}

.card--interactive:active {
  transform: scale(0.98);
  box-shadow: var(--shadow-sm);
}
```

Uso: grupos, partidos, pronósticos, notificaciones.

### 4.2 Botones

```css
/* Botón primario */
.btn-primary {
  background: var(--color-primary-light);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  padding: 14px var(--space-6);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  min-height: 52px;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  transition: background 0.15s, transform 0.1s;
  cursor: pointer;
}

.btn-primary:active {
  transform: scale(0.97);
  background: var(--color-primary);
}

/* Botón secundario */
.btn-secondary {
  background: transparent;
  color: var(--color-primary-light);
  border: 2px solid var(--color-primary-light);
  border-radius: var(--radius-md);
  padding: 12px var(--space-6);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  min-height: 52px;
  width: 100%;
}

/* Botón ícono */
.btn-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  border: none;
  background: rgba(255,255,255,0.15);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.125rem;
  cursor: pointer;
}

/* Botón destructivo */
.btn-danger {
  background: var(--color-danger);
  color: white;
}
```

### 4.3 Inputs

```css
.form-field {
  margin-bottom: var(--space-4);
}

.form-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2);
  display: block;
}

.form-input {
  width: 100%;
  padding: 14px var(--space-4);
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  color: var(--color-text-primary);
  background: var(--color-surface);
  transition: border-color 0.15s;
  min-height: 52px;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary-light);
}

.form-input--error {
  border-color: var(--color-danger);
}

.form-error {
  font-size: var(--text-sm);
  color: var(--color-danger);
  margin-top: var(--space-1);
}
```

### 4.4 Marcador de partido (Prediction input)

El componente más importante de la app. Diseño tipo scoreboard de app deportiva.

```html
<div class="match-scorer">
  <div class="match-scorer__team">
    <div class="match-scorer__badge">{{ match.home_team.name|slice:":3"|upper }}</div>
    <span class="match-scorer__name">{{ match.home_team }}</span>
  </div>

  <div class="match-scorer__inputs">
    <input type="number" name="home_goals" min="0" max="20"
           class="match-scorer__input" value="{{ form.home_goals.value|default:'' }}">
    <span class="match-scorer__sep">:</span>
    <input type="number" name="away_goals" min="0" max="20"
           class="match-scorer__input" value="{{ form.away_goals.value|default:'' }}">
  </div>

  <div class="match-scorer__team match-scorer__team--right">
    <div class="match-scorer__badge">{{ match.away_team.name|slice:":3"|upper }}</div>
    <span class="match-scorer__name">{{ match.away_team }}</span>
  </div>
</div>
```

```css
.match-scorer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-6) var(--space-4);
  background: var(--color-primary);
  border-radius: var(--radius-lg);
  color: white;
  margin-bottom: var(--space-6);
}

.match-scorer__team {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}

.match-scorer__badge {
  width: 48px;
  height: 48px;
  background: var(--color-primary-light);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: var(--font-bold);
  font-size: var(--text-sm);
}

.match-scorer__name {
  font-size: var(--text-xs);
  text-align: center;
  opacity: 0.85;
}

.match-scorer__inputs {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.match-scorer__input {
  width: 60px;
  height: 60px;
  background: rgba(255,255,255,0.12);
  border: 2px solid rgba(255,255,255,0.3);
  border-radius: var(--radius-md);
  color: white;
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  text-align: center;
  appearance: textfield;
}

.match-scorer__input:focus {
  outline: none;
  border-color: var(--color-accent);
  background: rgba(255,255,255,0.2);
}

.match-scorer__sep {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  opacity: 0.6;
}
```

### 4.5 Pill / Badge de estado

```css
.badge-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.badge-pill--open    { background: #dcfce7; color: #16a34a; }
.badge-pill--closing { background: #fef3c7; color: #d97706; }
.badge-pill--closed  { background: #fee2e2; color: #dc2626; }
.badge-pill--live    { background: #fce7f3; color: #db2777; }
```

Uso:
- `open` — plazo abierto (más de 2 horas)
- `closing` — plazo próximo a cerrar (menos de 30 min)
- `closed` — plazo cerrado
- `live` — partido en curso

### 4.6 Countdown de deadline

```html
<div class="deadline-badge {% if minutes_remaining < 30 %}deadline-badge--urgent{% endif %}">
  <i class="bi bi-clock"></i>
  {% if minutes_remaining > 60 %}
    Cierra en {{ minutes_remaining|floatformat:0|divide:60 }}h
  {% else %}
    Cierra en {{ minutes_remaining }}min
  {% endif %}
</div>
```

```css
.deadline-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-success);
  padding: 4px 10px;
  background: #dcfce7;
  border-radius: var(--radius-full);
}

.deadline-badge--urgent {
  color: var(--color-warning);
  background: #fef3c7;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.7; }
}
```

### 4.7 Leaderboard row

```html
<div class="leaderboard-row {% if forloop.counter <= 3 %}leaderboard-row--podium{% endif %}">
  <span class="leaderboard-row__rank">
    {% if forloop.counter == 1 %}<i class="bi bi-trophy-fill text-warning"></i>
    {% elif forloop.counter == 2 %}<i class="bi bi-trophy-fill" style="color:#94a3b8"></i>
    {% elif forloop.counter == 3 %}<i class="bi bi-trophy-fill" style="color:#b45309"></i>
    {% else %}#{{ forloop.counter }}{% endif %}
  </span>
  <div class="leaderboard-row__user">
    <span class="leaderboard-row__name">{{ entry.user.username }}</span>
    <span class="leaderboard-row__detail">{{ entry.correct }}/{{ entry.total }} exactos</span>
  </div>
  <span class="leaderboard-row__pts">{{ entry.points }} <small>pts</small></span>
</div>
```

```css
.leaderboard-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-2);
  border: 1px solid var(--color-border);
}

.leaderboard-row--podium {
  border-color: var(--color-gold);
  background: linear-gradient(135deg, #fffbeb, #ffffff);
}

.leaderboard-row__rank {
  width: 32px;
  text-align: center;
  font-weight: var(--font-bold);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.leaderboard-row__user {
  flex: 1;
}

.leaderboard-row__name {
  font-weight: var(--font-semibold);
  font-size: var(--text-base);
  display: block;
}

.leaderboard-row__detail {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

.leaderboard-row__pts {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--color-primary);
}
```

### 4.8 Toasts / Flash messages

Reemplazar los `alert` de Bootstrap por toasts flotantes en la parte superior.

```css
.toast-container {
  position: fixed;
  top: 64px;   /* debajo del header */
  left: 50%;
  transform: translateX(-50%);
  width: calc(100% - 32px);
  max-width: 448px;
  z-index: 300;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.app-toast {
  padding: var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  box-shadow: var(--shadow-md);
  animation: slideDown 0.25s ease;
}

.app-toast--success { background: #16a34a; color: white; }
.app-toast--error   { background: #dc2626; color: white; }
.app-toast--warning { background: #d97706; color: white; }
.app-toast--info    { background: var(--color-primary); color: white; }

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-12px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

Auto-dismiss con JS mínimo:
```html
{% block extra_js %}
<script>
  document.querySelectorAll('.app-toast').forEach(t => {
    setTimeout(() => t.style.opacity = '0', 3000);
    setTimeout(() => t.remove(), 3300);
  });
</script>
{% endblock %}
```

---

## 5. Pantallas — Flujos de Usuario

### 5.1 Pantallas de autenticación (sin bottom nav)

Las pantallas de login y registro tienen layout especial: fondo oscuro con el formulario centrado y la identidad de marca en la parte superior.

```
┌─────────────────────────┐
│                         │
│    🏆  Polla            │
│       Futbolera         │   ← Logo + nombre marca
│                         │
│  ┌───────────────────┐  │
│  │                   │  │
│  │   Iniciar sesión  │  │   ← Tarjeta con formulario
│  │                   │  │
│  │  Usuario          │  │
│  │  ┌─────────────┐  │  │
│  │  └─────────────┘  │  │
│  │                   │  │
│  │  Contraseña       │  │
│  │  ┌─────────────┐  │  │
│  │  └─────────────┘  │  │
│  │                   │  │
│  │  [  Entrar  ]     │  │   ← Botón primario full-width
│  │                   │  │
│  │  ¿No tenés cuenta?│  │
│  │  Registrarse →    │  │
│  └───────────────────┘  │
└─────────────────────────┘
```

```css
.auth-screen {
  min-height: 100dvh;
  background: var(--color-primary);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-6);
}

.auth-brand {
  text-align: center;
  color: white;
  margin-bottom: var(--space-8);
}

.auth-brand__icon {
  font-size: 3rem;
  display: block;
  margin-bottom: var(--space-2);
}

.auth-brand__name {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
}

.auth-card {
  width: 100%;
  max-width: 400px;
  background: white;
  border-radius: var(--radius-xl);
  padding: var(--space-8);
  box-shadow: var(--shadow-lg);
}
```

---

### 5.2 Home — Lista de grupos (`/groups/`)

```
┌─────────────────────────┐
│  ←    Mis Grupos    [+] │   ← Header: botón crear en derecha
├─────────────────────────┤
│                         │
│ ┌─────────────────────┐ │
│ │ 🛡️ Los Cracks       │ │
│ │ 5 miembros · Admin  │ │
│ │ Champions · Copa    │ │   ← Torneos activos del grupo
│ └─────────────────────┘ │
│                         │
│ ┌─────────────────────┐ │
│ │ 🛡️ Familia Pérez    │ │
│ │ 8 miembros · Miembro│ │
│ │ Liga Argentina      │ │
│ └─────────────────────┘ │
│                         │
│ ┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐ │
│   Unirse con código     │   ← Botón secundario
│ └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘ │
│                         │
├─────────────────────────┤
│  Grupos Torneos ✏️ Rank Alertas │   ← Bottom nav
└─────────────────────────┘
```

Cada tarjeta de grupo es tappable y lleva a la pantalla de detalle del grupo.

---

### 5.3 Detalle de grupo (`/groups/<slug>/`)

```
┌─────────────────────────┐
│  ←  Los Cracks     [⚙️] │   ← Config solo para admin
├─────────────────────────┤
│                         │
│  TORNEOS ACTIVOS        │   ← Sección header
│                         │
│ ┌─────────────────────┐ │
│ │ 🏆 Champions 25/26  │ │
│ │ 3 partidos esta semana│ │
│ │            Ver →    │ │
│ └─────────────────────┘ │
│                         │
│  MIEMBROS (5)           │
│                         │
│  👤 Juan  📊 142 pts    │
│  👤 María 📊 138 pts    │
│  👤 Pedro 📊 115 pts    │
│                         │
│  [  Invitar miembro  ]  │
│                         │
└─────────────────────────┘
```

---

### 5.4 Lista de partidos / Torneo (`/groups/<slug>/tournaments/<id>/`)

```
┌─────────────────────────┐
│  ← Champions 25/26      │
├─────────────────────────┤
│                         │
│  MARTES 3 JUN           │   ← Agrupados por fecha
│                         │
│ ┌─────────────────────┐ │
│ │ 🟢 Abierto · 4h 20m │ │   ← Badge de estado + countdown
│ │                     │ │
│ │  MAD    vs    BAR   │ │
│ │  ───    ─    ───    │ │
│ │  Mi pronóstico: 2-1 │ │   ← Si ya pronosticó
│ │              [✏️]   │ │   ← Editar si está abierto
│ └─────────────────────┘ │
│                         │
│ ┌─────────────────────┐ │
│ │ 🔴 Cerrado          │ │
│ │                     │ │
│ │  PSG    vs    MCI   │ │
│ │  Resultado: 1-2     │ │   ← Resultado real
│ │  Mi pred:   1-1  0pt│ │   ← Pronóstico y puntos obtenidos
│ └─────────────────────┘ │
│                         │
└─────────────────────────┘
```

---

### 5.5 Pantalla de pronóstico (`/groups/<slug>/tournaments/<id>/matches/<id>/predict/`)

```
┌─────────────────────────┐
│  ←   Tu pronóstico      │
├─────────────────────────┤
│                         │
│ ┌─────────────────────┐ │
│ │  MAD        BAR     │ │   ← Match scorer (componente 4.4)
│ │  ───        ───     │ │
│ │  [2]   :   [1]      │ │   ← Inputs grandes
│ │                     │ │
│ │ 🟢 Cierra en 4h 20m │ │
│ └─────────────────────┘ │
│                         │
│  Martes 3 Jun · 21:00   │
│  Champions · Semifinal  │
│                         │
│  ┌─────────────────┐    │
│  │ Guardar pronóst.│    │   ← Botón primario
│  └─────────────────┘    │
│                         │
│  ┌─────────────────┐    │
│  │    Cancelar     │    │   ← Botón secundario
│  └─────────────────┘    │
│                         │
└─────────────────────────┘
```

Si el deadline está cerrado, el formulario no aparece — se muestra el pronóstico existente como solo lectura con el resultado y puntos.

---

### 5.6 Ranking (`/groups/<slug>/tournaments/<id>/leaderboard/`)

```
┌─────────────────────────┐
│  ←   Ranking            │
├─────────────────────────┤
│                         │
│  Champions 25/26        │
│  Los Cracks · 8 partidos│
│                         │
│  🥇 Juan      142 pts   │   ← Podio destacado (fondo dorado)
│  🥈 María     138 pts   │
│  🥉 Carlos    115 pts   │
│  ─────────────────────  │
│  #4 Ana        98 pts   │
│  #5 Pedro      87 pts   │
│  #6 (tú)       74 pts   │   ← El usuario actual destacado
│                         │
└─────────────────────────┘
```

---

### 5.7 Perfil (`/accounts/profile/`)

```
┌─────────────────────────┐
│  ←   Mi Perfil          │
├─────────────────────────┤
│                         │
│     [Avatar grande]     │
│      juan_perez         │
│      juan@email.com     │
│                         │
│  ┌──────┐  ┌──────┐     │
│  │ 142  │  │ 47%  │     │   ← Stats destacadas
│  │ pts  │  │ aciert│    │
│  └──────┘  └──────┘     │
│                         │
│  AJUSTES                │
│                         │
│  Cambiar contraseña  →  │
│  Editar bio          →  │
│  Editar avatar       →  │
│                         │
│  ┌─────────────────┐    │
│  │  Cerrar sesión  │    │   ← Botón danger (form POST)
│  └─────────────────┘    │
│                         │
└─────────────────────────┘
```

---

## 6. Pantallas de estados vacíos y errores

### Estado vacío (empty state)

```css
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-8) var(--space-6);
  text-align: center;
  gap: var(--space-4);
}

.empty-state__icon {
  font-size: 3.5rem;
  color: var(--color-border);
}

.empty-state__title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.empty-state__subtitle {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}
```

### Página 404 / 403

Pantalla simple con ícono, mensaje y botón de "Volver al inicio". Sin tecnicismos.

---

## 7. Responsividad

| Breakpoint | Comportamiento |
|---|---|
| `< 480px` (móvil) | Layout nativo full-screen, bottom nav fijo |
| `480px–768px` (tablet) | Contenedor 480px centrado, fondo oscuro visible |
| `> 768px` (desktop) | Igual que tablet — el "teléfono" se ve en el centro de una pantalla oscura |

No hay breakpoints para adaptar el layout interno — la app siempre es una columna de 480px. Esto simplifica el desarrollo y refuerza la sensación de app móvil.

---

## 8. Archivos a crear/modificar

| Archivo | Acción | Descripción |
|---|---|---|
| `static/css/main.css` | Reemplazar | Sistema de diseño completo (variables + componentes) |
| `templates/base.html` | Reemplazar | App shell con header + bottom nav + toast container |
| `templates/accounts/login.html` | Reemplazar | Auth screen sin navbar |
| `templates/accounts/register.html` | Reemplazar | Auth screen sin navbar |
| `templates/accounts/profile.html` | Reemplazar | Pantalla de perfil con stats |
| `templates/groups/list.html` | Reemplazar | Lista de grupos tipo app |
| `templates/groups/detail.html` | Reemplazar | Detalle con torneos y miembros |
| `templates/tournaments/detail.html` | Reemplazar | Lista de partidos con badges y countdown |
| `templates/predictions/predict.html` | Reemplazar | Match scorer interactivo |
| `templates/scoring/leaderboard.html` | Reemplazar | Ranking con podio |
| `templates/notifications/list.html` | Reemplazar | Lista de notificaciones tipo inbox |

---

## 9. Orden de implementación

```
1. variables CSS y reset en main.css
2. base.html — app shell + bottom nav + toasts
3. login.html + register.html (auth screens, sin nav)
4. groups/list.html (pantalla principal post-login)
5. groups/detail.html
6. tournaments/detail.html (con badge de estado y countdown)
7. predictions/predict.html (match scorer)
8. scoring/leaderboard.html
9. accounts/profile.html
10. notifications/list.html
11. empty states y pantallas de error (404, 403)
```

---

*Este spec es la fuente de verdad para el agente de frontend. Cualquier decisión de diseño no cubierta aquí debe seguir los principios: minimalismo funcional, sensación de app nativa, tap targets grandes, jerarquía visual clara.*
