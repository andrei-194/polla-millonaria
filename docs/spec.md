# Spec Técnico — Polla Futbolera

**Versión:** 1.0  
**Fecha:** 2026-06-01  
**Arquitectura:** Hexagonal (Application / Domain / Infrastructure)  
**Entorno destino:** Railway  

---

## 1. Resumen del Proyecto

Sistema web monolítico de quinielas futbolísticas privadas. Los usuarios crean grupos cerrados, invitan participantes, pronostican resultados de torneos reales (obtenidos vía API externa) y compiten en rankings internos.

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
│   ├── accounts/                 ← autenticación y perfiles
│   │   ├── application/          ← casos de uso (servicios de aplicación)
│   │   ├── domain/               ← entidades, value objects, puertos (interfaces)
│   │   └── infrastructure/       ← modelos Django, repositorios, adaptadores
│   │
│   ├── groups/                   ← grupos y ligas privadas
│   │   ├── application/
│   │   ├── domain/
│   │   └── infrastructure/
│   │
│   ├── tournaments/              ← torneos, fixtures, resultados
│   │   ├── application/
│   │   ├── domain/
│   │   └── infrastructure/
│   │
│   ├── predictions/              ← pronósticos de usuarios
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

## 3. Módulos del Sistema

### 3.1 `accounts` — Autenticación y Perfiles

**Funcionalidades:**
- Registro con username + email + password (Django auth nativo)
- Login / logout con sesiones
- Perfil de usuario con avatar y estadísticas globales
- Cambio de contraseña

**Modelos de dominio:**
- `User` (extiende AbstractUser de Django)
- `UserProfile` (avatar, bio, stats agregadas)

**Endpoints (vistas):**
- `POST /accounts/register/`
- `POST /accounts/login/`
- `POST /accounts/logout/`
- `GET/POST /accounts/profile/`
- `GET/POST /accounts/password/change/`

---

### 3.2 `groups` — Grupos y Ligas Privadas

**Funcionalidades:**
- Crear un grupo con nombre, descripción y código de invitación único
- Unirse a un grupo mediante código o link de invitación
- Roles: Administrador (creador) y Miembro
- El admin puede expulsar miembros y regenerar el código de invitación
- Un usuario puede pertenecer a múltiples grupos
- Un grupo puede tener múltiples torneos activos simultáneamente

**Modelos de dominio:**
- `Group` (nombre, slug, código_invitación, creado_por, fecha_creación)
- `GroupMembership` (usuario, grupo, rol: admin|member, fecha_unión)

**Endpoints (vistas):**
- `GET /groups/` — listar grupos del usuario
- `POST /groups/create/` — crear grupo
- `GET /groups/<slug>/` — detalle del grupo
- `POST /groups/join/` — unirse con código
- `GET /groups/<slug>/invite/` — ver/regenerar link de invitación
- `POST /groups/<slug>/members/<id>/remove/` — expulsar miembro

---

### 3.3 `tournaments` — Torneos y Partidos

**Funcionalidades:**
- Un grupo puede activar un torneo (ej: Champions 2025/26, Copa América)
- El torneo tiene fases (grupos, octavos, cuartos, semis, final)
- Los partidos (fixtures) se sincronizan desde una API externa
- Los resultados se actualizan automáticamente cuando el partido termina
- Un admin de grupo puede forzar sincronización manual

**Modelos de dominio:**
- `Tournament` (nombre, código_externo, temporada, estado: activo|finalizado)
- `GroupTournament` (grupo, torneo, fecha_activación) ← relación many-to-many
- `Match` (torneo, fase, equipo_local, equipo_visitante, fecha, resultado, estado)
- `Team` (nombre, código, logo_url)

**Puerto de API externa:**
```python
# domain/ports.py
class FootballAPIPort(Protocol):
    def fetch_fixtures(self, tournament_code: str, season: str) -> list[MatchDTO]: ...
    def fetch_results(self, match_external_id: str) -> ResultDTO: ...
```

**Adaptador:** `infrastructure/adapters.py` implementa `FootballAPIPort` para la API elegida (API-Football, football-data.org, etc.). El adaptador es intercambiable sin tocar el dominio.

**Sincronización:** Tarea periódica con `django-q2` o `Celery` (a definir). En Railway se puede usar un `worker` service separado o un cron job nativo de Railway.

**Endpoints (vistas):**
- `GET /tournaments/` — listar torneos disponibles
- `POST /groups/<slug>/tournaments/add/` — activar torneo en grupo
- `GET /groups/<slug>/tournaments/<id>/` — fixtures del torneo en el grupo
- `POST /groups/<slug>/tournaments/<id>/sync/` — sincronización manual (admin)

---

### 3.4 `predictions` — Pronósticos

**Funcionalidades:**
- Cada miembro de un grupo puede pronosticar el resultado de cada partido
- El plazo para pronosticar cierra X minutos antes del inicio del partido (configurable)
- El pronóstico incluye: goles local, goles visitante
- Una vez cerrado el plazo, el pronóstico no puede editarse
- Vista de "mis pronósticos" y "pronósticos del grupo" (visible solo tras cierre)

**Modelos de dominio:**
- `Prediction` (usuario, partido, grupo, goles_local, goles_visitante, enviado_en)
- Restricción: única por (usuario, partido, grupo)

**Reglas de negocio (en dominio):**
- Si `ahora >= partido.fecha - PREDICTION_DEADLINE_MINUTES` → no se puede crear/editar
- Los pronósticos de otros usuarios no se muestran hasta que cierre el plazo

**Endpoints (vistas):**
- `GET /groups/<slug>/tournaments/<id>/matches/<match_id>/predict/`
- `POST /groups/<slug>/tournaments/<id>/matches/<match_id>/predict/`
- `GET /groups/<slug>/tournaments/<id>/predictions/` — vista grupal

---

### 3.5 `scoring` — Puntuación y Rankings

**Sistema de puntos (configurable por grupo, con defaults):**

| Resultado | Puntos |
|-----------|--------|
| Resultado exacto (ej: 2-1 y pronosticó 2-1) | 3 pts |
| Ganador correcto + diferencia de goles correcta | 2 pts |
| Solo ganador correcto (o empate correcto) | 1 pt |
| Incorrecto | 0 pts |

**Funcionalidades:**
- Cálculo de puntos automático al registrar resultado de partido
- Tabla de posiciones por grupo + torneo
- Historial de puntos partido a partido
- Estadísticas: racha de aciertos, % de exactos, etc.

**Modelos de dominio:**
- `Score` (usuario, grupo, torneo, partido, puntos_obtenidos, tipo_acierto)
- `Leaderboard` (vista materializada o calculada: ranking por grupo+torneo)

**Endpoints (vistas):**
- `GET /groups/<slug>/tournaments/<id>/leaderboard/` — tabla de posiciones
- `GET /groups/<slug>/tournaments/<id>/stats/<user_id>/` — estadísticas de usuario

---

### 3.6 `notifications` — Notificaciones

**Tipos de notificación (MVP):**
- Recordatorio: "Faltan 2 horas para que cierre el plazo del partido X"
- Alerta: "Resultado disponible: Partido X terminó Y-Z"
- Invitación: "Te invitaron al grupo X"

**Mecanismo:**
- Notificaciones in-app almacenadas en base de datos
- Envío por email usando Django email backend (SMTP o SendGrid)
- Las tareas se ejecutan con `django-q2` (scheduler simple) o cron Railway

**Modelos de dominio:**
- `Notification` (usuario, tipo, mensaje, leída, creada_en, metadata JSON)

**Endpoints (vistas):**
- `GET /notifications/` — lista de notificaciones del usuario
- `POST /notifications/<id>/read/` — marcar como leída
- `POST /notifications/read-all/` — marcar todas como leídas

---

## 4. Docker — Optimización para Railway

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

## 5. Variables de Entorno

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
INVITATION_LINK_BASE_URL=https://tu-dominio.com
```

---

## 6. Dependencias Python

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

## 7. Settings por Entorno

### `config/settings/base.py`
- Apps instaladas, middleware, templates, autenticación Django nativa
- Whitenoise en MIDDLEWARE (segunda posición, después de SecurityMiddleware)
- `STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"`
- `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`
- Configuración `django-q2` para tareas programadas

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

## 8. Endpoint de Salud

```python
# shared/infrastructure/views.py
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({"status": "ok"})
```

Registrar en `config/urls.py` como `/health/` — requerido por Railway para healthcheck.

---

## 9. Tareas Programadas (django-q2)

| Tarea | Frecuencia | Descripción |
|-------|------------|-------------|
| `sync_fixtures` | Cada 6 horas | Sincroniza partidos próximos desde API de fútbol |
| `sync_results` | Cada 5 minutos (días de partido) | Actualiza resultados de partidos en curso |
| `calculate_scores` | Trigger por resultado | Calcula puntos al registrar resultado |
| `send_prediction_reminders` | Cada hora | Envía recordatorios si faltan < 2 horas |

En Railway, el worker de django-q2 se puede configurar como un segundo servicio (mismo repo, distinto `startCommand`: `python manage.py qcluster`). Esto agrega costo marginal — alternativa: cron jobs de Railway apuntando a un endpoint privado.

---

## 10. Flujo de Datos Principal

```
[Usuario] → [Vista Django] → [Servicio de Aplicación]
                                    ↓
                             [Puerto de Dominio]
                                    ↓
                         [Repositorio (ORM Django)]
                                    ↓
                              [PostgreSQL]

[API Externa] ← [Adaptador Football API] ← [Tarea django-q2]
                                               ↓
                                      [Servicio de Aplicación]
                                               ↓
                                     [Match / Score actualizados]
```

---

## 11. Decisiones Pendientes (para definir antes de comenzar)

| Decisión | Opciones | Impacto |
|----------|----------|---------|
| API de fútbol | API-Football / football-data.org / otra | Afecta `FootballAPIPort` adapter |
| Proveedor email | SendGrid / Mailgun / Gmail SMTP | Afecta settings de producción |
| Tarea scheduler | django-q2 (worker) / cron Railway | Afecta costo en Railway |
| HTMX | Sí / No | Mejora UX sin build JS, opcional en MVP |

---

## 12. Orden de Implementación Recomendado

1. Scaffold inicial: estructura de carpetas, configuración Django, Docker, settings por entorno
2. `shared/` — base classes de dominio, excepciones, cliente HTTP base
3. `accounts` — registro, login, logout, perfil
4. `groups` — CRUD de grupos, invitaciones, membresías
5. `tournaments` — modelos, puerto de API externa, adaptador stub/mock
6. `predictions` — lógica de pronósticos con reglas de cierre de plazo
7. `scoring` — motor de puntuación y leaderboard
8. `notifications` — notificaciones in-app y email
9. Integración real con API de fútbol elegida
10. Tarea scheduler de sincronización
11. Polish de templates y UX
12. Configuración Railway + deploy

---

*Este documento es la fuente de verdad para el agente de backend. Cualquier decisión de implementación no cubierta aquí debe seguir los principios de arquitectura hexagonal: el dominio no conoce Django ni la base de datos; los adaptadores son intercambiables.*
