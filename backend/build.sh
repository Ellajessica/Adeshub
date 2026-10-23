#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install backend dependencies
pip install -r requirements.txt

# Run migrations against production database
python manage.py migrate

# Collect static files for WhiteNoise
python manage.py collectstatic --no-input

# Idempotently provision production superuser from environment variables if set
python manage.py create_admin_from_env
