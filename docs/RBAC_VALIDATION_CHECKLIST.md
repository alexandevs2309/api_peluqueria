# CHECKLIST DE VALIDACIÓN POST-IMPLEMENTACIÓN

## MIGRACIONES REQUERIDAS

```bash
# Activar entorno virtual primero
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# Crear migraciones para permisos custom
python manage.py makemigrations employees_api pos_api

# Verificar migraciones generadas
python manage.py showmigrations employees_api pos_api

# Aplicar migraciones
python manage.py migrate
```

## VALIDACIONES CRÍTICAS

### 1. Backend NO filtra por tenant
**Estado:** ⚠️ DOCUMENTADO pero NO RESUELTO

**Impacto:** `user.has_perm()` valida permisos de TODOS los tenants del usuario.

**Solución:** NO usar `user.has_perm()` directamente. Usar siempre DRF permission classes.

**Código seguro:**
```python
# ❌ INSEGURO (no filtra tenant)
if request.user.has_perm('pos_api.add_sale'):
    # ...

# ✅ SEGURO (filtra tenant)
# Usar permission_classes en ViewSet
```

### 2. Permission_map completo
**Estado:** ✅ CORREGIDO

**Acciones cubiertas:**
- EmployeeViewSet: 14 acciones
- SaleViewSet: 9 acciones

**Validar:**
```python
# Verificar que todas las @action tienen mapeo
from apps.employees_api.views import EmployeeViewSet
from apps.pos_api.views import SaleViewSet

# Listar acciones
for attr in dir(EmployeeViewSet):
    method = getattr(EmployeeViewSet, attr)
    if hasattr(method, 'mapping'):
        print(f"Action: {attr}")
```

### 3. Permisos custom en modelos
**Estado:** ✅ AGREGADOS, ⚠️ PENDIENTE MIGRACIÓN

**Permisos agregados:**
- `pos_api.refund_sale`
- `pos_api.view_financial_reports`
- `employees_api.view_employee_payroll`
- `employees_api.manage_employee_loans`

**Validar después de migrar:**
```python
from django.contrib.auth.models import Permission

# Verificar permisos existen
perms = Permission.objects.filter(
    codename__in=[
        'refund_sale',
        'view_financial_reports',
        'view_employee_payroll',
        'manage_employee_loans'
    ]
)
print(f"Permisos custom: {perms.count()}/4")
```

### 4. TenantPermissionByAction filtra correctamente
**Estado:** ✅ CORRECTO

**Validar:**
```python
# Test manual
from apps.core.tenant_permissions import TenantPermissionByAction
from apps.roles_api.models import UserRole

# Verificar query
user_roles = UserRole.objects.filter(
    user=request.user,
    tenant=request.tenant  # ✅ Filtra por tenant
)
```

## PROBLEMAS CONOCIDOS

### 1. Backend sin filtrado por tenant
**Severidad:** MEDIA

**Escenario vulnerable:**
```python
# Usuario tiene roles en 2 tenants:
# - Tenant A: Cajera (solo view_sale)
# - Tenant B: Client-Admin (todos los permisos)

# Si llamas user.has_perm() sin contexto de tenant:
user.has_perm('pos_api.delete_sale')  # ✅ True (por Tenant B)

# Pero el usuario está en Tenant A (request.tenant)
# Debería ser False
```

**Mitigación:** NO usar `user.has_perm()` en código. Solo DRF permission classes.

### 2. Acciones sin mapeo
**Severidad:** ALTA

**Comportamiento:** Si una acción NO está en `permission_map`, TenantPermissionByAction permite solo lectura (GET/HEAD/OPTIONS).

**Validar:**
```python
# Buscar @action sin mapeo
grep -A 5 "@action" apps/*/views.py | grep "def " | cut -d' ' -f6
# Comparar con permission_map
```

### 3. Permisos custom sin migrar
**Severidad:** CRÍTICA

**Síntoma:** Permission.DoesNotExist al asignar permisos a roles.

**Solución:** Ejecutar migraciones ANTES de setup_roles_permissions.py

## ORDEN DE EJECUCIÓN CORRECTO

```bash
# 1. Crear migraciones
python manage.py makemigrations employees_api pos_api

# 2. Aplicar migraciones
python manage.py migrate

# 3. Configurar roles (DESPUÉS de migrar)
python manage.py shell < scripts/setup_roles_permissions.py

# 4. Sincronizar usuarios
python manage.py shell < scripts/sync_user_roles.py

# 5. Validar
python manage.py shell
>>> from django.contrib.auth.models import Permission
>>> Permission.objects.filter(codename='refund_sale').exists()
True  # ✅
```

## TESTING RECOMENDADO

```python
# tests/test_tenant_permissions.py
from django.test import TestCase, RequestFactory
from apps.auth_api.models import User
from apps.roles_api.models import Role, UserRole
from apps.tenants_api.models import Tenant
from apps.core.tenant_permissions import TenantPermissionByAction

class TenantPermissionTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        
        # Crear 2 tenants
        self.tenant_a = Tenant.objects.create(name='A', subdomain='a')
        self.tenant_b = Tenant.objects.create(name='B', subdomain='b')
        
        # Usuario con roles en ambos tenants
        self.user = User.objects.create(email='test@test.com', tenant=self.tenant_a)
        
        # Rol Cajera en Tenant A
        role_cajera = Role.objects.create(name='Cajera')
        UserRole.objects.create(user=self.user, role=role_cajera, tenant=self.tenant_a)
        
        # Rol Admin en Tenant B
        role_admin = Role.objects.create(name='Admin')
        UserRole.objects.create(user=self.user, role=role_admin, tenant=self.tenant_b)
    
    def test_permission_filtered_by_tenant(self):
        """Usuario solo tiene permisos del tenant activo"""
        from django.contrib.auth.models import Permission
        
        # Asignar permisos
        perm_delete = Permission.objects.get(codename='delete_sale')
        Role.objects.get(name='Admin').permissions.add(perm_delete)
        
        # Request en Tenant A (Cajera)
        request = self.factory.get('/')
        request.user = self.user
        request.tenant = self.tenant_a
        
        permission = TenantPermissionByAction()
        permission.permission_map = {'list': 'pos_api.delete_sale'}
        
        # NO debe tener permiso (es Cajera en Tenant A)
        self.assertFalse(permission.has_permission(request, None))
        
        # Request en Tenant B (Admin)
        request.tenant = self.tenant_b
        
        # SÍ debe tener permiso (es Admin en Tenant B)
        self.assertTrue(permission.has_permission(request, None))
```

## ROLLBACK SI FALLA

```bash
# 1. Revertir migraciones
python manage.py migrate employees_api <numero_migracion_anterior>
python manage.py migrate pos_api <numero_migracion_anterior>

# 2. Revertir cambios en views.py
git checkout apps/employees_api/views.py
git checkout apps/pos_api/views.py

# 3. Revertir cambios en models.py
git checkout apps/employees_api/models.py
git checkout apps/pos_api/models.py

# 4. Eliminar archivos nuevos
rm apps/core/tenant_permissions.py
rm scripts/setup_roles_permissions.py
rm scripts/sync_user_roles.py
```
