# CHECKLIST DE IMPLEMENTACIÓN - PLAN CORRECTIVO RBAC

**Sistema**: API Peluquería - Django Multi-Tenant SaaS  
**Objetivo**: Proteger 100% de endpoints con TenantPermissionByAction  
**Duración**: 3 semanas (14-17 horas)

---

## SEMANA 1 - CORRECCIÓN CRÍTICA (4-5 horas)

### ✅ PASO 1: Corregir Fallback Inseguro (30 min)

**Archivo**: `apps/core/tenant_permissions.py`

**Cambio**:
```python
# LÍNEA 100-102 - REEMPLAZAR
if not action or action not in permission_map:
    return False  # DENY BY DEFAULT - CAMBIO CRÍTICO
```

**Validar**:
```bash
python scripts/validate_rbac_security.py | grep "fallback"
```

---

### ✅ PASO 2: Proteger reports_api (2 horas)

#### 2.1 Crear Modelo ReportPermission

**Archivo**: `apps/reports_api/models.py` (CREAR)

```python
from django.db import models

class ReportPermission(models.Model):
    """Modelo para permisos de reportes"""
    
    class Meta:
        managed = False
        permissions = [
            ('view_financial_reports', 'Can view financial reports'),
            ('view_employee_reports', 'Can view employee reports'),
            ('view_sales_reports', 'Can view sales reports'),
            ('view_kpi_dashboard', 'Can view KPI dashboard'),
            ('view_advanced_analytics', 'Can view advanced analytics'),
        ]
```

#### 2.2 Crear Migración

```bash
cd api_peluqueria
python manage.py makemigrations reports_api
python manage.py migrate reports_api
```

#### 2.3 Modificar reports_api/views.py

**Agregar imports**:
```python
from apps.core.tenant_permissions import TenantPermissionByAction
```

**AdminReportsView**:
```python
class AdminReportsView(APIView):
    permission_classes = [TenantPermissionByAction]
    permission_map = {'get': 'reports_api.view_financial_reports'}
```

**EmployeeReportView**:
```python
class EmployeeReportView(APIView):
    permission_classes = [TenantPermissionByAction]
    permission_map = {'get': 'reports_api.view_employee_reports'}
```

**SalesReportView**:
```python
class SalesReportView(APIView):
    permission_classes = [TenantPermissionByAction]
    permission_map = {'get': 'reports_api.view_sales_reports'}
```

**KPIDashboardView**:
```python
class KPIDashboardView(APIView):
    permission_classes = [TenantPermissionByAction]
    permission_map = {'get': 'reports_api.view_kpi_dashboard'}
```

#### 2.4 Modificar reports_api/analytics_views.py

```python
@api_view(['GET'])
@permission_classes([TenantPermissionByAction])
def advanced_analytics(request):
    # Agregar permission_map como atributo de función
    pass

# Alternativa: Convertir a APIView con permission_map
```

#### 2.5 Modificar reports_api/realtime_views.py

Similar a analytics_views.py

**Validar**:
```bash
python scripts/validate_rbac_security.py | grep "reports_api"
```

---

### ✅ PASO 3: Proteger inventory_api (30 min)

#### 3.1 Crear Custom Permission

**Archivo**: `apps/inventory_api/models.py`

```python
class Product(models.Model):
    # ... campos existentes ...
    
    class Meta:
        permissions = [
            ('adjust_stock', 'Can adjust product stock'),
        ]
```

#### 3.2 Crear Migración

```bash
python manage.py makemigrations inventory_api
python manage.py migrate inventory_api
```

#### 3.3 Modificar inventory_api/views.py

```python
from apps.core.tenant_permissions import TenantPermissionByAction

class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'inventory_api.view_product',
        'retrieve': 'inventory_api.view_product',
        'create': 'inventory_api.add_product',
        'update': 'inventory_api.change_product',
        'partial_update': 'inventory_api.change_product',
        'destroy': 'inventory_api.delete_product',
        'adjust_stock': 'inventory_api.adjust_stock',
        'low_stock': 'inventory_api.view_product',
        'stock_report': 'inventory_api.view_product',
        'search_by_barcode': 'inventory_api.view_product',
    }
```

**Validar**:
```bash
python scripts/validate_rbac_security.py | grep "ProductViewSet"
```

---

### ✅ PASO 4: Proteger services_api (1 hora)

#### 4.1 Crear Custom Permissions

**Archivo**: `apps/services_api/models.py`

```python
class Service(models.Model):
    # ... campos existentes ...
    
    class Meta:
        permissions = [
            ('set_employee_price', 'Can set employee-specific prices'),
            ('assign_employees', 'Can assign employees to services'),
        ]
```

#### 4.2 Crear Migración

```bash
python manage.py makemigrations services_api
python manage.py migrate services_api
```

#### 4.3 Modificar services_api/views.py

```python
from apps.core.tenant_permissions import TenantPermissionByAction

class ServiceViewSet(viewsets.ModelViewSet):
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'services_api.view_service',
        'retrieve': 'services_api.view_service',
        'create': 'services_api.add_service',
        'update': 'services_api.change_service',
        'partial_update': 'services_api.change_service',
        'destroy': 'services_api.delete_service',
        'set_employee_price': 'services_api.set_employee_price',
        'assign_employees': 'services_api.assign_employees',
        'categories': 'services_api.view_service',
        'employees': 'services_api.view_service',
    }

class ServiceCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'services_api.view_servicecategory',
        'retrieve': 'services_api.view_servicecategory',
        'create': 'services_api.add_servicecategory',
        'update': 'services_api.change_servicecategory',
        'partial_update': 'services_api.change_servicecategory',
        'destroy': 'services_api.delete_servicecategory',
    }
```

**Validar**:
```bash
python scripts/validate_rbac_security.py | grep "ServiceViewSet"
```

---

### ✅ PASO 5: Proteger earnings_views (1 hora)

**Archivo**: `apps/employees_api/earnings_views.py`

**Cambios**:

1. Eliminar método `_require_admin_role`
2. Agregar TenantPermissionByAction
3. Agregar permission_map

```python
from apps.core.tenant_permissions import TenantPermissionByAction

class PayrollViewSet(viewsets.ViewSet):
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list_periods': 'employees_api.view_employee_payroll',
        'register_payment': 'employees_api.manage_employee_loans',
        'recalculate_period': 'employees_api.view_employee_payroll',
        'submit_for_approval': 'employees_api.view_employee_payroll',
        'approve_period': 'employees_api.view_employee_payroll',
        'reject_period': 'employees_api.view_employee_payroll',
        'get_receipt': 'employees_api.view_employee_payroll',
    }
    
    # ELIMINAR: def _require_admin_role(self, request)
    # ELIMINAR: Todas las llamadas a self._require_admin_role(request)
```

**Validar**:
```bash
python scripts/validate_rbac_security.py | grep "PayrollViewSet"
python scripts/validate_rbac_security.py | grep "_require_admin_role"
```

---

### ✅ VALIDACIÓN SEMANA 1

```bash
# Ejecutar script completo
python scripts/validate_rbac_security.py

# Verificar que vulnerabilidades críticas bajaron de 49 a ~10
# Verificar que fallback está corregido
# Verificar que reports_api está protegido
```

**Resultado esperado**: 80% vulnerabilidades críticas resueltas

---

## SEMANA 2 - COBERTURA COMPLETA (6-7 horas)

### ✅ PASO 6: Migrar AppointmentViewSet (1 hora)

**Archivo**: `apps/appointments_api/models.py`

```python
class Appointment(models.Model):
    # ... campos existentes ...
    
    class Meta:
        permissions = [
            ('cancel_appointment', 'Can cancel appointments'),
            ('complete_appointment', 'Can mark appointments as complete'),
        ]
```

**Migración**:
```bash
python manage.py makemigrations appointments_api
python manage.py migrate appointments_api
```

**Archivo**: `apps/appointments_api/views.py`

```python
from apps.core.tenant_permissions import TenantPermissionByAction

class AppointmentViewSet(viewsets.ModelViewSet):
    permission_classes = [TenantPermissionByAction]
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

---

### ✅ PASO 7: Migrar ClientViewSet (30 min)

**Archivo**: `apps/clients_api/views.py`

```python
from apps.core.tenant_permissions import TenantPermissionByAction

class ClientViewSet(viewsets.ModelViewSet):
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'clients_api.view_client',
        'retrieve': 'clients_api.view_client',
        'create': 'clients_api.add_client',
        'update': 'clients_api.change_client',
        'partial_update': 'clients_api.change_client',
        'destroy': 'clients_api.delete_client',
        'history': 'clients_api.view_client',
        'add_loyalty_points': 'clients_api.change_client',
        'redeem_points': 'clients_api.change_client',
        'stats': 'clients_api.view_client',
        'birthdays_this_month': 'clients_api.view_client',
        'birthdays_today': 'clients_api.view_client',
        'upcoming_birthdays': 'clients_api.view_client',
    }
```

---

### ✅ PASO 8: Migrar InvoiceViewSet (1 hora)

**Archivo**: `apps/billing_api/models.py`

```python
class Invoice(models.Model):
    # ... campos existentes ...
    
    class Meta:
        permissions = [
            ('mark_invoice_paid', 'Can mark invoices as paid'),
            ('process_payment', 'Can process payments'),
        ]
```

**Migración**:
```bash
python manage.py makemigrations billing_api
python manage.py migrate billing_api
```

**Archivo**: `apps/billing_api/views.py`

```python
from apps.core.tenant_permissions import TenantPermissionByAction

class InvoiceViewSet(viewsets.ModelViewSet):
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'billing_api.view_invoice',
        'retrieve': 'billing_api.view_invoice',
        'create': 'billing_api.add_invoice',
        'mark_as_paid': 'billing_api.mark_invoice_paid',
        'pay': 'billing_api.process_payment',
    }
    
    # ELIMINAR validación is_superuser en get_queryset
```

---

### ✅ PASO 9: Actualizar setup_roles_permissions.py (1 hora)

**Archivo**: `scripts/setup_roles_permissions.py`

Agregar nuevos permisos a roles:

```python
# Client-Admin: TODOS
admin_permissions = [
    # ... existentes ...
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
    'reports_api.view_advanced_analytics',
]

# Manager: Sin delete, sin reportes financieros
manager_permissions = [
    # ... existentes ...
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

**Ejecutar**:
```bash
docker-compose exec web python scripts/setup_roles_permissions.py
```

---

### ✅ PASO 10: Migrar ViewSets Restantes (2 horas)

Aplicar mismo patrón a:
- PaymentViewSet
- PaymentAttemptViewSet
- NotificationListCreateView
- NotificationDetailView
- SystemSettingsRetrieveUpdateView
- BarbershopSettingsViewSet
- Todos los ViewSets detectados en auditoría

---

### ✅ VALIDACIÓN SEMANA 2

```bash
python scripts/validate_rbac_security.py

# Verificar cobertura >= 95%
# Verificar ViewSets protegidos >= 20/23
```

---

## SEMANA 3 - CONSOLIDACIÓN (4-5 horas)

### ✅ PASO 11: Eliminar Validaciones Ad-Hoc (2 horas)

**Archivos a modificar**:

1. `billing_api/views.py` - InvoiceViewSet.get_queryset
2. `notifications_api/views.py` - NotificationListCreateView.get_queryset
3. `tenants_api/views.py` - TenantViewSet.get_queryset
4. `tenants_api/admin_views.py` - AdminUserManagementViewSet.get_queryset
5. `subscriptions_api/views.py` - Múltiples validaciones

**Patrón**:
- Eliminar validaciones `user.roles.filter`
- Eliminar validaciones `is_superuser` (excepto IsSuperAdmin)
- Reemplazar con TenantPermissionByAction

---

### ✅ PASO 12: Tests de Autorización (2 horas)

**Crear**: `apps/core/tests/test_rbac_authorization.py`

```python
from django.test import TestCase
from apps.auth_api.models import User
from apps.roles_api.models import Role, UserRole
from apps.tenants_api.models import Tenant

class RBACAuthorizationTests(TestCase):
    def setUp(self):
        # Crear tenant
        self.tenant = Tenant.objects.create(name="Test Salon")
        
        # Crear roles
        self.admin_role = Role.objects.get(name='Client-Admin')
        self.cajera_role = Role.objects.get(name='Cajera')
        
        # Crear usuarios
        self.admin = User.objects.create(
            email='admin@test.com',
            tenant=self.tenant
        )
        UserRole.objects.create(
            user=self.admin,
            role=self.admin_role,
            tenant=self.tenant
        )
        
        self.cajera = User.objects.create(
            email='cajera@test.com',
            tenant=self.tenant
        )
        UserRole.objects.create(
            user=self.cajera,
            role=self.cajera_role,
            tenant=self.tenant
        )
    
    def test_cajera_cannot_view_financial_reports(self):
        self.client.force_login(self.cajera)
        response = self.client.get('/api/reports/admin/')
        self.assertEqual(response.status_code, 403)
    
    def test_admin_can_view_financial_reports(self):
        self.client.force_login(self.admin)
        response = self.client.get('/api/reports/admin/')
        self.assertEqual(response.status_code, 200)
    
    def test_cajera_cannot_adjust_stock(self):
        self.client.force_login(self.cajera)
        response = self.client.post('/api/inventory/products/1/adjust_stock/')
        self.assertEqual(response.status_code, 403)
    
    # ... más tests
```

**Ejecutar**:
```bash
docker-compose exec web python manage.py test apps.core.tests.test_rbac_authorization
```

---

### ✅ PASO 13: Auditoría Manual Final (1 hora)

**Checklist**:

- [ ] TenantPermissionByAction usa `return False` para acciones no mapeadas
- [ ] Todos los ViewSets tienen permission_classes = [TenantPermissionByAction]
- [ ] Todos los ViewSets tienen permission_map completo
- [ ] Todas las @action están en permission_map
- [ ] Todos los APIViews tienen permission_classes
- [ ] Cero validaciones ad-hoc de roles en métodos
- [ ] Custom permissions migrados a base de datos
- [ ] Roles actualizados con nuevos permisos
- [ ] Tests de autorización ejecutados y pasando
- [ ] Script de validación reporta 0 vulnerabilidades

**Ejecutar validación final**:
```bash
python scripts/validate_rbac_security.py
```

**Resultado esperado**:
```
CRÍTICAS: 0
ALTAS: 0
MEDIAS: 0
TOTAL: 0 vulnerabilidades detectadas

Estado: SEGURO
Cobertura: 100%
```

---

## COMANDOS ÚTILES

### Validar Seguridad
```bash
python scripts/validate_rbac_security.py
```

### Buscar ViewSets sin Protección
```bash
grep -r "permission_classes = \[IsAuthenticated\]" apps/*/views.py
```

### Buscar @action sin permission_map
```bash
grep -r "@action" apps/*/views.py | grep -v "permission_map"
```

### Buscar Validaciones Ad-Hoc
```bash
grep -r "user.roles.filter" apps/*/views.py
grep -r "is_superuser" apps/*/views.py | grep -v "# SuperAdmin"
```

### Ejecutar Tests
```bash
docker-compose exec web python manage.py test apps.core.tests.test_rbac_authorization
```

---

## ROLLBACK (Si es necesario)

Si algo falla, revertir cambios:

```bash
git checkout apps/core/tenant_permissions.py
git checkout apps/reports_api/
git checkout apps/inventory_api/
# ... etc
```

---

## DOCUMENTACIÓN FINAL

Actualizar:
- [ ] README.md con sección de seguridad RBAC
- [ ] docs/RBAC_ARCHITECTURE.md con arquitectura final
- [ ] docs/PERMISSION_MATRIX.md con matriz de permisos por rol
- [ ] docs/SECURITY_AUDIT_RBAC.md con estado "RESUELTO"

---

**Fin del Checklist**
