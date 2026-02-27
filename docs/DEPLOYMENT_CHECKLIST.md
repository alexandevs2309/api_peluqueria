# CHECKLIST DE DESPLIEGUE - ENDURECIMIENTO MULTI-TENANT

## PRE-DESPLIEGUE

### 1. Backup Completo
```bash
# Backup de base de datos
pg_dump -U postgres -d barberia_db > backup_pre_hardening_$(date +%Y%m%d).sql

# Backup de código
git tag -a v1.0-pre-hardening -m "Backup antes de endurecimiento"
git push origin v1.0-pre-hardening
```

### 2. Validar Tests Existentes
```bash
cd api_peluqueria
python manage.py test --keepdb
```
✅ Todos los tests deben pasar ANTES de continuar.

---

## DESPLIEGUE

### PASO 1: Aplicar Admin Panel (SIN DOWNTIME)

```bash
# 1. Copiar base_admin.py
cp apps/tenants_api/base_admin.py /ruta/produccion/apps/tenants_api/

# 2. Actualizar admin.py de cada app
# - employees_api/admin.py
# - tenants_api/admin.py

# 3. Reiniciar Django (admin panel no afecta API)
systemctl restart gunicorn
```

**Validación:**
```bash
# Login como SuperAdmin
curl -X POST https://api.tuapp.com/auth/login/ \
  -d '{"email":"superadmin@system.com","password":"xxx"}'

# Verificar acceso a admin
curl https://api.tuapp.com/admin/employees_api/employee/ \
  -H "Authorization: Bearer <token>"
```

**Rollback si falla:**
```bash
git revert HEAD
systemctl restart gunicorn
```

---

### PASO 2: Agregar Tenant a Appointment (REQUIERE DOWNTIME)

⚠️ **DOWNTIME ESTIMADO: 2-5 minutos**

```bash
# 1. Activar modo mantenimiento
touch /var/www/maintenance.flag

# 2. Aplicar migración
python manage.py migrate appointments_api 0005_add_tenant_field

# Salida esperada:
# Running migration 0005_add_tenant_field...
# ✅ Backfilled tenant for XXX appointments
# Migration complete.

# 3. Verificar integridad
python manage.py shell
>>> from apps.appointments_api.models import Appointment
>>> Appointment.objects.filter(tenant__isnull=True).count()
0  # Debe ser 0

# 4. Actualizar código
# - models.py
# - views.py

# 5. Reiniciar
systemctl restart gunicorn

# 6. Desactivar mantenimiento
rm /var/www/maintenance.flag
```

**Validación:**
```bash
# Crear appointment como Tenant A
curl -X POST https://api.tuapp.com/api/appointments/ \
  -H "Authorization: Bearer <token_tenant_a>" \
  -d '{
    "client": 1,
    "stylist": 2,
    "date_time": "2024-01-15T10:00:00Z"
  }'

# Verificar que tiene tenant
curl https://api.tuapp.com/api/appointments/<id>/ \
  -H "Authorization: Bearer <token_tenant_a>"
# Debe retornar appointment con tenant_id
```

**Rollback si falla:**
```bash
# Revertir migración
python manage.py migrate appointments_api 0004_initial

# Revertir código
git revert HEAD~2..HEAD

# Reiniciar
systemctl restart gunicorn
```

---

### PASO 3: Ejecutar Tests de Seguridad

```bash
# Ejecutar tests IDOR
python manage.py test apps.tenants_api.tests_security

# Salida esperada:
# test_idor_employee_retrieve_cross_tenant ... ok
# test_idor_employee_update_cross_tenant ... ok
# test_idor_employee_delete_cross_tenant ... ok
# test_idor_client_retrieve_cross_tenant ... ok
# test_idor_appointment_cross_tenant ... ok
# test_idor_sale_cross_tenant ... ok
# test_superadmin_can_access_all_tenants ... ok
# ----------------------------------------------------------------------
# Ran 12 tests in 2.345s
# OK
```

✅ Todos los tests deben pasar.

---

## POST-DESPLIEGUE

### 1. Monitoreo (Primeras 24 horas)

```bash
# Monitorear logs
tail -f /var/log/gunicorn/error.log | grep -i "tenant\|permission\|404"

# Monitorear métricas
curl https://api.tuapp.com/api/utils/health-check/
```

**Alertas esperadas:** NINGUNA

**Errores a vigilar:**
- ❌ `AttributeError: 'Appointment' object has no attribute 'tenant'`
- ❌ `IntegrityError: null value in column "tenant_id"`
- ❌ Aumento de 404 en endpoints de appointments

### 2. Validación Funcional

**Test Manual - Tenant A:**
```bash
# Login
TOKEN_A=$(curl -X POST https://api.tuapp.com/auth/login/ \
  -d '{"email":"admin@tenant-a.com","password":"xxx"}' | jq -r '.access')

# Listar employees (solo debe ver los suyos)
curl https://api.tuapp.com/api/employees/ \
  -H "Authorization: Bearer $TOKEN_A"

# Intentar acceder a employee de Tenant B (debe fallar)
curl https://api.tuapp.com/api/employees/999/ \
  -H "Authorization: Bearer $TOKEN_A"
# Esperado: 404
```

**Test Manual - SuperAdmin:**
```bash
TOKEN_SUPER=$(curl -X POST https://api.tuapp.com/auth/login/ \
  -d '{"email":"superadmin@system.com","password":"xxx"}' | jq -r '.access')

# Debe ver todos los tenants
curl https://api.tuapp.com/api/employees/ \
  -H "Authorization: Bearer $TOKEN_SUPER"
```

### 3. Verificar Admin Panel

```bash
# Login como Client-Admin de Tenant A
# Ir a: https://api.tuapp.com/admin/employees_api/employee/
# Verificar que SOLO ve employees de Tenant A

# Login como SuperAdmin
# Ir a: https://api.tuapp.com/admin/employees_api/employee/
# Verificar que ve TODOS los employees
```

---

## EVALUACIÓN DE RIESGO POST-IMPLEMENTACIÓN

### Riesgos Introducidos: NINGUNO ✅

**Razones:**
1. ✅ Admin panel: Solo afecta a usuarios con `is_staff=True`
2. ✅ Appointment.tenant: Migración con backfill automático
3. ✅ Tests: No modifican comportamiento, solo validan
4. ✅ Código defensivo: Mantiene filtrado existente

### Riesgos Mitigados: ALTO ✅

**Antes:**
- 🔴 Admin panel sin filtrado (escalada vertical)
- 🟡 Appointment sin tenant directo (bypass por NULL)
- 🟡 Sin tests de seguridad

**Después:**
- 🟢 Admin panel filtrado por tenant
- 🟢 Appointment con tenant directo
- 🟢 Tests automáticos de IDOR

---

## ROLLBACK COMPLETO

Si algo sale mal:

```bash
# 1. Restaurar base de datos
psql -U postgres -d barberia_db < backup_pre_hardening_YYYYMMDD.sql

# 2. Revertir código
git reset --hard v1.0-pre-hardening

# 3. Reiniciar servicios
systemctl restart gunicorn
systemctl restart celery

# 4. Verificar
curl https://api.tuapp.com/api/utils/health-check/
```

---

## CLASIFICACIÓN FINAL

🟢 **APLICACIÓN ENDURECIDA SIN REGRESIÓN**

**Justificación:**
- ✅ No rompe funcionalidad existente
- ✅ Migración segura con backfill
- ✅ Tests validan comportamiento
- ✅ Rollback simple y documentado
- ✅ Defensa en profundidad aplicada
- ✅ Downtime mínimo (2-5 min)

**Próximos pasos (opcional):**
- Implementar RLS en PostgreSQL (defensa adicional)
- Agregar más tests de seguridad
- Auditar otros modelos sin tenant directo
