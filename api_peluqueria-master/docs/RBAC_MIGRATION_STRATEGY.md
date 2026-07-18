# ESTRATEGIA DE MIGRACIÓN: User.role → UserRole + Role.permissions

## FASE 1: PREPARACIÓN (SIN ROMPER NADA)

### 1.1 Crear migraciones de permisos custom
```bash
python manage.py makemigrations pos_api employees_api
python manage.py migrate
```

### 1.2 Crear roles en base de datos con permisos
```python
# Script: scripts/setup_roles_permissions.py
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.roles_api.models import Role
from apps.employees_api.models import Employee
from apps.pos_api.models import Sale

# Crear roles base
client_admin = Role.objects.get_or_create(
    name='Client-Admin',
    defaults={'scope': 'TENANT', 'description': 'Administrador del tenant'}
)[0]

manager = Role.objects.get_or_create(
    name='Manager',
    defaults={'scope': 'TENANT', 'description': 'Manager con permisos limitados'}
)[0]

cajera = Role.objects.get_or_create(
    name='Cajera',
    defaults={'scope': 'TENANT', 'description': 'Cajera - solo POS'}
)[0]

# Asignar permisos a Client-Admin (todos)
employee_ct = ContentType.objects.get_for_model(Employee)
sale_ct = ContentType.objects.get_for_model(Sale)

admin_perms = Permission.objects.filter(
    content_type__in=[employee_ct, sale_ct]
)
client_admin.permissions.set(admin_perms)

# Asignar permisos a Cajera (solo ventas)
cajera_perms = Permission.objects.filter(
    content_type=sale_ct,
    codename__in=['add_sale', 'view_sale']
)
cajera.permissions.set(cajera_perms)

# Asignar permisos a Manager (lectura + algunas escrituras)
manager_perms = Permission.objects.filter(
    content_type__in=[employee_ct, sale_ct]
).exclude(codename__in=['delete_employee', 'delete_sale'])
manager.permissions.set(manager_perms)
```

### 1.3 Sincronizar User.role → UserRole
```python
# Script: scripts/sync_user_roles.py
from apps.auth_api.models import User
from apps.roles_api.models import Role, UserRole

for user in User.objects.filter(role__isnull=False).exclude(is_superuser=True):
    if not user.tenant:
        continue
    
    try:
        role = Role.objects.get(name=user.role)
        UserRole.objects.get_or_create(
            user=user,
            role=role,
            tenant=user.tenant
        )
        print(f"✅ Sincronizado: {user.email} → {role.name} en {user.tenant.name}")
    except Role.DoesNotExist:
        print(f"⚠️  Rol no existe: {user.role} para {user.email}")
```

## FASE 2: ACTIVACIÓN PROGRESIVA (COEXISTENCIA)

### 2.1 Aplicar nuevos permission_classes a ViewSets críticos
- ✅ EmployeeViewSet
- ✅ SaleViewSet
- ClientViewSet
- UserViewSet
- CashRegisterViewSet

### 2.2 Mantener User.role como fallback
```python
# En HasTenantPermission, agregar fallback temporal:
def has_permission(self, request, view):
    # ... código existente ...
    
    # FALLBACK TEMPORAL: Si no tiene UserRole, usar User.role
    if not user_roles.exists() and request.user.role:
        # Mapeo temporal User.role → permisos
        role_permissions = {
            'Client-Admin': True,  # Acceso total
            'Manager': self.required_permission in ['view_employee', 'view_sale'],
            'Cajera': self.required_permission in ['add_sale', 'view_sale'],
        }
        return role_permissions.get(request.user.role, False)
    
    return False
```

## FASE 3: VALIDACIÓN (2-4 SEMANAS)

### 3.1 Monitorear logs
```python
# Agregar logging en HasTenantPermission
import logging
logger = logging.getLogger('rbac')

def has_permission(self, request, view):
    result = # ... cálculo ...
    
    logger.info(
        f"RBAC: user={request.user.email} tenant={request.tenant.name} "
        f"perm={self.required_permission} result={result}"
    )
    return result
```

### 3.2 Verificar que NO se usa User.role en código nuevo
```bash
# Buscar usos de User.role
grep -r "user.role" apps/*/views.py
grep -r "request.user.role" apps/*/views.py
```

## FASE 4: DEPRECACIÓN (DESPUÉS DE VALIDACIÓN)

### 4.1 Marcar User.role como deprecated
```python
# En apps/auth_api/models.py
class User(AbstractBaseUser, PermissionsMixin):
    # DEPRECATED: Usar UserRole en su lugar
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        blank=True,
        null=True,
        help_text='DEPRECATED: Use UserRole instead'
    )
```

### 4.2 Eliminar fallback de HasTenantPermission
```python
# Remover código de fallback temporal
```

### 4.3 Eliminar permission_classes antiguas
```bash
# Eliminar archivos obsoletos
rm apps/core/permissions.py  # IsTenantAdmin, IsAdminRole
rm apps/core/role_permissions.py  # CanManageUsers
```

## FASE 5: LIMPIEZA (OPCIONAL, DESPUÉS DE 3+ MESES)

### 5.1 Crear migración para eliminar User.role
```python
# migrations/XXXX_remove_user_role.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('auth_api', 'XXXX_previous_migration'),
    ]
    
    operations = [
        migrations.RemoveField(
            model_name='user',
            name='role',
        ),
    ]
```

## ROLLBACK PLAN

Si algo falla en FASE 2-3:

1. Revertir permission_classes a IsAuthenticated
2. Mantener User.role activo
3. Investigar problema
4. Reintentar cuando esté corregido

## TESTING

```python
# tests/test_rbac_migration.py
from django.test import TestCase
from apps.auth_api.models import User
from apps.roles_api.models import Role, UserRole
from apps.tenants_api.models import Tenant

class RBACMigrationTest(TestCase):
    def test_user_with_userrole_has_permissions(self):
        tenant = Tenant.objects.create(name='Test', subdomain='test')
        user = User.objects.create(email='test@test.com', tenant=tenant)
        role = Role.objects.create(name='Cajera')
        UserRole.objects.create(user=user, role=role, tenant=tenant)
        
        # Asignar permisos al rol
        from django.contrib.auth.models import Permission
        perm = Permission.objects.get(codename='add_sale')
        role.permissions.add(perm)
        
        # Verificar
        self.assertTrue(user.has_perm('pos_api.add_sale'))
    
    def test_user_without_userrole_no_permissions(self):
        tenant = Tenant.objects.create(name='Test', subdomain='test')
        user = User.objects.create(email='test@test.com', tenant=tenant)
        
        self.assertFalse(user.has_perm('pos_api.add_sale'))
```

## CHECKLIST DE MIGRACIÓN

- [ ] Fase 1.1: Migraciones creadas
- [ ] Fase 1.2: Roles creados con permisos
- [ ] Fase 1.3: UserRole sincronizado
- [ ] Fase 2.1: ViewSets actualizados
- [ ] Fase 2.2: Fallback implementado
- [ ] Fase 3.1: Logging activo
- [ ] Fase 3.2: Validación en producción (2-4 semanas)
- [ ] Fase 4.1: User.role marcado deprecated
- [ ] Fase 4.2: Fallback eliminado
- [ ] Fase 4.3: Archivos obsoletos eliminados
- [ ] Fase 5.1: User.role eliminado (opcional)
