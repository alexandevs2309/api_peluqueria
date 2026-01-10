"""
Settings de producción - backend/settings_prod.py
"""
from .settings import *
import os

# SEGURIDAD CRÍTICA
DEBUG = False
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')  # OBLIGATORIO en prod
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS')

# SSL/TLS OBLIGATORIO
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Headers de seguridad
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Rate limiting ESTRICTO
THROTTLE_RATES = {
    'user': '300/hour',
    'anon': '30/hour',
    'login': '3/min',
    'register': '2/hour',
    'password_reset': '2/hour',
}

# Database - OBLIGATORIO connection pooling
DATABASES['default'].update({
    'CONN_MAX_AGE': 300,
    'OPTIONS': {
        'MAX_CONNS': 20,
        'sslmode': 'require',
    }
})

# Celery - NO eager en producción
CELERY_TASK_ALWAYS_EAGER = False

# Logging - Solo errores críticos por email
ADMINS = [('Admin', env('ADMIN_EMAIL'))]
MANAGERS = ADMINS

# Cache - Redis OBLIGATORIO
if not CACHES['default']['LOCATION'].startswith('redis://'):
    raise ValueError("Redis cache OBLIGATORIO en producción")

# Email - SendGrid OBLIGATORIO
if not SENDGRID_API_KEY or not SENDGRID_API_KEY.startswith('SG.'):
    raise ValueError("SendGrid API key OBLIGATORIO en producción")

# Sentry - OBLIGATORIO
if not SENTRY_DSN:
    raise ValueError("Sentry DSN OBLIGATORIO en producción")