#!/bin/sh
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Setting up initial data..."
python manage.py setup_initial_data

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
    echo "Creating superuser..."
    python manage.py createsuperuser --noinput || true
fi

echo "Starting server..."
exec "$@"
