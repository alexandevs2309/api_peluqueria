#!/usr/bin/env bash
set -euo pipefail

echo "[build] Python version:"
python --version
pip --version

echo "[build] Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[build] Static files..."
python manage.py collectstatic --noinput

echo "[build] Migrations..."
# Fix: insert auth_api.0006 directly into django_migrations if missing.
# Django's consistency check runs before --fake can help, so we use SQL.
python scripts/fix_migration_history.py
python manage.py migrate --noinput

if [ "${RUN_SETUP_SAAS_ON_BUILD:-0}" = "1" ]; then
  echo "[build] Seed SaaS..."
  python manage.py setup_saas || true
else
  echo "[build] Seed SaaS skipped (set RUN_SETUP_SAAS_ON_BUILD=1 to enable)"
fi

echo "[build] Done."
