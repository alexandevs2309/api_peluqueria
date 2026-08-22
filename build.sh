#!/usr/bin/env bash
set -eo pipefail

echo "[build] Python version:"
python --version

echo "[build] Pip version:"
pip --version

echo "[build] Instalando dependencias..."
pip install -r requirements.txt --no-cache-dir

echo "[build] Verificando gunicorn..."
which gunicorn && echo "[build] gunicorn OK" || echo "[build] gunicorn NOT FOUND"

echo "[build] Static files..."
python manage.py collectstatic --noinput || echo "[build] collectstatic ignorado"

echo "[build] Migrations..." 
python scripts/fix_migration_history.py || echo "[build] fix_migration ignorado"
python manage.py migrate --noinput || echo "[build] migrate ignorado"

echo "[build] Testing Django import..."
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django; django.setup()
from django.conf import settings
print('[build] SECRET_KEY:', settings.SECRET_KEY[:10] + '...')
print('[build] DB_HOST:', settings.DATABASES['default']['HOST'])
print('[build] Django import OK')
" || echo "[build] Django import fallo (build continua)"

echo "[build] Done."
