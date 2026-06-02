#!/usr/bin/env bash
# Render.com build script: install deps, collect static files, run migrations.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
