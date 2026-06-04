#!/usr/bin/env bash
set -uo pipefail

echo "[build] Python version:"
python --version
pip --version

echo "[build] Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[build] Static files..."
python manage.py collectstatic --noinput || echo "[build] collectstatic ignorado"

echo "[build] Migrations..."
python scripts/fix_migration_history.py || echo "[build] fix_migration_history ignorado"
python manage.py migrate --noinput || echo "[build] migrate ignorado"

echo "[build] Superadmin..."
python manage.py ensure_superadmin || echo "[build] ensure_superadmin ignorado"

if [ "${RUN_SETUP_SAAS_ON_BUILD:-0}" = "1" ]; then
  echo "[build] Seed SaaS..."
  python manage.py setup_saas || true
else
  echo "[build] Seed SaaS skipped (set RUN_SETUP_SAAS_ON_BUILD=1 to enable)"
fi

echo "[build] Done."
