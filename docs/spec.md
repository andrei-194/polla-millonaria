# Spec Técnico — Polla Futbolera

**Versión:** 2.0  
**Fecha:** 2026-06-02  
**Arquitectura:** Hexagonal (Application / Domain / Infrastructure)  
**Entorno destino:** Railway  

---

## 1. Resumen del Proyecto

Sistema web monolítico de quinielas futbolísticas privadas. Los jugadores compiten prediciendo resultados de partidos de torneos reales (obtenidos vía API externa) dentro de quinielas cerradas gestionadas por moderadores. El acceso público permite explorar resultados y rankings para incentivar la inscripción.

**Stack:**
- Backend: Django 5.x (última versión estable)
- Base de datos: PostgreSQL 16
- Frontend: Django Templates (HTMX opcional para interactividad sin JS complejo)
- Contenedores: Docker + Docker Compose
- Despliegue: Railway

---

## 2. Estructura de Carpetas — Arquitectura Hexagonal

```
polla_futbolera/                  ← raíz del proyecto Django
├── manage.py
├── config/                       ← configuración Django (settings, urls, wsgi, asgi)
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py        ← usado en Railway
│   ├── urls.py
│   └── wsgi.py
│
├── apps/                         ← módulos Django (cada uno sigue hexagonal internamente)
│   ├── accounts/                 ← autenticación, perfiles y sistema de roles
│   │   ├── application/
│   │   ├── domain/
│   │   └── infrastructure/
│   │
│   ├── quinielas/                ← quinielas e inscripciones de jugadores
│   │   ├── application/
│   │   ├── domain/
│   │   └── infrastructure/
│   │
│   ├── tournaments/              ← torneos, equipos, partidos y resultados
│   │   ├── application/
│   │   ├── domain/
│   │   └── infrastructure/
│   │
│   ├── predictions/              ← pronósticos de jugadores
│   │   ├── application/
│   │   ├── domain/
│   │   └── infrastructure/
│   │
│   ├── scoring/                  ← sistema de puntuación y rankings
│   │   ├── application/
│   │   ├── domain/
│   │   └── infrastructure/
│   │
│   └── notifications/            ← alertas y recordatorios
│       ├── application/
│       ├── domain/
│       └── infrastructure/
│
├── shared/                       ← código compartido entre apps
│   ├── domain/                   ← base classes, excepciones de dominio
│   └── infrastructure/           ← utilidades comunes, cliente HTTP base
│
├── templates/                    ← Django Templates globales
├── static/                       ← CSS, JS, imágenes
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
│
├── docker/
│   ├── Dockerfile
│   ├── Dockerfile.dev
│   └── entrypoint.sh
│
├── docker-compose.yml            ← para desarrollo local
├── docker-compose.prod.yml       ← referencia para Railway
├── .env.example
└── railway.toml                  ← configuración Railway
```

### Convención interna por capa (dentro de cada app)

```
application/
  services.py      ← orquesta casos de uso, llama a puertos del dominio
  dtos.py          ← objetos de transferencia entre capas

domain/
  entities.py      ← clases de dominio puras (sin Django)
  ports.py         ← interfaces/protocolos (ABC o Protocol) que infrastructure implementa
  exceptions.py    ← excepciones de dominio

infrastructure/
  models.py        ← modelos Django ORM
  repositories.py  ← implementación concreta de los puertos del dominio
  adapters.py      ← adaptadores externos (API de fútbol, email, etc.)
  views.py         ← vistas Django (controladores HTTP)
  urls.py
  forms.py
  admin.py
```

---

## 3. Sistema de Roles

El sistema de permisos se implementa con **Django Groups nativos**. No se crean modelos custom de roles. Hay 4 niveles:

| Nivel | Django Group | Capacidades |
|---|---|---|
| **Público** | *(sin grupo asignado)* | Ver lista de quinielas activas, resultados de partidos, top 10 de cada quiniela. Puede registrarse solo. No puede predecir ni ver detalles privados. |
| **Jugador** | `Jugador` | Predecir en quinielas donde está inscrito (dentro del plazo). Ver su ranking por quiniela. Editar perfil básico (nombre, apellido, avatar, contraseña). |
| **Moderador** | `Moderador` | Inscribir/dar de baja jugadores en quinielas. Activar/desactivar cuentas de jugadores. Monitorear resultados y rankings. Compartir links de acceso. |
| **Superadmin** | *(Django `is_staff` + `is_superuser`)* | Todo: crear quinielas y torneos, asignar roles, acceso al panel `/admin/`. |

### Reglas de asignación de roles

- Un usuario recién registrado queda como **Público** (sin grupo Django asignado).
- Solo el **Moderador** puede promover un usuario Público a Jugador.
- Solo el **Superadmin** puede asignar el rol Moderador.
- Los roles se gestionan desde el panel `/admin/` (superadmin) o desde `/moderador/` (moderador, solo para el rol Jugador).

### Campos editables por rol

| Campo | Público | Jugador | Moderador | Superadmin |
|---|---|---|---|---|
| Nombre / Apellido | ✗ | ✓ | ✓ | ✓ |
| Avatar | ✗ | ✓ | ✓ | ✓ |
| Contraseña | ✓ | ✓ | ✓ | ✓ |
| Email | ✗ | ✗ | ✗ | ✓ |
| Username | ✗ | ✗ | ✗ | ✓ |
| Puntos / Scores | ✗ | ✗ | ✗ | ✓ (automático) |
| Rol | ✗ | ✗ | Solo → Jugador | ✓ |

---

## 4. Módulos del Sistema

### 4.1 `accounts` — Autenticación, Perfiles y Roles

**Funcionalidades:**
- Registro público con username + email + password (Django auth nativo). El usuario queda como Público.
- Login / logout con sesiones.
- Perfil de usuario con avatar, nombre, apellido y estadísticas globales.
- Cambio de contraseña.
- Helpers de permisos reutilizables: `is_jugador(user)`, `is_moderador(user)`.

**Modelos de dominio:**
- `User` (extiende `AbstractUser` de Django)
- `UserProfile` (avatar, bio, stats agregadas — campos de solo lectura para el jugador)

**Endpoints (vistas):**
- `POST /accounts/register/` — registro público
- `POST /accounts/login/`
- `POST /accounts/logout/`
- `GET/POST /accounts/profile/` — editar perfil (campos permitidos según rol)
- `GET/POST /accounts/password/change/`

---

### 4.2 `quinielas` — Quinielas e Inscripciones

**Qué es una Quiniela:**
Una quiniela es una competencia privada de predicciones futbolísticas vinculada a exactamente un torneo real (Champions, Copa América, Liga BetPlay, etc.). Tiene su propio ranking independiente. La crea únicamente el superadmin. Los jugadores participan mediante inscripción gestionada por el moderador.

**Funcionalidades:**
- Listar quinielas activas (vista pública: nombre, torneo, top 10).
- Detalle de quiniela: partidos, ranking completo (solo jugadores inscritos), top 10 (público).
- El moderador inscribe o da de baja jugadores en una quiniela.
- Un jugador puede estar inscrito en múltiples quinielas simultáneamente.

**Modelos de dominio:**
- `Quiniela` (nombre, slug, descripción, torneo_id, estado: `activa`|`finalizada`, creada_en)
- `Inscripcion` (jugador_id, quiniela_id, activa: bool, inscrito_en)
  - Restricción única: `(jugador_id, quiniela_id)`

**Endpoints (vistas):**
- `GET /quinielas/` — lista de quinielas activas (público)
- `GET /quinielas/<slug>/` — detalle de quiniela
- `GET /quinielas/<slug>/leaderboard/` — ranking completo (inscrito) / top 10 (público)
- `GET /moderador/quinielas/<slug>/inscripciones/` — gestión de inscripciones (moderador)
- `POST /moderador/quinielas/<slug>/inscripciones/agregar/` — inscribir jugador (moderador)
- `POST /moderador/quinielas/<slug>/inscripciones/<id>/baja/` — dar de baja (moderador)

---

### 4.3 `tournaments` — Torneos y Partidos

**Funcionalidades:**
- El superadmin crea torneos desde el panel `/admin/` o vía comando de gestión.
- Al crear una Quiniela, el superadmin le asigna un torneo existente.
- Los partidos (fixtures) se sincronizan desde una API externa.
- Los resultados se actualizan automáticamente cuando el partido termina.
- El superadmin puede forzar sincronización manual desde el panel `/admin/`.

**Modelos de dominio:**
- `Tournament` (nombre, código_externo, temporada, estado: `activo`|`finalizado`)
- `Team` (nombre, código_externo, logo_url)
- `Match` (torneo_id, fase, equipo_local_id, equipo_visitante_id, fecha, resultado_local, resultado_visitante, estado: `programado`|`en_curso`|`finalizado`|`postergado`, external_id)

**Puerto de API externa:**
```python
# domain/ports.py
class FootballAPIPort(Protocol):
    def fetch_fixtures(self, tournament_code: str, season: str) -> list[MatchDTO]: ...
    def fetch_results(self, match_external_id: str) -> ResultDTO: ...
```

**Adaptador:** `infrastructure/adapters.py` implementa `FootballAPIPort` para la API elegida (API-Football, football-data.org, etc.). El adaptador es intercambiable sin tocar el dominio.

**Sincronización:** Tarea periódica con `django-q2`. En Railway se configura como worker service separado.

**Endpoints (vistas):**
- `GET /torneos/` — lista de torneos disponibles (público, solo lectura)
- `GET /torneos/<id>/partidos/` — fixtures del torneo (público)

---

### 4.4 `predictions` — Pronósticos

**Funcionalidades:**
- Solo jugadores inscritos en la quiniela pueden pronosticar.
- El plazo para pronosticar cierra X minutos antes del inicio del partido (configurable via `PREDICTION_DEADLINE_MINUTES`).
- El pronóstico incluye: goles local y goles visitante.
- Una vez cerrado el plazo, el pronóstico no puede crearse ni editarse.
- Vista "mis pronósticos" por quiniela.
- Pronósticos de otros jugadores visibles solo tras cierre del plazo.

**Modelos de dominio:**
- `Prediction` (jugador_id, partido_id, quiniela_id, goles_local, goles_visitante, enviado_en)
  - Restricción única: `(jugador_id, partido_id, quiniela_id)`

**Reglas de negocio (en dominio):**
- Si `ahora >= partido.fecha - PREDICTION_DEADLINE_MINUTES` → lanzar `PredictionClosedError`
- Los pronósticos ajenos no se exponen hasta que cierre el plazo del partido

**Endpoints (vistas):**
- `GET/POST /quinielas/<slug>/partidos/<match_id>/predecir/` — crear/editar pronóstico (jugador inscrito)
- `GET /quinielas/<slug>/mis-pronosticos/` — pronósticos propios del jugador en esa quiniela
- `GET /quinielas/<slug>/pronosticos/<match_id>/` — pronósticos del grupo tras cierre de plazo

---

### 4.5 `scoring` — Puntuación y Rankings

**Sistema de puntos (por quiniela, con defaults configurables):**

| Resultado | Puntos |
|-----------|--------|
| Resultado exacto (ej: pronosticó 2-1 y fue 2-1) | 3 pts |
| Ganador correcto + diferencia de goles exacta | 2 pts |
| Solo ganador correcto (o empate correcto) | 1 pt |
| Incorrecto | 0 pts |

**Funcionalidades:**
- Cálculo de puntos automático al registrar resultado de partido.
- Leaderboard por quiniela: ranking completo para jugadores inscritos, top 10 para usuarios públicos.
- Historial de puntos partido a partido por jugador.
- Estadísticas por jugador: racha de aciertos, % de exactos.

**Modelos de dominio:**
- `Score` (jugador_id, quiniela_id, partido_id, puntos_obtenidos, tipo_acierto: `exacto`|`diferencia`|`ganador`|`fallo`)

**Endpoints (vistas):**
- `GET /quinielas/<slug>/leaderboard/` — tabla de posiciones (inscrito: completa / público: top 10)
- `GET /quinielas/<slug>/estadisticas/<user_id>/` — estadísticas de un jugador (inscrito o moderador)

---

### 4.6 `notifications` — Notificaciones

**Tipos de notificación (MVP):**
- Recordatorio: "Faltan 2 horas para que cierre el plazo del partido X"
- Alerta: "Resultado disponible: Partido X terminó Y-Z"
- Bienvenida: "Fuiste inscrito en la quiniela X"

**Mecanismo:**
- Notificaciones in-app almacenadas en base de datos.
- Envío por email usando Django email backend (SMTP o SendGrid).
- Las tareas se ejecutan con `django-q2` (scheduler simple) o cron Railway.

**Modelos de dominio:**
- `Notification` (usuario_id, tipo, mensaje, leída: bool, creada_en, metadata: JSON)

**Endpoints (vistas):**
- `GET /notificaciones/` — lista de notificaciones del usuario autenticado
- `POST /notificaciones/<id>/leer/` — marcar como leída
- `POST /notificaciones/leer-todas/` — marcar todas como leídas

---

### 4.7 Panel del Moderador

Sección exclusiva para usuarios con rol `Moderador`. No es el panel `/admin/` de Django — es una interfaz web dentro de la app.

**Funcionalidades:**
- Ver lista de todos los jugadores y su estado (activo/inactivo).
- Activar o desactivar la cuenta de un jugador.
- Promover un usuario Público a Jugador.
- Ver todas las quinielas activas.
- Inscribir o dar de baja jugadores en quinielas.
- Ver rankings y resultados de cualquier quiniela.

**Endpoints (vistas):**
- `GET /moderador/` — dashboard del moderador
- `GET /moderador/jugadores/` — lista de usuarios públicos y jugadores
- `POST /moderador/jugadores/<id>/activar/` — activar cuenta
- `POST /moderador/jugadores/<id>/desactivar/` — desactivar cuenta
- `POST /moderador/jugadores/<id>/promover/` — promover a Jugador
- `GET /moderador/quinielas/` — lista de quinielas con stats
- `GET /moderador/quinielas/<slug>/inscripciones/` — jugadores inscritos
- `POST /moderador/quinielas/<slug>/inscripciones/agregar/` — inscribir jugador
- `POST /moderador/quinielas/<slug>/inscripciones/<id>/baja/` — dar de baja

---

## 5. Docker — Optimización para Railway

### Estrategia de costos en Railway

Railway cobra por CPU + RAM usada. Para minimizar costos:

1. **Imagen base slim:** `python:3.12-slim` — no Alpine (problemas con psycopg2 y compilación)
2. **Multi-stage build:** separar dependencias de build del runtime
3. **Sin servidor de desarrollo:** usar `gunicorn` en producción, no `runserver`
4. **Whitenoise** para servir archivos estáticos directamente desde Django (evitar un servicio nginx separado)
5. **Un solo servicio en Railway:** app Django + static (con whitenoise) en un container
6. **PostgreSQL:** usar el plugin PostgreSQL nativo de Railway (no un container separado)
7. **Variables de entorno:** Railway las inyecta automáticamente, no necesitamos `.env` en producción

### `docker/Dockerfile` (producción)

```dockerfile
# --- Stage 1: builder ---
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/production.txt .
RUN pip install --no-cache-dir --prefix=/install -r production.txt

# --- Stage 2: runtime ---
FROM python:3.12-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . .

RUN python manage.py collectstatic --noinput --settings=config.settings.production

EXPOSE 8000

ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
```

### `docker/Dockerfile.dev` (desarrollo local)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/development.txt .
RUN pip install --no-cache-dir -r development.txt

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

### `docker-compose.yml` (desarrollo local)

```yaml
version: "3.9"

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: polla_futbolera
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - polla_network

  web:
    build:
      context: .
      dockerfile: docker/Dockerfile.dev
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/polla_futbolera
      DJANGO_SETTINGS_MODULE: config.settings.development
      SECRET_KEY: dev-secret-key-change-in-production
      DEBUG: "True"
    depends_on:
      - db
    networks:
      - polla_network

  worker:
    build:
      context: .
      dockerfile: docker/Dockerfile.dev
    command: python manage.py qcluster
    volumes:
      - .:/app
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/polla_futbolera
      DJANGO_SETTINGS_MODULE: config.settings.development
      SECRET_KEY: dev-secret-key-change-in-production
      DEBUG: "True"
    depends_on:
      - db
    networks:
      - polla_network

networks:
  polla_network:
    driver: bridge

volumes:
  postgres_data:
```

### `railway.toml`

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "docker/Dockerfile"

[deploy]
startCommand = "gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2"
healthcheckPath = "/health/"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
```

---

## 6. Variables de Entorno

```env
# Django
SECRET_KEY=
DJANGO_SETTINGS_MODULE=config.settings.production
DEBUG=False
ALLOWED_HOSTS=*.railway.app,tu-dominio.com

# Base de datos (Railway la provee automáticamente como DATABASE_URL)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=

# API de fútbol (a completar cuando se elija)
FOOTBALL_API_KEY=
FOOTBALL_API_BASE_URL=

# App
PREDICTION_DEADLINE_MINUTES=60
```

---

## 7. Dependencias Python

### `requirements/base.txt`
```
Django==5.2.*
psycopg[binary]==3.*
gunicorn==22.*
whitenoise[brotli]==6.*
django-q2==1.*
httpx==0.*              # cliente HTTP async para API de fútbol
python-decouple==3.*    # manejo de variables de entorno
Pillow==10.*            # procesamiento de imágenes (avatares)
```

### `requirements/development.txt`
```
-r base.txt
django-debug-toolbar==4.*
factory-boy==3.*
pytest-django==4.*
```

### `requirements/production.txt`
```
-r base.txt
sentry-sdk[django]==2.*   # monitoreo de errores
```

---

## 8. Settings por Entorno

### `config/settings/base.py`
- Apps instaladas, middleware, templates, autenticación Django nativa
- Whitenoise en MIDDLEWARE (segunda posición, después de SecurityMiddleware)
- `STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"`
- `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`
- Configuración `django-q2` para tareas programadas
- Creación de Django Groups `Jugador` y `Moderador` en una migración de datos inicial

### `config/settings/development.py`
- `DEBUG = True`
- `DATABASE_URL` local desde `.env`
- Email backend en consola: `django.core.mail.backends.console.EmailBackend`

### `config/settings/production.py`
- `DEBUG = False`
- `DATABASE_URL` desde variable de entorno Railway
- `SECURE_SSL_REDIRECT = True`
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`
- Sentry inicializado

---

## 9. Endpoint de Salud

```python
# shared/infrastructure/views.py
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({"status": "ok"})
```

Registrar en `config/urls.py` como `/health/` — requerido por Railway para healthcheck.

---

## 10. Tareas Programadas (django-q2)

| Tarea | Frecuencia | Descripción |
|-------|------------|-------------|
| `sync_fixtures` | Cada 6 horas | Sincroniza partidos próximos desde API de fútbol |
| `sync_results` | Cada 5 minutos (días de partido) | Actualiza resultados de partidos en curso |
| `calculate_scores` | Trigger por resultado | Calcula puntos al registrar resultado de un partido |
| `send_prediction_reminders` | Cada hora | Envía recordatorios si faltan < 2 horas para el cierre |

En Railway, el worker de django-q2 se configura como un segundo servicio (mismo repo, distinto `startCommand`: `python manage.py qcluster`).

---

## 11. Flujo de Datos Principal

```
[Usuario Público]  →  ver quinielas, top 10, resultados (solo lectura)

[Jugador]  →  [Vista Django]  →  [Servicio de Aplicación]
                                        ↓
                                 [Puerto de Dominio]
                                        ↓ verifica inscripción + plazo
                                 [Repositorio (ORM Django)]
                                        ↓
                                    [PostgreSQL]

[API Externa]  ←  [Adaptador Football API]  ←  [Tarea django-q2]
                                                     ↓
                                          [Servicio de Aplicación]
                                                     ↓
                                       [Match actualizado → Score calculado]
                                                     ↓
                                       [Leaderboard de Quiniela actualizado]

[Moderador]  →  /moderador/  →  inscribir jugadores, activar cuentas
[Superadmin]  →  /admin/     →  crear quinielas, torneos, asignar roles
```

---

## 12. Decisiones Pendientes

| Decisión | Opciones | Impacto |
|----------|----------|---------|
| API de fútbol | API-Football / football-data.org / otra | Afecta `FootballAPIPort` adapter |
| Proveedor email | SendGrid / Mailgun / Gmail SMTP | Afecta settings de producción |
| Tarea scheduler | django-q2 (worker) / cron Railway | Afecta costo en Railway |
| HTMX | Sí / No | Mejora UX sin build JS, opcional en MVP |

---

## 13. Orden de Implementación Recomendado

1. Scaffold inicial: estructura de carpetas, configuración Django, Docker, settings por entorno
2. `shared/` — base classes de dominio, excepciones, cliente HTTP base
3. `accounts` — registro, login, logout, perfil + sistema de roles (Django Groups: `Jugador`, `Moderador`) + helpers de permisos
4. `tournaments` — modelos, puerto de API externa, adaptador stub/mock
5. `quinielas` — modelos `Quiniela` e `Inscripcion`, vistas públicas y panel del moderador
6. `predictions` — lógica de pronósticos con reglas de cierre de plazo, referenciando quiniela
7. `scoring` — motor de puntuación y leaderboard por quiniela
8. `notifications` — notificaciones in-app y email (incluyendo notificación de inscripción)
9. Integración real con API de fútbol elegida
10. Tarea scheduler de sincronización
11. Polish de templates y UX
12. Configuración Railway + deploy

---

*Este documento es la fuente de verdad para el agente de backend. Cualquier decisión de implementación no cubierta aquí debe seguir los principios de arquitectura hexagonal: el dominio no conoce Django ni la base de datos; los adaptadores son intercambiables. Los permisos se verifican siempre en la capa de vista (decoradores o mixins), nunca se asume el rol del usuario sin comprobarlo.*
