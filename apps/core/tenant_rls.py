"""Contexto de Row Level Security (RLS) por tenant — BE-11 / V-05.

Las policies de PostgreSQL leen dos GUC de sesión/transacción:

* ``app.tenant_id``: id del tenant resuelto por autenticación (JWT/cookie) o,
  en el auto-agendamiento público, por el subdomain de la URL.
* ``app.rls_bypass``: ``'on'`` **sólo** para superuser, webhooks
  server-to-server y tareas internas sin tenant.

Regla de oro: **si no hay contexto, no hay filas**. Una consulta directa con un
rol no propietario y sin `set_config` no debe ver datos de ningún tenant.

Modos de propagación
--------------------
Conexión directa (default): ``set_config(..., false)`` a nivel de sesión,
seguido de una limpieza explícita en ``finally``. Las conexiones de Django son
thread-local, por lo que no se comparten entre requests simultáneos.

PgBouncer en modo ``transaction``: una variable de sesión sobreviviría al
cambio de cliente físico y filtraría el tenant a otra petición. En ese modo se
usa ``set_config(..., true)`` dentro de un ``transaction.atomic()`` que envuelve
la vista, de modo que el GUC muere con la transacción. Es el mismoCoste que
``ATOMIC_REQUESTS=True`` pero acotado a ``/api/`` y sólo cuando RLS es activo.

El valor NUNCA se toma del payload, query param ni de un tool MCP.
"""
from __future__ import annotations

from contextlib import contextmanager

from django.conf import settings
from django.db import connection, transaction

TENANT_GUC = "app.tenant_id"
BYPASS_GUC = "app.rls_bypass"

# Webhooks server-to-server: la vista resuelve el tenant desde la firma/Payment.
# No hay usuario autenticado, así que se habilita un bypass decidido por el
# servidor y limitado a estas rutas exactas.
BYPASS_PREFIXES = (
    "/api/payments/stripe/webhook/",
    "/api/payments/azul/webhook/",
    "/api/billing/webhooks/",
)


def _rls_supported() -> bool:
    """Las policies y ``set_config`` sólo existen en PostgreSQL.

    La suite por defecto corre sobre SQLite; el middleware debe ser un no-op
    ahí para no romper los 600+ tests de aplicación (el aislamiento de app se
    prueba por separado en `tests_cross_tenant_isolation.py`).
    """
    return connection.vendor == "postgresql"


def _set(guc: str, value: str, *, local: bool) -> None:
    if not _rls_supported():
        return
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config(%s, %s, %s)", [guc, value, local])


def _local() -> bool:
    return bool(getattr(settings, "PGBOUNCER_ENABLED", False))


def set_tenant_context(tenant_id: int | str) -> None:
    """Fija el tenant de la petición y desactiva el bypass."""
    if not _rls_supported():
        return
    local = _local()
    _set(TENANT_GUC, str(int(tenant_id)), local=local)
    _set(BYPASS_GUC, "off", local=local)


def set_rls_bypass() -> None:
    """Permite ver todas las filas. Sólo para superuser/webhooks/tareas internas."""
    if not _rls_supported():
        return
    local = _local()
    _set(TENANT_GUC, "", local=local)
    _set(BYPASS_GUC, "on", local=local)


def clear_tenant_context() -> None:
    """Limpia ambos GUC. Deja la conexión en modo fail-closed.

    Las policies usan ``NULLIF(current_setting(...), '')`` para que la cadena
    vacía se comporte como ``NULL`` y no falle el cast a ``bigint``.
    """
    if not _rls_supported():
        return
    local = _local()
    _set(TENANT_GUC, "", local=local)
    _set(BYPASS_GUC, "off", local=local)


def _get_guc(guc: str) -> str | None:
    """Lee el valor efectivo de un GUC. ``None`` si no está definido."""
    if not _rls_supported():
        return None
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting(%s, true)", [guc])
        value = cursor.fetchone()[0]
    return value if value not in (None, "") else None


def _restore_context(previous_tenant: str | None, previous_bypass: str | None) -> None:
    if previous_bypass == "on":
        set_rls_bypass()
    elif previous_tenant is not None:
        set_tenant_context(previous_tenant)
    else:
        clear_tenant_context()


@contextmanager
def rls_bypass():
    """Bypass **explícito y temporal** para operaciones internas autorizadas.

    Restaura el contexto anterior al salir, incluso si la operación lanza una
    excepción. Está pensado para los tres casos donde todavía no existe tenant
    (resolución de subdomain en booking, alta de tenant en registro) y para
    tareas/commands internos autorizados. Nunca se activa desde datos del cliente.

    Con PgBouncer los GUC son locales a la transacción: este context manager
    abre una transacción si hace falta (por ejemplo en un worker, que no tiene
    el ``atomic()`` del middleware). Un ``atomic()`` ya existente se reutiliza.
    """
    previous_tenant = _get_guc(TENANT_GUC)
    previous_bypass = _get_guc(BYPASS_GUC)
    if _local():
        # La restauración va DESPUÉS de que el atomic termine (commit o
        # rollback). Si se hiciera en el `finally` interior, los callbacks de
        # `transaction.on_commit()` (p. ej. la auditoría de creación de usuario)
        # correrían con el GUC ya restaurado y no verían el tenant.
        with transaction.atomic():
            set_rls_bypass()
            yield
        _restore_context(previous_tenant, previous_bypass)
    else:
        set_rls_bypass()
        try:
            yield
        finally:
            _restore_context(previous_tenant, previous_bypass)


def _tenant_from_jwt(request) -> None:
    """Resuelve el tenant desde el JWT verificado cuando DRF aún no ha corrido."""
    token = request.META.get("HTTP_AUTHORIZATION", "")
    if token.startswith("Bearer "):
        token = token.split(" ", 1)[1]
    else:
        token = request.COOKIES.get("access_token", "")
    if not token:
        return

    try:
        from django.contrib.auth import get_user_model
        from rest_framework_simplejwt.authentication import JWTAuthentication

        validated = JWTAuthentication().get_validated_token(token)
        user_id = validated.get("user_id")
        if not user_id:
            return
        db_user = (
            get_user_model()
            .objects.only("id", "is_superuser", "tenant_id")
            .filter(pk=user_id)
            .first()
        )
        if db_user is None:
            return
        if db_user.is_superuser:
            set_rls_bypass()
        elif db_user.tenant_id:
            set_tenant_context(db_user.tenant_id)
    except Exception:  # noqa: BLE001 - token inválido => fail closed, sin contexto
        return


def _apply(request) -> None:
    path = request.path
    if any(path.startswith(prefix) for prefix in BYPASS_PREFIXES):
        set_rls_bypass()
        return

    # Auto-agendamiento público: el tenant NO viene del cliente, se resuelve
    # desde el subdomain de la URL, igual que en get_tenant_or_404().
    if path.startswith("/api/booking/"):
        parts = path.strip("/").split("/")
        if len(parts) >= 3:
            from apps.tenants_api.models import Tenant

            # Resolución de tenant por subdomain: todavía no hay contexto.
            # El bypass es temporal y no depende de ningún dato del body/query.
            with rls_bypass():
                tenant = (
                    Tenant.objects.filter(subdomain=parts[2], deleted_at__isnull=True)
                    .only("id")
                    .first()
                )
            if tenant is not None:
                set_tenant_context(tenant.id)
        return

    user = getattr(request, "user", None)
    if getattr(user, "is_authenticated", False):
        if getattr(user, "is_superuser", False):
            set_rls_bypass()
            return
        tenant_id = getattr(user, "tenant_id", None)
        if tenant_id:
            set_tenant_context(tenant_id)
            return

    _tenant_from_jwt(request)


class TenantRLSMiddleware:
    """Fija el contexto RLS antes de la vista y lo limpia después.

    Debe ir DESPUÉS de ``AuthenticationMiddleware`` y ANTES de cualquier
    middleware que consulte datos de negocio (MaintenanceMode, TenantMiddleware).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith("/api/") or not _rls_supported():
            return self.get_response(request)

        # PgBouncer transaction pooling exige GUC locales dentro de transacción.
        if _local():
            with transaction.atomic():
                _apply(request)
                return self.get_response(request)

        try:
            _apply(request)
            return self.get_response(request)
        finally:
            clear_tenant_context()
