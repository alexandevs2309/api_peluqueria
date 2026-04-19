#!/usr/bin/env bash
# build.sh — Render Build Command
# Se ejecuta una vez antes de arrancar el web service.
set -euo pipefail

echo "[build] Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[build] Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

echo "[build] Aplicando migraciones..."
python manage.py migrate --noinput

echo "[build] Creando planes por defecto..."
python manage.py create_default_plans

echo "[build] Listo."
