"""Settings para verificación RLS contra un PostgreSQL local con roles realistas.

Uso (sin secretos en el repositorio)::

    AURON_RLS_DB_NAME=... AURON_RLS_DB_USER=... AURON_RLS_DB_PASSWORD=... \
    DJANGO_SETTINGS_MODULE=backend.rls_test_settings python manage.py migrate \
        --skip-checks --noinput

El usuario de la BD debe ser explícitamente no propietario, NOSUPERUSER y
NOBYPASSRLS para que las policies se apliquen. `AURON_RLS_PGBOUNCER=1` activa
el modo de GUC por transacción, equivalente a PgBouncer en modo transaction.
"""
from __future__ import annotations

import os

from backend.test_settings import *  # noqa: F401,F403

MIGRATION_MODULES = {}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["AURON_RLS_DB_NAME"],
        "USER": os.environ["AURON_RLS_DB_USER"],
        "PASSWORD": os.environ.get("AURON_RLS_DB_PASSWORD", ""),
        "HOST": os.environ.get("AURON_RLS_DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("AURON_RLS_DB_PORT", "5432"),
        "CONN_MAX_AGE": int(
            os.environ.get(
                "AURON_RLS_CONN_MAX_AGE",
                "0" if os.environ.get("AURON_RLS_PGBOUNCER") == "1" else "600",
            )
        ),
        "CONN_HEALTH_CHECKS": True,
    }
}

# test_settings omite el middleware RLS; en la verificación debe estar activo.
MIDDLEWARE = list(MIDDLEWARE)
if "apps.core.tenant_rls.TenantRLSMiddleware" not in MIDDLEWARE:
    idx = MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware") + 1
    MIDDLEWARE.insert(idx, "apps.core.tenant_rls.TenantRLSMiddleware")

PGBOUNCER_ENABLED = os.environ.get("AURON_RLS_PGBOUNCER") == "1"

# Para la prueba con worker real: broker compartido entre procesos.
CELERY_BROKER_URL = os.environ.get(
    "AURON_RLS_CELERY_BROKER", "redis://127.0.0.1:56379/0"
)
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_ALWAYS_EAGER = os.environ.get("AURON_RLS_CELERY_EAGER") == "1"
