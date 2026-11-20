# Endurecimiento de seguridad — cinco trampas (2026-11-19)

> Rama: `security/hardening-cinco-trampas` (creada desde `master @ cd6d230`).
> Estado: cambios en el working tree, **sin commit, push ni merge**.
> Repo afectado: `api_peluqueria`. No se han tocado los otros tres repos.

---

## 1. Alcance y reglas aplicadas

Se auditaron y corrigieron únicamente las cinco trampas indicadas, sin reescribir
subsistemas y sin modificar autenticación, JWT, cookies, MFA, modelo multi-tenant,
roles base, suscripciones ni contratos REST. Ninguna corrección introdujo una
dependencia nueva ni ejecutó migraciones contra datos reales.

Se aplicaron las invariantes de `AGENTS.md`: tenant derivado del backend,
`is_superuser` como única fuente de verdad para superadministrador, deny-by-default
en permisos, escrituras atómicas y auditoría cuando aplica, `Decimal` en dinero y
sin secretos ni passwords por defecto.

## 2. Metodología

1. Lectura de `AGENTS.md`, `ESTADO_Y_PLAN.md` y auditorías previas.
2. Verificación de `git status --short`, rama y suite base.
3. Lectura del código de los cinco vectores y trazado extremo a extremo.
4. Correcciones mínimas con pruebas negativas en el mismo cambio.
5. Suite completa, `makemigrations --check --dry-run --skip-checks` y
   comparación contra `HEAD` en worktree aislado para los tests no recogidos.

## 3. Clasificación global

| Trampa | Clasificación inicial | Estado final |
|---|---|---|
| 1. Rate limiting no atómico y fail-open | **ALTO** | Corregido; riesgo residual **MEDIO** por contador local por proceso |
| 2. Accesibilidad / frontend | **NO APLICA** en este repo | Documentado; corresponde a `auron-tailadmin` |
| 3. RLS inexistente | **ALTO** | **No corregido**: requiere decisión arquitectónica |
| 4. Permisos antes de escribir | **CRÍTICO / ALTO** | Corregido salvo decisión de despliegue del webhook |
| 5. Bucles y procesos ilimitados | **MEDIO** | Corregido; checkpoints globales siguen pendientes |

## 4. Trampa 1 — Rate limiting

**Hallazgo ALTO.** `cache.get` + `cache.set` no era atómico, el backend se elegía
por substring `localhost`, las claves no incluían tenant, las rutas de cobro
estaban exentas, `SubscriptionValidationMiddleware` usaba otra definición de
superadmin y no había timeout de Redis. Existía un bypass concurrency y un
fail-open total ante caída de caché.

Correcciones:

- `cache.add` + `cache.incr` para un contador atómico por `tenant.id`, usuario,
  scope y hora.
- Clave de sincronización `sub_sync:{tenant}` con `cache.add`; `usub:{tenant}:{user}`
  con borrado tenant-scoped.
- Rutas de cobro exentas solo del paywall, pero con cuota del plan.
- `is_superuser` como única excepción; se eliminó el fallback por nombre de rol.
- Degradación controlada: si Redis falla se usa un limitador local thread-safe y
  la respuesta lleva `X-RateLimit-Degraded: 1`.
- `REDIS_CACHE_TIMEOUT` (default `0.5 s`) para connect/socket y `TIMEOUT` de cache.
- Cabeceras de límite también en respuestas 429.

**No se declara protección completa:** durante una caída de Redis el contador de
emergencia es por proceso, no distribuido. Con N workers el límite efectivo puede
ser N veces el del plan. Dejar Redis caído no abre tráfico ilimitado, pero sí
multiplica el cupo. Se recomienda decidir entre fail-closed estricto (503) o un
servicio de rate limit compartido antes de multi-replica.

## 5. Trampa 2 — Accesibilidad / frontend

**NO APLICA en `api_peluqueria`.** Este repo solo contiene plantillas de correo
(`templates/emails/`, 23 archivos); no hay interfaz de usuario propia. Los
componentes observables están en `auron-tailadmin`:

- `src/app/shared/components/ui/modal/modal.component.ts` / `.html`
- `src/app/shared/components/global-search/global-search.component.*`
- `src/app/shared/components/app-header/app-header.component.*`

No se ha modificado ninguno. Cualquier corrección de foco, roles ARIA o navegación
debe hacerse en ese repo con su propia rama y suite. Trasladar el hallazgo sin
inventar una corrección backend evita cambiar contratos por un problema de UI.

## 6. Trampa 3 — Row Level Security

**ALTO y no corregido.** No existe `ENABLE ROW LEVEL SECURITY`, `CREATE POLICY` ni
DDL `.sql` en el repo. `DB_USER` por defecto es `postgres` y el aislamiento depende
exclusivamente de la capa Django. PgBouncer usa `pool_mode=transaction`, por lo que
un `SET` de sesión sería incorrecto.

No se activó RLS, no se crearon roles SQL, no se añadieron columnas y no se
ejecutó migración alguna. Hacerlo sin decisión previa podría dejar la aplicación
sin acceso a sus propias tablas o crear una falsa sensación de aislamiento.

Propuesta pendiente de autorización:

1. Rol SQL no owner (`auron_app`) y usuario de aplicación separado del owner.
2. Columnas `tenant_id` aditivas en tablas hijas que hoy no la tienen.
3. Policies con `current_setting('app.tenant_id', true)::bigint`.
4. Middleware/ORM que ejecute `set_config('app.tenant_id', %, true)` dentro de
   `transaction.atomic()` (compatible con PgBouncer transaction pooling).
5. Activación reversible por entorno, primero en staging, nunca en producción
   sin plan de rollback.

## 7. Trampa 4 — Permisos antes de escribir

Hallazgos corregidos en el mismo cambio:

| ID | Hallazgo | Clasificación | Corrección |
|---|---|---|---|
| C-1 | `role='SuperAdmin'` convertía a cualquier creador en superusuario | **CRÍTICO** | Solo `is_superuser` real puede crear otro superusuario |
| M-4 | `change_role` bloqueaba `Super-Admin` pero no `SuperAdmin` | **CRÍTICO** | Bloquea ambos nombres y cualquier rol `scope='GLOBAL'`; transacción y tenant explícitos |
| A-1 | `deactivate_plan` modificaba catálogo global sin permiso de superadmin | **ALTO** | Incluido en `get_permissions` con `IsSuperAdmin` y auditado en la misma transacción |
| A-2 | Webhook de WhatsApp `AllowAny` con firma opcional y secreto vacío | **ALTO** | `whatsapp_connect` genera secreto, lo envía en la URL configurada, exige token y verifica HMAC si viene; fail-closed |
| A-3 | `has_object_permission` devolvía `True` si no resolvía tenant | **ALTO** | Deny-by-default; resuelve tenant por relaciones hijas conocidas; catálogos globales lo declaran explícitamente |
| M-1 | `bulk_activate` / `bulk_deactivate` / `bulk_delete` sin auditoría ni límite consistente | **ALTO** | Validación estricta de IDs, tope 20, `transaction.atomic()` y auditoría por tenant |
| M-3 | Acción `reply` de soporte sin `permission_map` | **MEDIO** | Añadida al mapa y a la lógica de objeto con `change_supportticket` |
| B-3 | Borrado de usuarios y bulk sin atomicidad/auditoría | **ALTO** | Auditoría y borrado en una transacción; validación y tope en bulk |

Además, las respuestas cacheadas de PayPal ahora comprueban dueño mediante una
clave auxiliar, sin añadir campos al contrato de respuesta.

**Residual A-2:** el token viaja en query string porque el proveedor actual no
permite configurar headers desde `set_webhook`. Puede quedar en logs de acceso.
Se recomienda moverlo a `X-Webhook-Token` cuando el proveedor lo soporte, o
rotarlo periódicamente. Clasificación **BAJO**.

## 8. Trampa 5 — Bucles y recursos ilimitados

Hallazgos corregidos:

- `LimitOffsetPagination` no aplicaba `MAX_PAGE_SIZE`: se introdujo
  `BoundedLimitOffsetPagination` con `max_limit=200` (`BAJO/MEDIO`). El default de
  25 no cambia; 200 es un techo deliberado para minimizar ruptura de clientes.
- `mark_expired_appointments` materializaba todas las citas vencidas: ahora
  procesa lotes de 500 con tope de 200 lotes y continúa en la siguiente ejecución
  mediante `id__gt` (`MEDIO`).
- SSE usaba `while True` y `socket_timeout=None`: ahora tiene timeout de socket y
  de espera, cota de heartbeats y cota absoluta de 30 minutos, con reloj
  inyectable para prueba (`MEDIO`).
- Generación de subdominio/nombre de tenant con `while` sin cota: sustituida por
  intervalo acotado y fallback UUID (`BAJO`).
- `cron_run` esperaba hasta 120 s por tarea: reducido a 15 s y distingue
  `timeout` de `error` (`MEDIO`).
- Cliente Stripe sin timeout: `configure_stripe()` centraliza timeout de 30 s y
  `max_network_retries=2` en billing y POS (`MEDIO`).

Queda pendiente, fuera de este cambio, la revisión de checkpoints globales y
presupuestos de tiempo en el resto de workers/colas; se documenta como
**BAJO** porque no se ha encontrado un bucle adicional sin cota en el código
revisado.

## 9. Archivos modificados

`apps/auth_api/serializers.py`, `apps/auth_api/views.py`,
`apps/billing_api/stripe_client.py` (nuevo), `apps/billing_api/stripe_service.py`,
`apps/billing_api/tasks.py`, `apps/core/pagination.py` (nuevo),
`apps/core/tenant_permissions.py`, `apps/core/test_security_hardening.py` (nuevo),
`apps/notifications_api/sse.py`, `apps/notifications_api/tasks.py`,
`apps/payments_api/stripe_provider.py`, `apps/roles_api/role_hierarchy.py`,
`apps/settings_api/barbershop_views.py`, `apps/settings_api/tests.py`,
`apps/subscriptions_api/middleware.py`, `apps/subscriptions_api/registration_views.py`,
`apps/subscriptions_api/tests_whatsapp.py`, `apps/subscriptions_api/views.py`,
`apps/support_api/views.py`, `apps/tenants_api/admin_views.py`,
`apps/tenants_api/views.py`, `backend/settings.py`, `backend/test_settings.py`,
`ops/monitoring/health_views.py` y este documento.

## 10. Pruebas ejecutadas

Comando base:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -q 2>&1 | Select-Object -Last 40
```

- Antes: `523 passed, 4 skipped, 2 xfailed, 21 warnings in 53.14s`.
- Después: **`540 passed, 4 skipped, 2 xfailed, 21 warnings in 50.13s`**.
- Nuevas: 17 pruebas en `apps/core/test_security_hardening.py`, todas verdes.
- `python manage.py makemigrations --check --dry-run --skip-checks --settings=backend.test_settings`:
  **`No changes detected`**.
- `git diff --check`: sin errores.

Se detectó que `pytest.ini` (`python_files = tests.py test_*.py *_tests.py`) **no
recoge** archivos `tests_*.py`. Al ejecutar explícitamente ese conjunto se
obtuvieron 23 fallos; el mismo conjunto sobre `HEAD` en worktree aislado produce
los mismos 23 fallos. Por tanto no son regresiones, pero sí un hueco de cobertura
**MEDIO** que requiere decisión separada: corregir esos tests o ampliar el patrón
de recolección en un cambio propio.

## 11. Compatibilidad y seguridad operativa

- No se cambiaron firmas de tools, rutas, campos de respuesta ni modelos de
  negocio. Las propiedades de cache de PayPal se guardan aparte.
- No se ejecutaron migraciones, no se modificaron datos reales, secretos ni
  variables de producción.
- No se desplegó nada y no se hicieron push ni merge.
- La seguridad del webhook depende de que `whatsapp_connect` haya generado un
  secreto. Instancias creadas antes de este cambio con
  `whatsapp_webhook_secret=''` rechazarán eventos hasta reconectarse o hasta que
  se configure el secreto manualmente: es fail-closed deliberado.
- `REDIS_CACHE_TIMEOUT` es nueva variable opcional; no contiene secretos.

## 12. Decisión pendiente y autorización

Se necesita autorización expresa para:

1. Activar RLS con el plan restringido de la sección 6 (diseño, staging y
   rollback). **No se ha activado nada.**
2. Elegir fail-closed estricto frente a limitador local distribuido durante
   caída de Redis.
3. Decidir si se corrigen o se integran los `tests_*.py` no recogidos.
4. Autorizar commit, push y merge de esta rama.

Hasta entonces el cambio permanece aislado en
`security/hardening-cinco-trampas` con el working tree modificado.
