import os
import sys
from pathlib import Path

os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

# Clear SMTP/email env vars so IntegrationService falls through to debug console
os.environ.pop('RESEND_API_KEY', None)
os.environ.pop('EMAIL_HOST', None)
os.environ.pop('EMAIL_HOST_USER', None)
os.environ.pop('EMAIL_HOST_PASSWORD', None)
os.environ.pop('EMAIL_PORT', None)
os.environ.pop('EMAIL_USE_TLS', None)
os.environ.pop('DEFAULT_FROM_EMAIL', None)

SECRET_KEY = 'test-secret-key-not-for-production'
BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'django_filters',
    'django_ratelimit',
    'drf_spectacular',
    'django_celery_beat',
    # 'allauth',
    # 'allauth.account',
    # 'oauth2_provider',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'apps.auth_api',
    'apps.roles_api',
    'apps.tenants_api',
    'apps.subscriptions_api',
    'apps.billing_api',
    'apps.payments_api',
    'apps.notifications_api',
    'apps.audit_api',
    'apps.employees_api',
    'apps.clients_api',
    'apps.services_api',
    'apps.appointments_api',
    'apps.pos_api',
    'apps.inventory_api',
    'apps.reports_api',
    'apps.settings_api',
    'apps.utils',
    'apps.support_api',
    'apps.tutorials_api',
    'apps.booking_api',
    'apps.chatbot_api',
    'apps.telemetry_api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.tenants_api.middleware.TenantMiddleware',
    'apps.utils.middleware.ErrorContextMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
ROOT_URLCONF = 'backend.urls'
USE_TZ = True
LANGUAGE_CODE = 'es'
STATIC_URL = '/static/'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.debug', 'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
AUTH_USER_MODEL = 'auth_api.User'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
STORAGES = {'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}}
MIGRATION_MODULES = {app: None for app in [
    'admin', 'auth', 'contenttypes', 'sessions', 'messages', 'staticfiles',
    'auth_api', 'roles_api', 'tenants_api', 'subscriptions_api', 'billing_api',
    'payments_api', 'notifications_api', 'audit_api', 'employees_api',
    'clients_api', 'services_api', 'appointments_api', 'pos_api',
    'inventory_api', 'reports_api', 'settings_api', 'support_api',
    'tutorials_api', 'booking_api', 'chatbot_api', 'telemetry_api',
]}
CELERY_TASK_ALWAYS_EAGER = True
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Comprobantes de pago manual: usar un directorio temporal fuera de MEDIA_ROOT.
import tempfile
PROOF_STORAGE_ROOT = os.path.join(tempfile.gettempdir(), 'auron_payment_proofs_tests')
PAYMENT_PROOF_MAX_SIZE_MB = 5
STRIPE_SECRET_KEY = 'sk_test_placeholder_for_tests'
STRIPE_PUBLISHABLE_KEY = 'pk_test_public_key'
STRIPE_WEBHOOK_SECRET = 'whsec_test_secret'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'apps.auth_api.authentication.DualJWTAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'EXCEPTION_HANDLER': 'apps.core.exceptions_handler.exception_handler',
    'DEFAULT_THROTTLE_RATES': {
        'user': '10000/hour',
        'anon': '200/hour',
        'login': '10/min',
        'register': '5/hour',
        'password_reset': '5/hour',
        'mfa_verify': '10/min',
        'chatbot': '200/hour',
    },
}

PAYPAL_SANDBOX = True

SIMPLE_JWT = {
    'AUTH_HEADER_TYPES': ('Bearer',),
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_BLACKLIST_ENABLED': True,
}

AUTHENTICATION_BACKENDS = [
    'apps.roles_api.backends.RoleBasedPermissionBackend',
    'django.contrib.auth.backends.ModelBackend',
]

