#!/usr/bin/env bash
set -euo pipefail

echo "[build] Python version:"
python --version

echo "[build] Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[build] Static files..."
python manage.py collectstatic --noinput

echo "[build] Migrations..." 
python scripts/fix_migration_history.py
python manage.py migrate --noinput

echo "[build] Done."
