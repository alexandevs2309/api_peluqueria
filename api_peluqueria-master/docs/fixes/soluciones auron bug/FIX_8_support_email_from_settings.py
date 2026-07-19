# ============================================================
# FIX 8: apps/tenants_api/middleware.py — email de soporte
# PROBLEMA: La respuesta de tenant inactivo retorna hardcoded:
#            'support_email': 'support@barbershop.com'
#            Eso no es el email de Auron Suite.
#
# SOLUCIÓN: Leer desde settings con fallback sensato.
# ============================================================

# En settings.py — AGREGAR esta variable (si no existe):
# SUPPORT_EMAIL = env('SUPPORT_EMAIL', default='soporte@auron-suite.com')

# En middleware.py — REEMPLAZAR la línea hardcodeada:
# ANTES:
#   'support_email': 'support@barbershop.com'
# DESPUÉS:

from django.conf import settings as django_settings

# En _inactive_tenant_response(), cambiar:
return JsonResponse({
    'error': 'TENANT_INACTIVE',
    'code': 'TENANT_INACTIVE',
    'reason': reason,
    'message': message,
    'tenant_id': getattr(tenant, 'id', None),
    'tenant_subdomain': getattr(tenant, 'subdomain', None),
    'support_email': getattr(django_settings, 'SUPPORT_EMAIL', 'soporte@auron-suite.com'),
    'support_url': getattr(django_settings, 'SUPPORT_URL', 'https://auron-suite.com/soporte'),
}, status=403)


# ============================================================
# FIX 8b: .env.example — agregar variables faltantes
# ============================================================

# Agregar al .env.example:
# SUPPORT_EMAIL=soporte@auron-suite.com
# SUPPORT_URL=https://auron-suite.com/soporte
# SENTRY_DSN=https://xxx@sentry.io/yyy         ← falta en repo actual
