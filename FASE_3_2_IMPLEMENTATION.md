# FASE 3.2: SOFT DELETES Y AUDIT TRAIL - PLAN DE IMPLEMENTACIÓN

## CHECKLIST DE IMPLEMENTACIÓN

### 1. PREPARACIÓN (ORDEN CRÍTICO)
- [ ] Crear migraciones Django para agregar campos soft delete a modelos seleccionados
- [ ] Ejecutar: `python manage.py makemigrations`
- [ ] Ejecutar: `python manage.py migrate`
- [ ] Ejecutar: `python manage.py migrate_soft_deletes --dry-run` (verificar)
- [ ] Ejecutar: `python manage.py migrate_soft_deletes` (aplicar)

### 2. MODELOS A MIGRAR (SELECTIVO)
```python
# ✅ MIGRAR A BusinessModel:
apps/clients_api/models.py:
  - Client (hereda de BusinessModel)

apps/employees_api/models.py:
  - Employee (hereda de BusinessModel)

apps/pos_api/models.py:
  - Sale (hereda de BusinessModel)
  - SaleItem (hereda de BusinessModel)

apps/payroll_api/models.py:
  - PayrollCalculation (hereda de BusinessModel)
  - PayrollPayment (hereda de BusinessModel)

# ❌ NO MIGRAR:
- auth_api/models.py (User, Token)
- tenants_api/models.py (Tenant - crítico para RLS)
- audit_api/models.py (BusinessAuditLog)
- settings_api/models.py
```

### 3. VIEWSETS A ACTUALIZAR
```python
# Agregar mixins a ViewSets existentes:
from apps.utils.mixins import SoftDeleteMixin, AuditableMixin

class ClientViewSet(SoftDeleteMixin, AuditableMixin, ModelViewSet):
    pass

class EmployeeViewSet(SoftDeleteMixin, AuditableMixin, ModelViewSet):
    pass

class SaleViewSet(SoftDeleteMixin, AuditableMixin, ModelViewSet):
    pass
```

### 4. TESTS CRÍTICOS
- [ ] `python manage.py test apps.utils.tests.test_soft_delete_audit`
- [ ] Verificar que RLS sigue funcionando
- [ ] Verificar que APIs mantienen contratos HTTP
- [ ] Verificar que auditoría se registra correctamente

### 5. COMANDOS DE VERIFICACIÓN
```bash
# Verificar soft deletes
python manage.py shell -c "
from apps.clients_api.models import Client
print('Clientes activos:', Client.objects.count())
print('Clientes totales:', Client.all_objects.count())
"

# Verificar auditoría
python manage.py shell -c "
from apps.audit_api.audit_models import BusinessAuditLog
print('Registros de auditoría:', BusinessAuditLog.objects.count())
"

# Verificar mypy sigue funcionando
mypy apps/utils/models.py
mypy apps/audit_api/audit_models.py
```

## CRITERIOS DE FINALIZACIÓN FASE 3.2

### ✅ SEÑALES DE ÉXITO:
- [ ] Modelos críticos usan soft delete sin romper funcionalidad
- [ ] Manager por defecto excluye registros soft-deleted
- [ ] APIs mantienen contratos HTTP (DELETE -> 204)
- [ ] Nuevos endpoints /restore/ y /deleted/ funcionan
- [ ] Auditoría se registra automáticamente en create/update/delete
- [ ] RLS sigue funcionando con soft delete
- [ ] Tests pasan sin errores
- [ ] Mypy no reporta errores en módulos nuevos

### 📊 MÉTRICAS A OBSERVAR:
```bash
# Cobertura de auditoría
SELECT action, COUNT(*) FROM business_audit_log 
GROUP BY action ORDER BY COUNT(*) DESC;

# Registros soft-deleted por modelo
SELECT content_type_id, COUNT(*) FROM business_audit_log 
WHERE action = 'soft_delete' GROUP BY content_type_id;

# Performance de queries (no debe degradarse)
EXPLAIN ANALYZE SELECT * FROM clients_api_client WHERE is_deleted = false;
```

### 🚫 QUÉ NO HACER AÚN:
- NO implementar hard delete automático
- NO agregar retención de datos por tiempo
- NO implementar compliance GDPR completo
- NO migrar TODOS los modelos a soft delete
- NO usar signals globales para auditoría

### 🎯 BENEFICIOS INMEDIATOS:
1. **Trazabilidad**: Registro completo de acciones críticas
2. **Recuperación**: Posibilidad de restaurar datos eliminados
3. **Compliance**: Base para auditorías futuras
4. **Debugging**: Visibilidad de cambios en producción
5. **Seguridad**: Prevención de pérdida accidental de datos

## SIGUIENTE FASE (3.3):
- Optimización de queries con soft delete
- Dashboard de auditoría para administradores
- Políticas de retención de datos
- Integración con compliance legal