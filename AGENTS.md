# Reglas — api_peluqueria (backend)

- Fuente de verdad: `backend/settings.py`, `backend/urls.py`. Los README y `docs/` pueden estar desactualizados (ver `../ESTADO_Y_PLAN.md`).
- Todo modelo de negocio nuevo hereda `TenantModel` de `apps/core/models.py` y se filtra por `request.tenant`. El tenant viene del JWT, nunca del payload.
- Toda vista nueva declara `permission_map` y usa `TenantPermissionByAction` (deny-by-default). Superuser es la única excepción.
- Importes con `Decimal`, nunca `float`. Escrituras financieras dentro de `transaction.atomic()` e idempotentes.
- No modificar directamente `IMMUTABLE_FIELDS` de ventas confirmadas ni snapshots de nómina.
- Migraciones: crear con `makemigrations`, nunca a mano. Verificar con `python manage.py makemigrations --check --dry-run`.
- Tests: `pytest -q` con `backend.test_settings` (SQLite en memoria, Celery eager). Añadir tests cross-tenant cuando el cambio toque aislamiento.
- `DualJWTAuthentication` está deprecado: no lo uses en código nuevo; migrar a `CookieJWTAuthentication`.
- `run_all_tests.sh` ya usa `FRONTEND_DIR` relativo al workspace y define `warn()` (P0-5 corregido); aun así requiere dependencias instaladas para que las fases pytest/tsc no se marquen como SKIP.
- `deploy-production.sh` copia `.env.production.example` (no existe `.env.example`).
- No imprimir secretos en scripts (`build.sh:29` lo hacía). No commitear `.env`.
- Dominio RD: `DOP`, `America/Santo_Domingo`, `es-DO`, NCF B01/B02/B14/B15. Cambios fiscales/laborales requieren validación profesional: marcar como bloqueadores legales.
