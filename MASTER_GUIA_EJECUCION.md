# ============================================================
#  AURON SUITE — GUÍA DE EJECUCIÓN DE FIXES
#  Orden estricto. No saltarse pasos. Cada fix tiene prerrequisitos.
# ============================================================

## FASE 0 — ANTES DE EMPEZAR (10 minutos)

```bash
# 1. Crear rama de seguridad
git checkout -b fix/security-critical-rbac

# 2. Snapshot de base de datos actual
python manage.py dumpdata > backup_pre_fixes_$(date +%Y%m%d).json

# 3. Ejecutar tests actuales para tener baseline
python -m pytest --tb=short -q 2>&1 | tee test_baseline.txt
```

---

## DÍA 1 — Blockers financieros y de seguridad (4–6 horas)

### FIX_5 — Stripe publishable key fuera del bundle ⏱️ 1h
```
Archivo: frontend-app/src/environments/environment.prod.ts
Archivo: frontend-app/src/environments/environment.ts
Archivo: frontend-app/env-config.sh
→ Seguir instrucciones de FIX_5_stripe_key_runtime_only.sh
→ Verificar: grep -r "pk_test_\|pk_live_" dist/ → debe estar vacío
```

### FIX_13 — Stripe LIVE activation ⏱️ 1h
```
→ Obtener sk_live_ y pk_live_ de Stripe Dashboard
→ Actualizar en Render: STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, STRIPE_WEBHOOK_SECRET
→ Aplicar cambio en settings.py (bloquear arranque con sk_test_ en producción)
→ Ejecutar scripts/verify_stripe_live.py en producción
→ Hacer UN cobro real de $1 y verificarlo
```

### FIX_1 — Stripe customer idempotente ⏱️ 30min
```
Archivo: apps/billing_api/stripe_service.py
→ Reemplazar create_customer() con get_or_create_customer()
→ El modelo User ya tiene stripe_customer_id — solo faltaba usarlo
→ Test: crear dos suscripciones para el mismo user → solo 1 customer en Stripe
```

---

## DÍA 2 — RBAC crítico (6–8 horas)

### PRERREQUISITO: Ejecutar script de asignación de permisos
```bash
# Asignar permisos explícitos a roles existentes ANTES de eliminar el fallback implícito
python manage.py shell < scripts/assign_default_role_permissions.py
# → Verificar output: "Total asignados: N" debe ser > 0
```

### FIX_7 — Eliminar ROLE_IMPLICIT_PERMISSIONS bypass ⏱️ 2h
```
→ Ejecutar FIX_7b script de asignación de permisos (obligatorio primero)
→ Aplicar FIX_10 (reemplaza tenant_permissions.py completo)
→ Correr tests: python -m pytest apps/ -k "permission or rbac or tenant" -q
→ Verificar: cajera no puede acceder a /api/reports/kpi-dashboard/
```

### FIX_10 — TenantPermissionByAction deny-by-default ⏱️ 30min
```
Archivo: apps/core/tenant_permissions.py
→ Reemplazar archivo completo con FIX_10
→ CRÍTICO: Ejecutar FIX_7b ANTES de este paso
```

### FIX_3 — Analytics y realtime views RBAC ⏱️ 2h
```
Archivo: apps/reports_api/analytics_views.py → reemplazar con FIX_3 (APIView classes)
Archivo: apps/reports_api/realtime_views.py  → reemplazar con FIX_3b (APIView classes)
Archivo: apps/reports_api/urls.py            → actualizar rutas a .as_view()
```

### FIX_4 — Payroll permission_map separado ⏱️ 1h
```
Archivo: apps/employees_api/earnings_views.py
→ Aplicar nuevo permission_map del FIX_4
→ Crear migración de permisos (FIX_4b)
→ python manage.py makemigrations employees_api --name add_payroll_permissions
→ python manage.py migrate
```

### FIX_11 — Settings y Barbershop RBAC ⏱️ 1h
```
Archivo: apps/settings_api/views.py
Archivo: apps/settings_api/barbershop_views.py
→ Aplicar permission_map de FIX_11
```

---

## DÍA 3 — Operaciones y notificaciones (3–4 horas)

### FIX_2 — Trial notifications reales ⏱️ 1.5h
```
Archivo: apps/tenants_api/middleware.py     → reemplazar send_trial_notification()
Archivo: apps/subscriptions_api/tasks.py    → agregar send_trial_warning_email task
→ Verificar: python manage.py shell -c "
    from apps.subscriptions_api.tasks import send_trial_warning_email
    # Test con tenant real
    send_trial_warning_email.delay(tenant_id=1, days_left=3)
  "
→ Verificar que el email llega
```

### FIX_8 — Support email desde settings ⏱️ 15min
```
Archivo: apps/tenants_api/middleware.py
→ Reemplazar 'support@barbershop.com' hardcodeado
→ Agregar SUPPORT_EMAIL al .env y .env.example
```

### FIX_6 — CI/CD deploy real ⏱️ 1h
```
Archivo: .github/workflows/ci-cd.yml
→ Agregar secrets: RENDER_DEPLOY_HOOK_URL, PRODUCTION_API_URL
→ Reemplazar job "deploy" vacío con FIX_6
→ Crear health check view si no existe (FIX_6c)
→ Verificar: hacer un push a master y confirmar que el pipeline despliega y
  el smoke test pasa
```

### FIX_9 — Staging environment ⏱️ 1h
```
→ Seguir instrucciones de FIX_9_staging_environment.sh
→ CRÍTICO: environment.ts (dev) nunca debe volver a apuntar a producción
```

---

## VERIFICACIÓN FINAL — GO-LIVE (45 minutos)

```bash
# Ejecutar el checklist completo
bash FIX_12_go_live_checklist_commands.sh 2>&1 | tee go_live_evidence_$(date +%Y%m%d).txt

# Criterios de aprobación:
# ✅ DEBUG=False
# ✅ Stripe LIVE activo
# ✅ Health check HTTP 200
# ✅ Celery async (no eager)
# ✅ Sentry recibió el error de prueba
# ✅ Tests RBAC pasan
# ✅ Backup reciente verificado
```

---

## RESUMEN DE ARCHIVOS A MODIFICAR

| Archivo | Fix | Tipo |
|---------|-----|------|
| apps/core/tenant_permissions.py | FIX_10 | Reemplazar completo |
| apps/billing_api/stripe_service.py | FIX_1 | Reemplazar completo |
| apps/tenants_api/middleware.py | FIX_2 + FIX_8 | Modificar métodos |
| apps/subscriptions_api/tasks.py | FIX_2 | Agregar task |
| apps/reports_api/analytics_views.py | FIX_3 | Reemplazar completo |
| apps/reports_api/realtime_views.py | FIX_3 | Reemplazar completo |
| apps/reports_api/urls.py | FIX_3 | Actualizar rutas |
| apps/employees_api/earnings_views.py | FIX_4 | Modificar permission_map |
| apps/employees_api/migrations/ | FIX_4b | Crear migración |
| frontend-app/src/environments/ | FIX_5 + FIX_9 | Reemplazar archivos |
| frontend-app/env-config.sh | FIX_5 | Modificar |
| .github/workflows/ci-cd.yml | FIX_6 | Agregar job deploy |
| scripts/assign_default_role_permissions.py | FIX_7b | Crear script |
| apps/settings_api/views.py | FIX_11 | Modificar clase |
| apps/settings_api/barbershop_views.py | FIX_11 | Agregar permission_map |
| backend/settings.py | FIX_13 | Modificar bloque Stripe |

## TIEMPO TOTAL ESTIMADO: 3 días de trabajo enfocado
