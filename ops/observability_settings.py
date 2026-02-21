# CONFIGURACIÓN DE OBSERVABILIDAD PROFESIONAL
# Agregar/reemplazar en backend/settings.py

import logging
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

# ============================================
# SENTRY CONFIGURATION (PROFESIONAL)
# ============================================

SENTRY_DSN = env('SENTRY_DSN', default=None)

def add_custom_context(event, hint):
    """Agregar contexto custom a eventos Sentry"""
    if 'request' in hint:
        request = hint['request']
        if hasattr(request, 'tenant') and request.tenant:
            event.setdefault('tags', {})['tenant_id'] = request.tenant.id
        if hasattr(request, 'user') and request.user.is_authenticated:
            event.setdefault('tags', {})['user_id'] = request.user.id
    return event

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(
                transaction_style='url',
                middleware_spans=True,
                signals_spans=True,
            ),
            CeleryIntegration(
                monitor_beat_tasks=True,
                propagate_traces=True,
            ),
            RedisIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            ),
        ],
        traces_sample_rate=1.0 if DEBUG else 0.3,
        profiles_sample_rate=0.1,
        send_default_pii=False,
        environment=env('SENTRY_ENVIRONMENT', default='production'),
        release=env('SENTRY_RELEASE', default='1.0.0'),
        before_send=add_custom_context,
    )

# ============================================
# LOGGING ESTRUCTURADO (JSON)
# ============================================

import os
LOG_DIR = BASE_DIR / 'logs'
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s'
        },
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json' if not DEBUG else 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
        'metrics_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'metrics.log',
            'maxBytes': 10485760,
            'backupCount': 5,
            'formatter': 'json',
        },
    },
    'loggers': {
        'api.requests': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'metrics.financial': {
            'handlers': ['console', 'metrics_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.billing_api': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        '': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}

# ============================================
# MIDDLEWARE (AGREGAR OBSERVABILIDAD)
# ============================================

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.tenants_api.middleware.TenantMiddleware',
    'apps.subscriptions_api.middleware.SubscriptionValidationMiddleware',
    'apps.utils.middleware.StructuredLoggingMiddleware',  # NUEVO
    'apps.utils.middleware.SlowQueryMiddleware',  # NUEVO
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.audit_api.middleware.AuditLogMiddleware',
]

# ============================================
# CELERY BEAT (AGREGAR MÉTRICAS)
# ============================================

CELERY_BEAT_SCHEDULE = {
    # ... existentes ...
    
    # NUEVO: Calcular MRR cada 6 horas
    'calculate-daily-mrr': {
        'task': 'apps.billing_api.tasks.calculate_daily_mrr',
        'schedule': crontab(hour='*/6', minute=0),
    },
}

# ============================================
# VARIABLES DE ENTORNO REQUERIDAS
# ============================================

# Agregar a .env:
# SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
# SENTRY_ENVIRONMENT=production
# SENTRY_RELEASE=1.0.0
