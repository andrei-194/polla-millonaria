#!/bin/sh
set -e

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
exec "$@"
