import os
import sys

os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

SECRET_KEY = 'test-secret-key-not-for-production'

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
    'oauth2_provider',
    'health_check',
    'mptt',
    'simple_history',
    'rest_framework_simplejwt',
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
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
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
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.debug', 'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
AUTH_USER_MODEL = 'auth_api.User'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
STORAGES = {'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}}
MIGRATION_MODULES = {app: None for app in [
    'admin', 'auth', 'contenttypes', 'sessions', 'messages', 'staticfiles',
    'auth_api', 'roles_api', 'tenants_api', 'subscriptions_api', 'billing_api',
    'payments_api', 'notifications_api', 'audit_api', 'employees_api',
    'clients_api', 'services_api', 'appointments_api', 'pos_api',
    'inventory_api', 'reports_api', 'settings_api',
]}
CELERY_TASK_ALWAYS_EAGER = True
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
STRIPE_SECRET_KEY = 'sk_test_placeholder_for_tests'
