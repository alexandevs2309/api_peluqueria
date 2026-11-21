"""Herramientas para operaciones internas autorizadas que necesitan RLS bypass.

El bypass **no** es global: sólo lo activan funciones explícitamente marcadas con
``@internal_task`` o comandos que heredan de ``RLSInternalCommand``. El contexto
se restaura al terminar, incluso cuando la operación falla.
"""
from __future__ import annotations

from functools import wraps

from django.core.management.base import BaseCommand
from django.db import connections
from django.db.models.signals import post_migrate, pre_migrate

from apps.core.tenant_rls import rls_bypass


def internal_task(func):
    """Marca una tarea Celery como operación interna autorizada.

    Debe aplicarse **debajo** de ``@shared_task`` para que Celery registre la
    función con su nombre original y envuelva la ejecución real.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        with rls_bypass():
            return func(*args, **kwargs)

    return wrapper


class RLSInternalCommand(BaseCommand):
    """Base para management commands de administración autorizada.

    Los comandos heredan de esta clase en lugar de ``BaseCommand``. Eso limita
    el bypass a comandos revisados uno a uno, no a todo el intérprete.
    """

    def execute(self, *args, **options):
        with rls_bypass():
            return super().execute(*args, **options)


# ---------------------------------------------------------------------------
# Migraciones
# ---------------------------------------------------------------------------
# Con FORCE ROW LEVEL SECURITY el propietario de las tablas también está sujeto
# a las policies. `manage.py migrate` se ejecuta con el rol propietario (DDL),
# por lo que necesita un bypass explícito mientras corren las migraciones.
# Se fija a nivel de sesión sobre la conexión indicada por Django y se limpia
# al terminar. Nunca se activa en procesos de petición ni en workers.

_MIGRATION_CONNECTIONS: set[str] = set()


def _migration_bypass_on(sender, using, **kwargs) -> None:  # noqa: ANN001
    connection = connections[using]
    if connection.vendor != "postgresql":
        return
    _MIGRATION_CONNECTIONS.add(using)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.tenant_id', '', false)")
        cursor.execute("SELECT set_config('app.rls_bypass', 'on', false)")


def _migration_bypass_off(sender, using, **kwargs) -> None:  # noqa: ANN001
    if using not in _MIGRATION_CONNECTIONS:
        return
    connection = connections[using]
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.rls_bypass', 'off', false)")
    _MIGRATION_CONNECTIONS.discard(using)


def connect_migration_bypass() -> None:
    """Conecta los handlers de bypass sólo para el proceso que corre migraciones.

    Se llama desde ``TenantsApiConfig.ready()``. El bypass queda limitado a la
    conexión usada por ``migrate`` y se desactiva en ``post_migrate``.
    """
    pre_migrate.connect(_migration_bypass_on, dispatch_uid="auron_rls_migration_bypass_on")
    post_migrate.connect(_migration_bypass_off, dispatch_uid="auron_rls_migration_bypass_off")
