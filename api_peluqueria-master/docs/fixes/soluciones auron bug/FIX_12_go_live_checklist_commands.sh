#!/bin/bash
# ============================================================
# FIX 12: GO_LIVE_CHECKLIST.md — ejecutar y evidenciar cada punto
# Este script NO es para ejecutar de un tirón.
# Ejecutar sección por sección. Cada comando produce evidencia.
# ============================================================

set -e

API_URL="${PRODUCTION_API_URL:-https://api.auron-suite.com}"
echo "=== AURON SUITE GO-LIVE VERIFICATION ==="
echo "API: $API_URL"
echo "Fecha: $(date -u '+%Y-%m-%d %H:%M UTC')"
echo ""

# =====================================================
# SECCIÓN 1: Sentry configurado y activo
# =====================================================
echo "--- 1. Verificar Sentry ---"

# 1a. Verificar que SENTRY_DSN está seteado en producción
curl -s "${API_URL}/api/healthz/" | python3 -m json.tool
# → Si aparece 'healthy', el backend arrancó con configuración válida

# 1b. Disparar error de prueba para verificar que Sentry lo captura
# Ejecutar desde Django shell en producción:
python manage.py shell -c "
import sentry_sdk
try:
    raise Exception('TEST: Sentry verification from go-live checklist')
except Exception as e:
    sentry_sdk.capture_exception(e)
    print('✅ Error enviado a Sentry — verificar dashboard en 30 segundos')
"

# 1c. Verificar que el DSN no es vacío
python manage.py shell -c "
from django.conf import settings
dsn = getattr(settings, 'SENTRY_DSN', None)
if dsn and len(dsn) > 20:
    print(f'✅ SENTRY_DSN configurado: {dsn[:30]}...')
else:
    print('❌ SENTRY_DSN no configurado o vacío')
"

echo ""

# =====================================================
# SECCIÓN 2: Backup + Restore
# =====================================================
echo "--- 2. Backup y restore ---"

# 2a. Render PostgreSQL managed database — verificar backups automáticos
# → Render Plan: Si usas Render PostgreSQL de pago, los backups diarios son automáticos.
# → Verificar en Render Dashboard > Databases > [tu DB] > Backups
echo "Render managed PostgreSQL backups: verificar en https://dashboard.render.com"

# 2b. Dump manual de prueba (ejecutar en servidor)
python manage.py dumpdata --natural-foreign --natural-primary \
    --exclude=contenttypes \
    --exclude=auth.permission \
    -o /tmp/auron_backup_$(date +%Y%m%d_%H%M%S).json
echo "✅ Dump manual exitoso: /tmp/auron_backup_*.json"

# 2c. Restore de prueba en entorno aislado
# (Ejecutar en staging, NO en producción)
# python manage.py flush --no-input
# python manage.py loaddata /tmp/auron_backup_YYYYMMDD_HHMMSS.json
# echo "✅ Restore exitoso"

echo ""

# =====================================================
# SECCIÓN 3: Validación de entorno productivo
# =====================================================
echo "--- 3. Validación del entorno ---"

# 3a. DEBUG=False
python manage.py shell -c "
from django.conf import settings
debug = settings.DEBUG
print('✅ DEBUG=False' if not debug else '❌ DEBUG=True EN PRODUCCIÓN — CRÍTICO')
"

# 3b. ALLOWED_HOSTS correcto
python manage.py shell -c "
from django.conf import settings
hosts = settings.ALLOWED_HOSTS
print(f'✅ ALLOWED_HOSTS: {hosts}')
risky = [h for h in hosts if h in ('*', '')]
if risky:
    print(f'❌ ALLOWED_HOSTS contiene wildcard inseguro: {risky}')
"

# 3c. HTTPS activo
python manage.py shell -c "
from django.conf import settings
ssl = getattr(settings, 'SECURE_SSL_REDIRECT', False)
hsts = getattr(settings, 'SECURE_HSTS_SECONDS', 0)
print(f'✅ SECURE_SSL_REDIRECT={ssl}, HSTS={hsts}s' if ssl and hsts > 0 else '⚠️  Revisar HTTPS config')
"

# 3d. Cookies seguras
python manage.py shell -c "
from django.conf import settings
checks = {
    'SESSION_COOKIE_SECURE': getattr(settings, 'SESSION_COOKIE_SECURE', False),
    'SESSION_COOKIE_HTTPONLY': getattr(settings, 'SESSION_COOKIE_HTTPONLY', True),
    'CSRF_COOKIE_SECURE': getattr(settings, 'CSRF_COOKIE_SECURE', False),
}
for k, v in checks.items():
    status = '✅' if v else '❌'
    print(f'{status} {k}={v}')
"

# 3e. Stripe en modo LIVE (no test)
python manage.py shell -c "
from django.conf import settings
key = getattr(settings, 'STRIPE_SECRET_KEY', '')
if key.startswith('sk_live_'):
    print('✅ Stripe en modo LIVE')
elif key.startswith('sk_test_'):
    print('❌ Stripe en modo TEST — cobros NO reales')
else:
    print('❌ STRIPE_SECRET_KEY no configurada')
"

# 3f. Migraciones aplicadas
python manage.py migrate --plan 2>&1 | grep -E "^  No migrations|^  \[X\]|^  \[ \]" | tail -5
echo "✅ Si no hay líneas con [ ] (sin marcar), migraciones al día"

# 3g. Tests críticos de RBAC pasan
python -m pytest apps/employees_api/tests.py -k "rbac or tenant or permission" -q \
    --tb=short 2>&1 | tail -10

echo ""

# =====================================================
# SECCIÓN 4: Healthcheck y workers
# =====================================================
echo "--- 4. Healthcheck y workers ---"

# 4a. Health endpoint
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/api/healthz/")
echo "Health check: HTTP $HEALTH"
[ "$HEALTH" = "200" ] && echo "✅ API healthy" || echo "❌ API no saludable"

# 4b. Celery worker activo (verificar en Render dashboard o logs)
python manage.py shell -c "
from django.core.cache import cache
import uuid
key = f'celery_ping_{uuid.uuid4().hex[:8]}'
cache.set(key, 'ok', timeout=10)
result = cache.get(key)
print('✅ Redis/cache operativo' if result == 'ok' else '❌ Redis no responde')
"

# 4c. CELERY_TASK_ALWAYS_EAGER debe ser False en producción
python manage.py shell -c "
from django.conf import settings
eager = getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False)
print('❌ CELERY_TASK_ALWAYS_EAGER=True — tasks síncronas, NO usar en producción' if eager else '✅ Celery async mode activo')
"

echo ""
echo "=== CHECKLIST COMPLETADO ==="
echo "Fecha de verificación: $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "Responsable: $(git config user.name 2>/dev/null || echo 'N/A')"
echo ""
echo "PRÓXIMOS PASOS POST-CHECKLIST:"
echo "1. Actualizar docs/GO_LIVE_CHECKLIST.md marcando cada ítem"
echo "2. Hacer commit con evidencia: git commit -m 'chore: go-live checklist completed YYYY-MM-DD'"
echo "3. Documentar RTO/RPO medidos en el checklist"
