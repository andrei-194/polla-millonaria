#!/bin/sh
set -e

# RAILWAY_ROLE=worker arranca solo el qcluster (sin migrations/static)
# RAILWAY_ROLE=web (default) hace el bootstrap completo + gunicorn
if [ "${RAILWAY_ROLE}" = "worker" ]; then
    echo "Starting django-q2 worker..."
    exec python manage.py qcluster
fi

echo "Running migrations..."
python manage.py migrate --noinput

echo "Setting up initial data..."
python manage.py setup_initial_data

echo "Seeding Mundial 2026..."
python manage.py seed_mundial_2026 --quiniela-slug=mundial-2026

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
    echo "Creating superuser..."
    python manage.py createsuperuser --noinput || true
fi

echo "Starting server..."
if [ $# -eq 0 ]; then
    exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 3 --timeout 120
fi
exec "$@"
