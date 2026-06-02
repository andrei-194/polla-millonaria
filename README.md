# Polla Futbolera

Sistema web de quinielas futbolísticas privadas. Los usuarios crean grupos cerrados, invitan participantes mediante código, pronostican resultados de partidos reales y compiten en un ranking interno por grupo.

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Django 5.2 · Python 3.12 |
| Base de datos | PostgreSQL 16 |
| Frontend | Django Templates · Bootstrap 5 |
| Cola de tareas | django-q2 |
| Contenedores | Docker · Docker Compose |
| Deploy | Railway |

## Arquitectura

Monolito con arquitectura hexagonal por app. Cada módulo en `apps/` sigue la estructura `application / domain / infrastructure`.

```
polla_futbolera/
├── apps/
│   ├── accounts/       # Usuarios y perfiles
│   ├── groups/         # Grupos privados e invitaciones
│   ├── tournaments/    # Torneos, equipos y partidos
│   ├── predictions/    # Pronósticos
│   ├── scoring/        # Puntuación y leaderboard
│   └── notifications/  # Notificaciones in-app y email
├── config/             # Settings, URLs, WSGI
├── docker/             # Dockerfiles y entrypoint
├── docs/               # Spec técnico
├── requirements/       # base · development · production
└── templates/          # Templates Django globales
```

## Desarrollo local

### Requisitos

- Docker y Docker Compose

### Levantar el entorno

```bash
cd polla_futbolera
cp .env.example .env
docker-compose up
```

La aplicación queda disponible en `http://localhost:8000`.  
Las migraciones se aplican automáticamente al arrancar.

### Crear superusuario

```bash
docker-compose exec web python manage.py createsuperuser
```

### Comandos útiles

```bash
# Ejecutar tests
docker-compose exec web python manage.py test

# Abrir shell Django
docker-compose exec web python manage.py shell

# Crear migraciones
docker-compose exec web python manage.py makemigrations
```

## Variables de entorno

Copiar `.env.example` a `.env` y ajustar los valores. Las variables requeridas son:

| Variable | Descripción |
|---|---|
| `SECRET_KEY` | Clave secreta Django |
| `DB_*` | Credenciales PostgreSQL |
| `FOOTBALL_API_KEY` | API key de football-data.org |
| `PREDICTION_DEADLINE_MINUTES` | Minutos de anticipación para cerrar pronósticos |

## Deploy en Railway

El proyecto incluye `railway.toml` y `config/settings/production.py` listos para Railway. Ver `docs/spec.md` para detalles de configuración.
