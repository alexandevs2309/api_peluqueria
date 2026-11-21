"""Settings efímeros para verificar Celery Beat en la Fase E.3.

Igual que ``backend.rls_test_settings`` pero con un schedule de 1 segundo que
encola una tarea interna ya marcada con ``@internal_task``. No se usa en
producción.
"""
from __future__ import annotations

from backend.rls_test_settings import *  # noqa: F401,F403

CELERY_BEAT_SCHEDULE = {
    "rls-e3-internal-probe": {
        "task": "apps.pos_api.tasks.auto_close_old_cash_registers",
        "schedule": 1.0,
    },
}
