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

echo "[build] Testing gunicorn/Django import..."
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
from django.conf import settings
print('[build] SECRET_KEY:', settings.SECRET_KEY[:10] + '...')
print('[build] DB_HOST:', settings.DATABASES['default']['HOST'])
print('[build] Django settings OK')
" 2>&1 || echo "[build] gunicorn import test FAILED (build continues)"

echo "[build] Done."
