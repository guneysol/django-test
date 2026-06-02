#!/usr/bin/env bash
# Render.com build script: install deps, collect static files, run migrations,
# and populate demo data + an admin user.
#
# Seeding runs here (at build time) because Render's Free tier has no shell for
# one-off commands. All steps are idempotent, so re-deploys stay safe.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

# Populate genres, books, reviews and demo members (safe to re-run).
python manage.py seed_data

# Create the admin superuser if it doesn't already exist.
python manage.py shell -c "from django.contrib.auth import get_user_model; U = get_user_model(); U.objects.filter(username='admin').exists() or U.objects.create_superuser('admin', 'admin@example.com', 'admin12345')"
