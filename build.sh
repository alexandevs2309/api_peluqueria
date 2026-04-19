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
python manage.py showmigrations tenants_api

echo "[build] Creando datos iniciales (roles, planes, superadmin)..."
python manage.py setup_saas

echo "[build] Listo."
