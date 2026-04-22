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
python manage.py migrate --noinput

if [ "${RUN_SETUP_SAAS_ON_BUILD:-0}" = "1" ]; then
  echo "[build] Seed SaaS..."
  python manage.py setup_saas || true
else
  echo "[build] Seed SaaS skipped (set RUN_SETUP_SAAS_ON_BUILD=1 to enable)"
fi

echo "[build] Done."
