"""
Settings de producción - SaaS Peluquerías
CRÍTICO: Usar solo en producción
"""
from .settings import *
import os

# ==========================================
# CONFIGURACIÓN CRÍTICA DE PRODUCCIÓN
# ==========================================

# NUNCA True en producción
DEBUG = False

# OBLIGATORIO: Configurar hosts permitidos
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])
if not ALLOWED_HOSTS:
    raise ValueError("❌ CRÍTICO: ALLOWED_HOSTS debe estar configurado en producción")

# CSRF Origins para frontend
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])
if not CSRF_TRUSTED_ORIGINS:
    raise ValueError("❌ CRÍTICO: CSRF_TRUSTED_ORIGINS debe estar configurado")

# ==========================================
# SEGURIDAD SSL/HTTPS
# ==========================================

# Forzar HTTPS
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Cookies seguras
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Headers de seguridad adicionales
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# ==========================================
# CORS RESTRICTIVO
# ==========================================

# Solo orígenes específicos
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
if not CORS_ALLOWED_ORIGINS:
    raise ValueError("❌ CRÍTICO: CORS_ALLOWED_ORIGINS debe estar configurado")

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # NUNCA True en producción

# ==========================================
# RATE LIMITING ESTRICTO
# ==========================================

THROTTLE_RATES = {
    'user': '300/hour',      # Reducido de 500
    'anon': '30/hour',       # Reducido de 50
    'login': '3/min',        # Reducido de 5
    'register': '2/hour',    # Reducido de 3
    'password_reset': '2/hour',
}

REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = THROTTLE_RATES

# ==========================================
# BASE DE DATOS PRODUCCIÓN
# ==========================================

# Validar DATABASE_URL
DATABASE_URL = env('DATABASE_URL', default=None)
if not DATABASE_URL or not DATABASE_URL.startswith('postgres'):
    raise ValueError("❌ CRÍTICO: DATABASE_URL PostgreSQL requerido en producción")

DATABASES = {
    'default': {
        **env.db(),
        'CONN_MAX_AGE': 300,  # 5 minutos
        'OPTIONS': {
            'sslmode': 'require',  # SSL requerido
        },
    }
}

# ==========================================
# CACHE Y REDIS
# ==========================================

REDIS_URL = env('REDIS_URL', default=None)
if not REDIS_URL:
    raise ValueError("❌ CRÍTICO: REDIS_URL requerido en producción")

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'PASSWORD': env('REDIS_PASSWORD', default=''),
        },
        'TIMEOUT': 300,  # 5 minutos
    }
}

# ==========================================
# CELERY PRODUCCIÓN
# ==========================================

CELERY_BROKER_URL = env('CELERY_BROKER_URL', default=None)
if not CELERY_BROKER_URL:
    raise ValueError("❌ CRÍTICO: CELERY_BROKER_URL requerido")

CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default=None)
if not CELERY_RESULT_BACKEND:
    raise ValueError("❌ CRÍTICO: CELERY_RESULT_BACKEND requerido")

# Configuración robusta para producción
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_IGNORE_RESULT = False
CELERY_RESULT_EXPIRES = 3600  # 1 hora

# ==========================================
# LOGGING PRODUCCIÓN
# ==========================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'django_structlog.formatters.DjangoStructlogJSONFormatter',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'sentry': {
            'level': 'ERROR',
            'class': 'sentry_sdk.integrations.logging.SentryHandler',
        },
    },
    'root': {
        'handlers': ['console', 'sentry'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'sentry'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ==========================================
# SENTRY OBLIGATORIO
# ==========================================

SENTRY_DSN = env('SENTRY_DSN', default=None)
if not SENTRY_DSN:
    raise ValueError("❌ CRÍTICO: SENTRY_DSN requerido en producción")

# ==========================================
# EMAIL PRODUCCIÓN
# ==========================================

SENDGRID_API_KEY = env('SENDGRID_API_KEY', default=None)
if not SENDGRID_API_KEY or not SENDGRID_API_KEY.startswith('SG.'):
    raise ValueError("❌ CRÍTICO: SENDGRID_API_KEY válido requerido")

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'apikey'
EMAIL_HOST_PASSWORD = SENDGRID_API_KEY

DEFAULT_FROM_EMAIL = env('SENDGRID_FROM_EMAIL')
if not DEFAULT_FROM_EMAIL:
    raise ValueError("❌ CRÍTICO: SENDGRID_FROM_EMAIL requerido")

# ==========================================
# ARCHIVOS ESTÁTICOS
# ==========================================

# En producción, usar CDN o S3
STATIC_URL = '/static/'
STATIC_ROOT = '/code/staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = '/code/media'

# ==========================================
# VALIDACIONES FINALES
# ==========================================

# Validar SECRET_KEY
if not SECRET_KEY or len(SECRET_KEY) < 50:
    raise ValueError("❌ CRÍTICO: SECRET_KEY debe tener al menos 50 caracteres")

# Validar que no hay configuraciones de desarrollo
if 'testserver' in ALLOWED_HOSTS:
    raise ValueError("❌ CRÍTICO: 'testserver' no debe estar en ALLOWED_HOSTS en producción")

if 'localhost' in str(CORS_ALLOWED_ORIGINS):
    raise ValueError("❌ CRÍTICO: localhost no debe estar en CORS_ALLOWED_ORIGINS en producción")

# ==========================================
# SPECTACULAR PRODUCCIÓN
# ==========================================

# Restringir acceso a documentación
SPECTACULAR_SETTINGS.update({
    'SERVE_PERMISSIONS': ['rest_framework.permissions.IsAuthenticated'],
    'SERVE_INCLUDE_SCHEMA': False,
})

print("✅ Configuración de producción cargada correctamente")