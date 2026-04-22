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

echo "[build] Seed SaaS..."
python manage.py setup_saas || true

echo "[build] Done."