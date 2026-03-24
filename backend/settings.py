from datetime import timedelta
import os
import sys
import environ
from pathlib import Path
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


env = environ.Env(
    DEBUG=(bool, False),
)
configured_env_file = os.getenv('DJANGO_ENV_FILE')
env_path = None

# En contenedores/producción, tomar variables de entorno como fuente principal.
# Solo cargar archivo .env cuando DEBUG no viene definido en el entorno o se
# especifica explícitamente DJANGO_ENV_FILE.
if configured_env_file:
    env_path = Path(configured_env_file)
    if not env_path.is_absolute():
        env_path = BASE_DIR / configured_env_file
elif 'DEBUG' not in os.environ:
    env_path = BASE_DIR / '.env'

if env_path and env_path.exists():
    environ.Env.read_env(env_path)
SECRET_KEY = env('SECRET_KEY')

# Sentry configuration
SENTRY_DSN = env('SENTRY_DSN', default=None)
if SENTRY_DSN and not env.bool('DISABLE_SENTRY', default=False):
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(transaction_style='url'),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment=env('SENTRY_ENVIRONMENT', default='development'),
        release=env('SENTRY_RELEASE', default='1.0.0'),
    )

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG', default=False)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost', 'web', "api_peluqueria-web-1",
])
if DEBUG:
    ALLOWED_HOSTS.append('testserver')

# Application definition

INSTALLED_APPS = [
    'django_prometheus',  # Métricas Prometheus
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

# librerias de terceros
    'rest_framework.authtoken',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'rest_framework_simplejwt.token_blacklist',    
    'celery',
    'django_celery_beat',

# Apps personalizadas (auth_api PRIMERO)
    'apps.auth_api',
    'apps.tenants_api',
    'apps.roles_api',
    'apps.appointments_api',
    'apps.clients_api',
    'apps.employees_api',
    'apps.services_api',
    'apps.inventory_api',
    'apps.pos_api',
    'apps.billing_api',
    'apps.reports_api',
    'apps.settings_api',
    'apps.subscriptions_api',
    'apps.audit_api',
    'apps.payments_api',
    'apps.notifications_api',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',  # Primera
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # Soporte multiidiomas
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.tenants_api.middleware.TenantMiddleware',
    'apps.subscriptions_api.middleware.SubscriptionValidationMiddleware',
    'apps.subscriptions_api.middleware.APIRateLimitMiddleware',  # Rate limiting por plan
    'apps.utils.middleware.StructuredLoggingMiddleware',  # Logging con tenant_id/user_id
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.audit_api.middleware.AuditLogMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',  # Última
]


# Rate limiting configuration by environment
if DEBUG:
    THROTTLE_RATES = {
        'user': '1000/hour',
        'anon': '200/hour', 
        'login': '10/min',
        'register': '5/hour',
        'password_reset': '5/hour',
    }
else:
    # Production: Strict security limits
    THROTTLE_RATES = {
        'user': '500/hour',
        'anon': '50/hour',
        'login': '5/min',
        'register': '1/day',  # 1 registro por IP/día en producción
        'password_reset': '3/hour',
    }

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'apps.auth_api.authentication.DualJWTAuthentication',  # Soporta localStorage Y cookies
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # Fallback
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100,
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': THROTTLE_RATES,
}

# Stripe configuration
STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = env('STRIPE_PUBLISHABLE_KEY', default='pk_test_1234567890abcdef')

GEO_LOCK_ENABLED = True

SIMPLE_JWT = {
    'AUTH_HEADER_TYPES': ('Bearer',),
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),  # Reducido de 8 horas a 30 min
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),     # Reducido de 30 días a 7 días
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_BLACKLIST_ENABLED': True,
    'TOKEN_OBTAIN_SERIALIZER': 'apps.auth_api.serializers.CustomTokenObtainPairSerializer',
}

if DEBUG:
    CORS_ALLOWED_ORIGINS = env.list(
        'CORS_ALLOWED_ORIGINS',
        default=['http://localhost:4200']
    )
else:
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^https://[\w-]+\.tuapp\.com$",
    ]
    # CSRF protection para requests POST desde frontend
    CSRF_TRUSTED_ORIGINS = env.list(
        'CSRF_TRUSTED_ORIGINS',
        default=['https://app.tudominio.com', 'https://www.tudominio.com']
    )

CORS_ALLOW_CREDENTIALS = True


SPECTACULAR_SETTINGS = {
    'TITLE': 'Sistema de Gestión de Peluquería API',
    'DESCRIPTION': 'API para la gestión de citas, clientes, empleados y servicios de peluquería',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
ROOT_URLCONF = 'backend.urls'
WSGI_APPLICATION = 'backend.wsgi.application'



# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django_prometheus.db.backends.postgresql',
        'NAME': env('DB_NAME', default='barbershop_db'),
        'USER': env('DB_USER', default='postgres'),
        'PASSWORD': env('DB_PASSWORD', default='postgres'),
        'HOST': env('DB_HOST', default='db'),
        'PORT': env('DB_PORT', default='5432'),
        'CONN_MAX_AGE': env.int('CONN_MAX_AGE', default=600),  # 10 min en producción
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'  # 30s max por query
        }
    }
}

# Cache configuration using Redis
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://localhost:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PASSWORD': env('REDIS_PASSWORD', default=''),
        }
    }
}

# Session engine using Redis cache
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Celery configuration for production
CELERY_TASK_ALWAYS_EAGER = env.bool('CELERY_TASK_ALWAYS_EAGER', default=False)
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Santo_Domingo'
APPOINTMENT_NO_SHOW_GRACE_MINUTES = env.int('APPOINTMENT_NO_SHOW_GRACE_MINUTES', default=15)

# Celery Beat Schedule
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'cleanup-expired-trials': {
        'task': 'apps.subscriptions_api.tasks.cleanup_expired_trials',
        'schedule': crontab(hour=2, minute=0),  # Diario a las 2:00 AM
    },
    'check-expired-subscriptions': {
        'task': 'apps.subscriptions_api.tasks.check_expired_subscriptions',
        'schedule': crontab(minute=0),  # Cada hora
    },
    # Tareas de automatización de citas
    'mark-expired-appointments': {
        'task': 'apps.notifications_api.tasks.mark_expired_appointments',
        'schedule': crontab(minute='*/15'),  # Cada 15 minutos
    },
    'send-daily-reminders': {
        'task': 'apps.notifications_api.tasks.send_daily_appointment_reminders',
        'schedule': crontab(hour=8, minute=0),  # Diario a las 8:00 AM
    },
    'notify-upcoming-appointments': {
        'task': 'apps.notifications_api.tasks.notify_upcoming_appointments',
        'schedule': crontab(minute=0),  # Cada hora
    },
    # Tareas existentes de notificaciones
    'send-appointment-reminders': {
        'task': 'apps.notifications_api.tasks.send_appointment_reminders',
        'schedule': crontab(hour=18, minute=0),  # Diario a las 6:00 PM
    },
    'process-scheduled-notifications': {
        'task': 'apps.notifications_api.tasks.process_scheduled_notifications',
        'schedule': crontab(minute='*/15'),  # Cada 15 minutos
    },
    'cleanup-old-notifications': {
        'task': 'apps.notifications_api.tasks.cleanup_old_notifications',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Domingos a las 3:00 AM
    },
    # Reconciliación financiera diaria
    'daily-financial-reconciliation': {
        'task': 'apps.billing_api.tasks.daily_financial_reconciliation',
        'schedule': crontab(hour=4, minute=0),  # Diario a las 4:00 AM
    },
}

# Financial reconciliation alerts
FINANCE_ALERT_EMAILS = env.list('FINANCE_ALERT_EMAILS', default=['finance@yourdomain.com'])
STRIPE_WEBHOOK_SECRET = env('STRIPE_WEBHOOK_SECRET', default='')




# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = 'auth_api.User'

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'apps.roles_api.backends.RoleBasedPermissionBackend',  # Backend personalizado para roles
    'django.contrib.auth.backends.ModelBackend',  # Backend por defecto de Django
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

from django.utils.translation import gettext_lazy as _

LANGUAGE_CODE = 'es'

LANGUAGES = [
    ('es', _('Spanish')),
    ('en', _('English')),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

TIME_ZONE = 'America/Santo_Domingo'

USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = []

# Solo agregar directorio static si existe
if (BASE_DIR / 'static').exists():
    STATICFILES_DIRS.append(BASE_DIR / 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email configuration
FRONTEND_URL = env('FRONTEND_URL', default='http://localhost:4200')

# En desarrollo, redirige todos los emails a esta dirección (limitación de Resend en modo test)
DEV_EMAIL_OVERRIDE = env('DEV_EMAIL_OVERRIDE', default='') if DEBUG else ''

if "pytest" in sys.modules:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
else:
    # Email configuration (Resend SMTP / SendGrid / fallback console)
    SENDGRID_API_KEY = env('SENDGRID_API_KEY', default='')
    DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default=env('SENDGRID_FROM_EMAIL', default='noreply@yourdomain.com'))

    _smtp_host = env('EMAIL_HOST', default='')
    _smtp_password = env('EMAIL_HOST_PASSWORD', default='')

    if _smtp_host and _smtp_password:
        EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
        EMAIL_HOST = _smtp_host
        EMAIL_PORT = env.int('EMAIL_PORT', default=587)
        EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
        EMAIL_HOST_PASSWORD = _smtp_password
        EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
        EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL', default=False)
    elif SENDGRID_API_KEY and SENDGRID_API_KEY.startswith('SG.'):
        EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
        EMAIL_HOST = 'smtp.sendgrid.net'
        EMAIL_PORT = 587
        EMAIL_USE_TLS = True
        EMAIL_HOST_USER = 'apikey'
        EMAIL_HOST_PASSWORD = SENDGRID_API_KEY
    else:
        EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Security settings
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# CRÍTICO: SameSite cookies para prevenir CSRF
SESSION_COOKIE_SAMESITE = 'Strict' if not DEBUG else 'Lax'
CSRF_COOKIE_SAMESITE = 'Strict' if not DEBUG else 'Lax'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # JS necesita leerlo

# Basic security headers (safe for development)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Request payload limits (DoS hardening)
DATA_UPLOAD_MAX_MEMORY_SIZE = env.int('DATA_UPLOAD_MAX_MEMORY_SIZE', default=5 * 1024 * 1024)  # 5MB
FILE_UPLOAD_MAX_MEMORY_SIZE = env.int('FILE_UPLOAD_MAX_MEMORY_SIZE', default=5 * 1024 * 1024)  # 5MB

# Logging mejorado con seguridad
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'security': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.auth_api': {
            'handlers': ['security'],
            'level': 'INFO',
            'propagate': False,
        },
        '': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
        },
    },
}



