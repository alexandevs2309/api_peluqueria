# AUDITORÍA COMPLETA DE SEGURIDAD RBAC MULTI-TENANT

**Fecha**: 2024  
**Sistema**: Django Multi-Tenant SaaS - Barbería  
**Arquitectura**: TenantPermissionByAction + UserRole + Role.permissions  
**Estado**: VULNERABLE POR OMISIONES (13% cobertura)

---

## RESUMEN EJECUTIVO

### Clasificación de Seguridad
**VULNERABLE POR OMISIONES** - Solo 2 de 15+ ViewSets protegidos (13% cobertura)

### Hallazgos Críticos
1. **87% de endpoints sin protección RBAC** - Usan solo IsAuthenticated
2. **15+ @action sin permission_map** - Acciones críticas expuestas
3. **Reportes financieros sin validación** - Cajera puede ver datos administrativos
4. **Inventario sin control de rol** - adjust_stock sin restricción
5. **Servicios sin protección** - set_employee_price accesible a todos

### Impacto Operacional
- **Cajera** tiene acceso de facto a funciones administrativas
- **Estilista** puede modificar precios y configuraciones
- **Datos financieros** expuestos a roles no autorizados
- **Integridad de datos** comprometida (ajustes de stock, precios)

---

## FASE 1 — AUDITORÍA DETALLADA

### 1.1 ViewSets con IsAuthenticated SOLAMENTE

| ViewSet | Archivo | Línea | Acciones | Criticidad |
|---------|---------|-------|----------|------------|
| **AppointmentViewSet** | appointments_api/views.py | ~15 | list, create, update, destroy, availability, cancel, complete, today | ALTA |
| **ClientViewSet** | clients_api/views.py | ~10 | list, create, update, destroy | MEDIA |
| **ServiceViewSet** | services_api/views.py | ~12 | list, create, update, destroy, set_employee_price, assign_employees | CRÍTICA |
| **ServiceCategoryViewSet** | services_api/views.py | ~80 | list, create, update, destroy | BAJA |
| **ProductViewSet** | inventory_api/views.py | ~15 | list, create, update, destroy, adjust_stock | CRÍTICA |
| **AuditLogViewSet** | audit_api/views.py | ~10 | list, retrieve, summary, actions, sources | MEDIA |
| **InvoiceViewSet** | billing_api/views.py | ~15 | list, create, mark_as_paid, pay | ALTA |
| **PaymentAttemptViewSet** | billing_api/views.py | ~120 | list, retrieve, create, update | MEDIA |
| **NotificationListCreateView** | notifications_api/views.py | ~8 | list, create | BAJA |
| **NotificationDetailView** | notifications_api/views.py | ~20 | retrieve, update, destroy | BAJA |
| **PaymentViewSet** | payments_api/views.py | ~15 | list, create, create_subscription_payment, confirm_payment | ALTA |
| **PayrollViewSet** | employees_api/earnings_views.py | ~10 | list_periods, register_payment, recalculate_period, approve_period | CRÍTICA |
| **SystemSettingsRetrieveUpdateView** | settings_api/views.py | ~10 | retrieve, update | MEDIA |
| **BarbershopSettingsViewSet** | settings_api/barbershop_views.py | ~15 | list, create, upload_logo, admin_settings | MEDIA |

**Total: 14 ViewSets vulnerables**

### 1.2 APIViews sin Protección RBAC

| APIView | Archivo | Método | Criticidad |
|---------|---------|--------|------------|
| **AdminReportsView** | reports_api/views.py | GET | CRÍTICA |
| **EmployeeReportView** | reports_api/views.py | GET | CRÍTICA |
| **SalesReportView** | reports_api/views.py | GET | CRÍTICA |
| **KPIDashboardView** | reports_api/views.py | GET | CRÍTICA |
| **BillingStatsView** | billing_api/views.py | GET | ALTA |
| **SaasMetricsView** | settings_api/admin_views.py | GET | CRÍTICA |
| **SystemMonitorView** | settings_api/admin_views.py | GET | ALTA |
| **MyActiveSubscriptionView** | subscriptions_api/views.py | GET | BAJA |
| **MyEntitlementsView** | subscriptions_api/views.py | GET | BAJA |
| **RenewSubscriptionView** | subscriptions_api/views.py | GET, POST | MEDIA |

**Total: 10 APIViews vulnerables**

### 1.3 @action Sin permission_map

| ViewSet | @action | Criticidad | Razón |
|---------|---------|------------|-------|
| AppointmentViewSet | availability | MEDIA | Expone disponibilidad de empleados |
| AppointmentViewSet | cancel | ALTA | Permite cancelar citas sin validación |
| AppointmentViewSet | complete | ALTA | Marca citas como completadas |
| AppointmentViewSet | today | BAJA | Lista citas del día |
| ProductViewSet | adjust_stock | CRÍTICA | Modifica inventario sin control |
| ServiceViewSet | set_employee_price | CRÍTICA | Cambia precios sin autorización |
| ServiceViewSet | assign_employees | ALTA | Asigna empleados a servicios |
| InvoiceViewSet | mark_as_paid | CRÍTICA | Marca facturas como pagadas |
| InvoiceViewSet | pay | CRÍTICA | Procesa pagos |
| PayrollViewSet | register_payment | CRÍTICA | Registra pagos de nómina |
| PayrollViewSet | approve_period | CRÍTICA | Aprueba períodos de pago |
| PayrollViewSet | recalculate_period | ALTA | Recalcula montos |
| TenantViewSet | activate | ALTA | Activa tenants |
| TenantViewSet | deactivate | ALTA | Desactiva tenants |
| TenantViewSet | bulk_delete | CRÍTICA | Elimina múltiples tenants |

**Total: 15+ acciones críticas sin mapeo**

### 1.4 Validación de TenantPermissionByAction

**Archivo**: `apps/core/tenant_permissions.py`

✅ **CORRECTO**:
- Filtrado por `request.tenant` (línea 48-50)
- SuperAdmin bypass ANTES de validación tenant (línea 38-40)
- Validación formato `app_label.codename` (línea 56-57)
- Consulta UserRole con prefetch (línea 59-62)

❌ **INCORRECTO**:
```python
# Línea 100-102
if not action or action not in permission_map:
    # Sin mapeo, permitir solo lectura
    return request.method in ['GET', 'HEAD', 'OPTIONS']
```

**PROBLEMA**: Fallback inseguro - acciones no mapeadas permiten GET por defecto.

**SOLUCIÓN**: Cambiar a `return False` (deny by default).

### 1.5 Reportes y Dashboards Financieros

**CRÍTICO**: Todos los endpoints de reports_api usan solo IsAuthenticated

| Endpoint | Datos Expuestos | Acceso Actual |
|----------|-----------------|---------------|
| /api/reports/admin/ | Métricas administrativas completas | Todos los usuarios autenticados |
| /api/reports/employee/ | Nómina y comisiones de empleados | Todos los usuarios autenticados |
| /api/reports/sales/ | Ventas detalladas con montos | Todos los usuarios autenticados |
| /api/reports/kpi/ | KPIs financieros del negocio | Todos los usuarios autenticados |
| /api/reports/analytics/advanced/ | Analytics avanzados | Todos los usuarios autenticados |
| /api/reports/analytics/business-intelligence/ | Business Intelligence | Todos los usuarios autenticados |
| /api/reports/realtime/metrics/ | Métricas en tiempo real | Todos los usuarios autenticados |

**IMPACTO**: Cajera puede ver:
- Salarios de todos los empleados
- Comisiones y ganancias
- Métricas de rentabilidad
- Proyecciones financieras
- KPIs administrativos

### 1.6 Validaciones Ad-Hoc en Métodos

**PATRÓN DETECTADO**: Validaciones dentro de métodos en lugar de permission_classes

```python
# billing_api/views.py - InvoiceViewSet
def get_queryset(self):
    if hasattr(self.request.user, 'roles') and self.request.user.is_superuser:
        return Invoice.objects.all()
    # ...
```

```python
# employees_api/earnings_views.py - PayrollViewSet
def _require_admin_role(self, request):
    if not request.user.roles.filter(name__in=['Super-Admin', 'Client-Admin']).exists():
        raise PermissionDenied("No autorizado")
```

```python
# notifications_api/views.py - NotificationListCreateView
def get_queryset(self):
    if user.is_superuser or user.roles.filter(name__in=['Super-Admin', 'Client-Admin']).exists():
        return InAppNotification.objects.filter(recipient__tenant=user.tenant)
```

**PROBLEMA**: 
- Lógica duplicada en múltiples archivos
- No usa infraestructura RBAC existente
- Difícil de mantener y auditar
- Inconsistente con TenantPermissionByAction

---

## FASE 2 — PLAN CORRECTIVO PROFESIONAL

### NIVEL 1 — CORRECCIÓN INMEDIATA (Máximo Impacto)

**Prioridad**: CRÍTICA  
**Tiempo estimado**: 2-4 horas  
**Impacto**: Protege 80% de vulnerabilidades críticas

#### 1.1 Corregir Fallback Inseguro en TenantPermissionByAction

**Archivo**: `apps/core/tenant_permissions.py`

**Cambio**:
```python
# LÍNEA 100-102 - REEMPLAZAR
if not action or action not in permission_map:
    return False  # DENY BY DEFAULT
```

#### 1.2 Proteger Reportes Financieros

**Archivo**: `apps/reports_api/views.py`

**Cambios**:
1. Importar TenantPermissionByAction
2. Agregar permission_classes a TODOS los ViewSets/APIViews
3. Definir permission_map para cada endpoint

**Archivos a modificar**:
- `reports_api/views.py` (AdminReportsView, EmployeeReportView, SalesReportView, KPIDashboardView)
- `reports_api/analytics_views.py` (advanced_analytics, business_intelligence, predictive_analytics)
- `reports_api/realtime_views.py` (realtime_metrics, live_dashboard_data, performance_alerts)

#### 1.3 Proteger Acciones Críticas de Inventario

**Archivo**: `apps/inventory_api/views.py`

**Cambios**:
1. Reemplazar `IsAuthenticated` con `TenantPermissionByAction`
2. Agregar permission_map con adjust_stock

#### 1.4 Proteger Servicios y Precios

**Archivo**: `apps/services_api/views.py`

**Cambios**:
1. Reemplazar `IsAuthenticated` con `TenantPermissionByAction`
2. Agregar permission_map con set_employee_price, assign_employees

#### 1.5 Proteger Nómina

**Archivo**: `apps/employees_api/earnings_views.py`

**Cambios**:
1. Reemplazar validación ad-hoc `_require_admin_role` con TenantPermissionByAction
2. Agregar permission_map para register_payment, approve_period, recalculate_period

---

### NIVEL 2 — COBERTURA COMPLETA

**Prioridad**: ALTA  
**Tiempo estimado**: 4-6 horas  
**Impacto**: Protege 100% de endpoints

#### 2.1 ViewSets a Migrar

| ViewSet | Archivo | permission_map Requerido |
|---------|---------|--------------------------|
| AppointmentViewSet | appointments_api/views.py | list: view_appointment, create: add_appointment, update: change_appointment, destroy: delete_appointment, cancel: change_appointment, complete: change_appointment |
| ClientViewSet | clients_api/views.py | list: view_client, create: add_client, update: change_client, destroy: delete_client |
| ServiceCategoryViewSet | services_api/views.py | list: view_servicecategory, create: add_servicecategory, update: change_servicecategory, destroy: delete_servicecategory |
| AuditLogViewSet | audit_api/views.py | list: view_auditlog, retrieve: view_auditlog |
| InvoiceViewSet | billing_api/views.py | list: view_invoice, create: add_invoice, mark_as_paid: change_invoice |
| PaymentAttemptViewSet | billing_api/views.py | list: view_paymentattempt, retrieve: view_paymentattempt |
| NotificationListCreateView | notifications_api/views.py | list: view_notification, create: add_notification |
| PaymentViewSet | payments_api/views.py | list: view_payment, create: add_payment |
| SystemSettingsRetrieveUpdateView | settings_api/views.py | retrieve: view_systemsettings, update: change_systemsettings |
| BarbershopSettingsViewSet | settings_api/barbershop_views.py | list: view_barbershopsettings, create: change_barbershopsettings |

#### 2.2 Permisos Necesarios por Modelo

**Crear migraciones para custom permissions**:

```python
# appointments_api/models.py - Meta.permissions
('cancel_appointment', 'Can cancel appointments'),
('complete_appointment', 'Can mark appointments as complete'),

# inventory_api/models.py - Meta.permissions
('adjust_stock', 'Can adjust product stock'),

# services_api/models.py - Meta.permissions
('set_employee_price', 'Can set employee-specific prices'),
('assign_employees', 'Can assign employees to services'),

# billing_api/models.py - Meta.permissions
('mark_invoice_paid', 'Can mark invoices as paid'),
('process_payment', 'Can process payments'),

# reports_api - Crear modelo ReportPermission
('view_financial_reports', 'Can view financial reports'),
('view_employee_reports', 'Can view employee reports'),
('view_sales_reports', 'Can view sales reports'),
('view_kpi_dashboard', 'Can view KPI dashboard'),
('view_advanced_analytics', 'Can view advanced analytics'),
```

#### 2.3 Mapeo Recomendado por Módulo

**appointments_api**:
```python
permission_map = {
    'list': 'appointments_api.view_appointment',
    'retrieve': 'appointments_api.view_appointment',
    'create': 'appointments_api.add_appointment',
    'update': 'appointments_api.change_appointment',
    'partial_update': 'appointments_api.change_appointment',
    'destroy': 'appointments_api.delete_appointment',
    'availability': 'appointments_api.view_appointment',
    'cancel': 'appointments_api.cancel_appointment',
    'complete': 'appointments_api.complete_appointment',
    'today': 'appointments_api.view_appointment',
}
```

**inventory_api**:
```python
permission_map = {
    'list': 'inventory_api.view_product',
    'retrieve': 'inventory_api.view_product',
    'create': 'inventory_api.add_product',
    'update': 'inventory_api.change_product',
    'partial_update': 'inventory_api.change_product',
    'destroy': 'inventory_api.delete_product',
    'adjust_stock': 'inventory_api.adjust_stock',
}
```

**services_api**:
```python
permission_map = {
    'list': 'services_api.view_service',
    'retrieve': 'services_api.view_service',
    'create': 'services_api.add_service',
    'update': 'services_api.change_service',
    'partial_update': 'services_api.change_service',
    'destroy': 'services_api.delete_service',
    'set_employee_price': 'services_api.set_employee_price',
    'assign_employees': 'services_api.assign_employees',
}
```

**reports_api** (crear modelo ReportPermission):
```python
permission_map = {
    'get': 'reports_api.view_financial_reports',  # AdminReportsView
}

permission_map = {
    'get': 'reports_api.view_employee_reports',  # EmployeeReportView
}

permission_map = {
    'get': 'reports_api.view_sales_reports',  # SalesReportView
}

permission_map = {
    'get': 'reports_api.view_kpi_dashboard',  # KPIDashboardView
}
```

**billing_api**:
```python
permission_map = {
    'list': 'billing_api.view_invoice',
    'retrieve': 'billing_api.view_invoice',
    'create': 'billing_api.add_invoice',
    'mark_as_paid': 'billing_api.mark_invoice_paid',
    'pay': 'billing_api.process_payment',
}
```

**employees_api (earnings)**:
```python
permission_map = {
    'list_periods': 'employees_api.view_employee_payroll',
    'register_payment': 'employees_api.manage_employee_loans',  # Ya existe
    'approve_period': 'employees_api.view_employee_payroll',
    'recalculate_period': 'employees_api.view_employee_payroll',
}
```

---

### NIVEL 3 — BLINDAJE FINAL

**Prioridad**: MEDIA  
**Tiempo estimado**: 2-3 horas  
**Impacto**: Elimina deuda técnica y estandariza

#### 3.1 Eliminar Validaciones Ad-Hoc

**Archivos a modificar**:
1. `billing_api/views.py` - Eliminar validación `is_superuser` en get_queryset
2. `employees_api/earnings_views.py` - Eliminar método `_require_admin_role`
3. `notifications_api/views.py` - Eliminar validación `user.roles.filter` en get_queryset
4. `tenants_api/views.py` - Eliminar validación `is_superuser` en get_queryset
5. `tenants_api/admin_views.py` - Eliminar validación `roles.filter` en get_queryset

**Reemplazar con**: TenantPermissionByAction en permission_classes

#### 3.2 Estandarizar Patrón en Todo el Proyecto

**Patrón estándar**:
```python
from apps.core.tenant_permissions import TenantPermissionByAction

class MyViewSet(viewsets.ModelViewSet):
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'app.view_model',
        'retrieve': 'app.view_model',
        'create': 'app.add_model',
        'update': 'app.change_model',
        'partial_update': 'app.change_model',
        'destroy': 'app.delete_model',
        # Custom actions
        'custom_action': 'app.custom_permission',
    }
```

#### 3.3 Actualizar scripts/setup_roles_permissions.py

**Agregar permisos a roles**:

```python
# Client-Admin: TODOS los permisos
admin_permissions = [
    # ... permisos existentes ...
    'appointments_api.cancel_appointment',
    'appointments_api.complete_appointment',
    'inventory_api.adjust_stock',
    'services_api.set_employee_price',
    'services_api.assign_employees',
    'billing_api.mark_invoice_paid',
    'billing_api.process_payment',
    'reports_api.view_financial_reports',
    'reports_api.view_employee_reports',
    'reports_api.view_sales_reports',
    'reports_api.view_kpi_dashboard',
]

# Manager: Sin delete, sin reportes financieros
manager_permissions = [
    # ... permisos existentes ...
    'appointments_api.cancel_appointment',
    'appointments_api.complete_appointment',
    'inventory_api.adjust_stock',
    'services_api.set_employee_price',
    'reports_api.view_sales_reports',
]

# Cajera: Solo ventas y citas
cajera_permissions = [
    'pos_api.add_sale',
    'pos_api.view_sale',
    'appointments_api.view_appointment',
    'appointments_api.add_appointment',
    'clients_api.view_client',
]

# Estilista: Solo lectura + completar citas
estilista_permissions = [
    'appointments_api.view_appointment',
    'appointments_api.complete_appointment',
    'clients_api.view_client',
    'services_api.view_service',
    'pos_api.view_sale',
]
```

#### 3.4 Checklist de Verificación Final

**Ejecutar antes de declarar sistema seguro**:

- [ ] TenantPermissionByAction usa `return False` para acciones no mapeadas
- [ ] Todos los ViewSets tienen permission_classes = [TenantPermissionByAction]
- [ ] Todos los ViewSets tienen permission_map completo
- [ ] Todas las @action están en permission_map
- [ ] Todos los APIViews tienen permission_classes
- [ ] Cero validaciones ad-hoc de roles en métodos
- [ ] Custom permissions migrados a base de datos
- [ ] Roles actualizados con nuevos permisos
- [ ] Tests de autorización por rol ejecutados
- [ ] Auditoría manual de endpoints críticos

**Script de validación**:
```bash
# Buscar ViewSets sin TenantPermissionByAction
grep -r "permission_classes = \[IsAuthenticated\]" apps/*/views.py

# Buscar @action sin permission_map
grep -r "@action" apps/*/views.py | grep -v "permission_map"

# Buscar validaciones ad-hoc
grep -r "user.roles.filter" apps/*/views.py
grep -r "is_superuser" apps/*/views.py | grep -v "# SuperAdmin"
```

---

## ORDEN RECOMENDADO DE APLICACIÓN

### Semana 1 - CRÍTICO
1. ✅ Corregir fallback TenantPermissionByAction (30 min)
2. ✅ Proteger reports_api completo (2 horas)
3. ✅ Proteger inventory_api.adjust_stock (30 min)
4. ✅ Proteger services_api precios (1 hora)
5. ✅ Proteger earnings_views nómina (1 hora)

**Resultado**: 80% vulnerabilidades críticas resueltas

### Semana 2 - ALTA PRIORIDAD
6. ✅ Migrar AppointmentViewSet (1 hora)
7. ✅ Migrar ClientViewSet (30 min)
8. ✅ Migrar InvoiceViewSet (1 hora)
9. ✅ Migrar PaymentViewSet (1 hora)
10. ✅ Crear custom permissions (1 hora)
11. ✅ Actualizar setup_roles_permissions.py (1 hora)

**Resultado**: 95% cobertura RBAC

### Semana 3 - CONSOLIDACIÓN
12. ✅ Eliminar validaciones ad-hoc (2 horas)
13. ✅ Estandarizar patrón en ViewSets restantes (2 horas)
14. ✅ Tests de autorización (2 horas)
15. ✅ Auditoría manual final (1 hora)

**Resultado**: Sistema 100% protegido

---

## ARCHIVOS A MODIFICAR (Lista Exacta)

### Modificaciones Críticas (Semana 1)
1. `apps/core/tenant_permissions.py` - Línea 100-102
2. `apps/reports_api/views.py` - Agregar TenantPermissionByAction
3. `apps/reports_api/analytics_views.py` - Agregar TenantPermissionByAction
4. `apps/reports_api/realtime_views.py` - Agregar TenantPermissionByAction
5. `apps/inventory_api/views.py` - Reemplazar IsAuthenticated
6. `apps/services_api/views.py` - Reemplazar IsAuthenticated
7. `apps/employees_api/earnings_views.py` - Reemplazar _require_admin_role

### Modificaciones Alta Prioridad (Semana 2)
8. `apps/appointments_api/views.py` - Reemplazar IsAuthenticated
9. `apps/clients_api/views.py` - Reemplazar IsAuthenticated
10. `apps/billing_api/views.py` - Reemplazar IsAuthenticated
11. `apps/payments_api/views.py` - Reemplazar IsAuthenticated
12. `apps/appointments_api/models.py` - Agregar Meta.permissions
13. `apps/inventory_api/models.py` - Agregar Meta.permissions
14. `apps/services_api/models.py` - Agregar Meta.permissions
15. `apps/billing_api/models.py` - Agregar Meta.permissions
16. `apps/reports_api/models.py` - CREAR con Meta.permissions
17. `scripts/setup_roles_permissions.py` - Actualizar permisos

### Modificaciones Consolidación (Semana 3)
18. `apps/billing_api/views.py` - Eliminar validación is_superuser
19. `apps/notifications_api/views.py` - Eliminar validación roles.filter
20. `apps/tenants_api/views.py` - Eliminar validación is_superuser
21. `apps/tenants_api/admin_views.py` - Eliminar validación roles.filter
22. `apps/audit_api/views.py` - Agregar TenantPermissionByAction
23. `apps/settings_api/views.py` - Agregar TenantPermissionByAction
24. `apps/settings_api/barbershop_views.py` - Agregar TenantPermissionByAction

**Total: 24 archivos a modificar**

---

## MÉTRICAS DE ÉXITO

### Antes (Estado Actual)
- ✅ 2 ViewSets protegidos (13%)
- ❌ 14 ViewSets vulnerables (87%)
- ❌ 15+ @action sin mapeo
- ❌ 10 APIViews sin protección
- ❌ Validaciones ad-hoc en 5 archivos

### Después (Estado Objetivo)
- ✅ 16 ViewSets protegidos (100%)
- ✅ 0 ViewSets vulnerables (0%)
- ✅ 0 @action sin mapeo
- ✅ 10 APIViews protegidos (100%)
- ✅ 0 validaciones ad-hoc

### KPIs de Seguridad
- **Cobertura RBAC**: 13% → 100%
- **Endpoints críticos protegidos**: 20% → 100%
- **Acciones sin mapeo**: 15+ → 0
- **Validaciones ad-hoc**: 5 → 0
- **Tiempo de implementación**: 3 semanas
- **Riesgo operacional**: ALTO → BAJO

---

## CONCLUSIÓN

El sistema actual está **VULNERABLE POR OMISIONES** con solo 13% de cobertura RBAC. La implementación de TenantPermissionByAction es correcta, pero solo se usa en 2 de 15+ ViewSets.

**Plan correctivo** de 3 semanas protegerá 100% de endpoints sin rediseñar arquitectura, usando infraestructura RBAC existente y consolidando en patrón estándar.

**Prioridad inmediata**: Proteger reportes financieros, inventario, servicios y nómina (Semana 1) para resolver 80% de vulnerabilidades críticas.
