# AUDITORÍA COMPLETA DE RBAC
## Auron Suite - Plataforma SaaS Multi-Tenant

**Auditor**: Senior Django + DRF Architect | Especialista RBAC SaaS  
**Fecha**: 26-04-2026  
**Nivel de Revisión**: EXHAUSTIVA (COMPLETA)  
**Stack Auditado**: Django 4.x + DRF + PostgreSQL + Angular + JWT  
**Clasificación**: CONFIDENCIAL

---

## 📑 ÍNDICE EJECUTIVO

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Hallazgos Críticos](#hallazgos-críticos)
3. [Arquitectura Actual Mapeada](#arquitectura-actual-mapeada)
4. [Análisis por Rol](#análisis-por-rol)
5. [Vulnerabilidades Detectadas](#vulnerabilidades-detectadas)
6. [Matriz Ideal de Permisos](#matriz-ideal-de-permisos)
7. [Riesgos de Acceso Cruzado](#riesgos-de-acceso-cruzado)
8. [Validaciones Propuestas](#validaciones-propuestas)
9. [Plan de Correcciones](#plan-de-correcciones)
10. [Recomendaciones CTO](#recomendaciones-cto)

---

## RESUMEN EJECUTIVO

### Estado Actual: **7/10 - MODERADAMENTE SEGURO**

**Puntuación por Área**:
- Aislamiento Multi-Tenant: 9/10 ✅
- Validación de Permisos: 7/10 ⚠️
- Roles Definidos: 6/10 ⚠️
- Protección de Endpoints: 7/10 ⚠️
- Auditoría de Acceso: 8/10 ✅
- Control de Features: 6/10 ⚠️

### Vulnerabilidades Críticas Identificadas: **3**
### Vulnerabilidades Altas: **8**
### Recomendaciones: **15**

---

## HALLAZGOS CRÍTICOS

### 🔴 CRÍTICA #1: Client-Admin con Permiso Wildcard '*'

**Ubicación**: `apps/core/tenant_permissions.py` línea ~119

**Código Actual**:
```python
ROLE_IMPLICIT_PERMISSIONS = {
    'Client-Admin': '*',  # ⚠️ ACCESO TOTAL A TODO
    ...
}
```

**Impacto**:
- Client-Admin PUEDE: crear usuarios, editar nómina, ver reportes financieros, cambiar configuración
- Client-Admin NO está limitado a su tenant (solo por middleware)
- Si hay bypass de middleware, Client-Admin accede a TODO
- Incumple principio de "Least Privilege"

**Riesgo**: **ALTO**
- Un admin de un salon (tenant) podría teóricamente acceder a datos de otro salon si hay flaw

**Solución**:
```python
'Client-Admin': [
    # Gestión de usuarios
    'add_user', 'change_user', 'delete_user', 'view_user',
    # Configuración del tenant
    'change_tenant_settings', 'view_tenant_settings',
    # Empleados
    'add_employee', 'change_employee', 'view_employee',
    # Roles y permisos
    'view_role', 'change_role',
    # Reportes
    'view_financial_report', 'view_sales_report', 'view_employee_report',
    # Configuración POS
    'view_pos_configuration', 'change_pos_configuration',
    # Auditoría
    'view_audit_log',
    # NO incluir: delete_tenant, manage_subscriptions, etc.
]
```

**Prioridad**: CRÍTICA - Corregir en < 1 hora

---

### 🔴 CRÍTICA #2: Rol "Soporte" Sin Permisos Implícitos Definidos

**Ubicación**: `apps/core/tenant_permissions.py`

**Problema**: El rol "Soporte" existe en la jerarquía pero NO está en `ROLE_IMPLICIT_PERMISSIONS`

**Código Actual**:
```python
ROLE_IMPLICIT_PERMISSIONS = {
    'Client-Admin': '*',
    'Manager': [...],
    'Cajera': [...],
    'Estilista': [...],
    'Client-Staff': [...],
    'Utility': [...],
    # ❌ 'Soporte': FALTA
}
```

**Impacto**:
- Usuarios con rol Soporte NO pueden acceder a NADA (403 en todos los endpoints)
- Si el rol se asigna en producción, quedará inoperativo
- Inconsistencia en la jerarquía de roles

**Solución**:
```python
'Soporte': [
    # Lectura total (auditoría / debugging)
    'view_user', 'view_employee', 'view_client', 'view_sale', 'view_appointment',
    'view_product', 'view_service', 'view_audit_log',
    # Acciones limitadas (reset password, desbloquear cuenta)
    'reset_user_password', 'unlock_user_account', 'view_tenant_settings',
    # NO: delete_*, change_sensitive_*, create_*
]
```

**Prioridad**: CRÍTICA - Corregir en < 30 min

---

### 🔴 CRÍTICA #3: SuperAdmin Sin Validación has_object_permission()

**Ubicación**: `apps/core/tenant_permissions.py` línea ~150-155

**Código Actual**:
```python
def has_permission(self, request, view):
    if request.user.is_superuser:
        return True  # ⚠️ BYPASEA TODO
    # ... resto de validaciones ...

# has_object_permission() NO implementado para SuperAdmin
```

**Impacto**:
- SuperAdmin puede acceder a CUALQUIER objeto sin validar tenant
- Si existe bug en queryset filtering, SuperAdmin vería datos de otros tenants
- No hay protección doble (defense in depth)

**Escenario de Riesgo**:
```python
# En algún ViewSet mal configurado:
class BadViewSet(ViewSet):
    def get_queryset(self):
        if self.request.user.is_superuser:
            return Product.objects.all()  # ← TODOS los productos, todos los tenants
        return Product.objects.filter(tenant=self.request.tenant)
```

**Solución**:
```python
class TenantPermissionByAction(BasePermission):
    def has_permission(self, request, view):
        # ... validaciones ...
        return True/False
    
    def has_object_permission(self, request, view, obj):
        # SuperAdmin sí puede acceder
        if request.user.is_superuser:
            return True
        
        # Usuarios normales: validar tenant
        tenant = getattr(request, 'tenant', None)
        if hasattr(obj, 'tenant'):
            return obj.tenant == tenant
        
        # Si objeto no tiene tenant, denegar
        return False
```

**Prioridad**: CRÍTICA - Implementar defense in depth

---

## ARQUITECTURA ACTUAL MAPEADA

### Jerarquía de Roles (Como existe hoy)

```
PLATAFORMA (SuperAdmin)
├─ Acceso global
├─ Bypass de todos los controles
└─ No limitado a tenant

TENANT (Client-Admin) - ⚠️ WILDCARD '*'
├─ Gestiona su negocio
├─ Puede crear/eliminar usuarios
├─ Ve reportes financieros
└─ [DEBERÍA estar limitado a 30-40 permisos específicos]

TENANT OPERACIONAL
├─ Manager (13 permisos) - ✅ Bien definido
│  ├─ Gestiona citas
│  ├─ Ve clientes
│  ├─ Reportes operacionales
│  └─ NO puede: nómina, configuración global
│
├─ Cajera (15 permisos) - ✅ Recientemente corregido
│  ├─ VE: productos, promociones
│  ├─ VENDE: crear ventas
│  ├─ COBRA: caja registradora
│  └─ NO puede: editar productos, crear usuarios
│
├─ Estilista (8 permisos) - ✅ Bien definido
│  ├─ Ve citas propias
│  ├─ Marca asistencia
│  ├─ Ve clientes
│  └─ NO puede: acceso administrativo
│
├─ Client-Staff (8 permisos) - ✅ Bien definido
│  ├─ Lectura limitada
│  ├─ Marca asistencia
│  └─ NO puede: modificar datos
│
└─ Utility (3 permisos) - ✅ Acceso mínimo
   ├─ Ve empleados
   ├─ Ve citas
   └─ NO puede: casi nada

ESPECIAL (❌ INCOMPLETO)
└─ Soporte - SIN PERMISOS IMPLÍCITOS
   ├─ [Debería tener permisos de lectura]
   └─ Actualmente: 403 en todo
```

### Niveles de Validación (Capas)

```
CAPA 1: Middleware
  ├─ TenantMiddleware → Inyecta request.tenant
  ├─ SubscriptionValidationMiddleware → Valida estado de suscripción
  └─ Validaciones: tenant activo, plan válido, etc.

CAPA 2: Permission Classes (DRF)
  ├─ TenantPermissionByAction → Valida permiso por acción
  ├─ HasFeaturePermission → Valida si plan tiene feature
  ├─ IsSuperAdmin → Solo superusuarios
  └─ IsTenantAdmin → Solo Client-Admin o SuperAdmin

CAPA 3: ViewSet level
  ├─ permission_map: mapeo de acción → permiso
  ├─ queryset filtering: filtra por tenant
  └─ get_serializer_context(): pasa request al serializer

CAPA 4: Serializer level
  ├─ to_representation(): puede filtrar campos por rol
  ├─ validate(): validaciones de negocio
  └─ (No implementa seguridad, solo datos)

CAPA 5: Queryset filtering
  ├─ get_queryset() en ViewSet
  ├─ Filtra por tenant: Product.objects.filter(tenant=request.tenant)
  └─ Fallback a none() si no hay tenant
```

### Archivos Clave del Sistema RBAC

```
1. DEFINICIÓN DE ROLES
   └─ apps/roles_api/models.py
      ├─ Role(name, scope, permissions M2M)
      └─ UserRole(user, role, tenant)

2. PERMISOS IMPLÍCITOS (Fallback)
   └─ apps/core/tenant_permissions.py
      └─ ROLE_IMPLICIT_PERMISSIONS = {...}

3. VALIDADORES DE PERMISOS
   └─ apps/core/tenant_permissions.py
      ├─ HasTenantPermission
      └─ TenantPermissionByAction ← USADO EN 22+ VIEWSETS

4. PROTECCIÓN MULTI-TENANT
   └─ apps/tenants_api/middleware.py
      └─ TenantMiddleware → Inyecta tenant en request

5. CADA VIEWSET
   └─ permission_classes = [TenantPermissionByAction, HasFeaturePermission]
   └─ permission_map = {'list': 'app_api.view_model', ...}
```

---

## ANÁLISIS POR ROL

### 1. SUPERADMIN PLATAFORMA

**Definición**: Administrador global del SaaS. Acceso irrestricto.

**Permisos Actuales**: `is_superuser=True` → Bypass de TODO

#### ✅ Qué DEBERÍA poder hacer:

- ✅ Ver/editar todos los tenants
- ✅ Ver/editar todos los usuarios
- ✅ Ver reportes globales (MRR, churn, etc.)
- ✅ Gestionar planes de suscripción
- ✅ Ver audit logs de TODO el sistema
- ✅ Hacer cambios de emergencia en producción
- ✅ Ver datos financieros globales
- ✅ Acceder a cualquier tenant para debugging

#### ❌ Qué NO debería poder hacer:

- ❌ Acceder a datos sin auditarse (TODO debe logearse)
- ❌ Modificar datos de usuario sin autorización
- ❌ Borrar registros de auditoría
- ❌ Cambiar su propio rol a través de la API

#### 🔒 Controles Actuales:

```python
# En middleware: SuperAdmin bypasea TODO
if get_effective_role_name(request.user) == 'SuperAdmin':
    return None  # Sin restricciones de tenant
```

#### 🚨 VULNERABILIDADES:

1. **No hay Dual Control**: Un SuperAdmin puede cambiar su contraseña sin aprobación
2. **Audit puede ser limitado**: Si hay bug, SuperAdmin podría no logearse
3. **No hay Rate Limiting**: SuperAdmin podría hacer 10k acciones por minuto
4. **IP Whitelisting**: No hay restricción de desde qué IP entra SuperAdmin

#### 📊 RECOMENDACIONES PARA SUPERADMIN:

| Recomendación | Prioridad | Implementación |
|---------------|-----------|---|
| Implementar dual approval para cambios críticos | ALTA | 4 horas |
| Agregar IP whitelist config | MEDIA | 2 horas |
| Rate limiting específico para SuperAdmin | MEDIA | 1 hora |
| Audit log inmutable | ALTA | 6 horas |
| 2FA obligatorio | ALTA | 3 horas |
| Sesión con timeout agresivo (15 min) | MEDIA | 30 min |

---

### 2. CLIENT-ADMIN (DUEÑO DEL NEGOCIO)

**Definición**: Propietario/administrador del tenant (ej: dueño del salón).

**Permisos Actuales**: `ROLE_IMPLICIT_PERMISSIONS['Client-Admin'] = '*'`

#### ✅ Qué DEBERÍA poder hacer:

- ✅ Ver/editar empleados de su salón
- ✅ Ver reportes de su salón
- ✅ Configurar salón (horarios, servicios)
- ✅ Gestionar usuarios de su salón
- ✅ Ver todas las ventas de su salón
- ✅ Acceder a configuración de planes
- ✅ Ver facturación de su salón

#### ❌ Qué NO debería poder hacer:

- ❌ Acceder a otros salones
- ❌ Editar el plan de suscripción (solo ver)
- ❌ Ver datos de SuperAdmin
- ❌ Eliminar el tenant
- ❌ Crear otros Client-Admin
- ❌ Ver datos de otros tenants

#### 🔒 Controles Actuales:

```python
'Client-Admin': '*'  # ⚠️ WILDCARD - PERMITE TODO EN SU TENANT
```

#### 🚨 VULNERABILIDADES DETECTADAS:

1. **Permiso Wildcard**: Si hay bypass de middleware tenant, accede a TODO
2. **Sin limitación de features**: Client-Admin ve features aunque plan no tenga
3. **Puede editar roles**: Podría promocionarse a sí mismo a SuperAdmin (si hay bug)
4. **Sin restricción de usuarios creados**: Podría crear 10k usuarios fake

#### 📊 MATRIZ IDEAL PARA CLIENT-ADMIN:

```python
'Client-Admin': [
    # USUARIOS
    'add_user', 'change_user', 'delete_user', 'view_user',
    
    # EMPLEADOS
    'add_employee', 'change_employee', 'delete_employee', 'view_employee',
    'view_employee_reports', 'export_employee_data',
    
    # CLIENTES
    'add_client', 'change_client', 'delete_client', 'view_client',
    
    # SERVICIOS
    'add_service', 'change_service', 'delete_service', 'view_service',
    
    # PRODUCTOS / INVENTARIO
    'add_product', 'change_product', 'delete_product', 'view_product',
    'adjust_stock', 'view_supplier',
    
    # CITAS
    'add_appointment', 'change_appointment', 'cancel_appointment', 
    'complete_appointment', 'view_appointment',
    
    # POS / VENTAS
    'add_sale', 'change_sale', 'delete_sale', 'view_sale', 'refund_sale',
    'add_cashregister', 'change_cashregister', 'view_cashregister',
    'add_promotion', 'change_promotion', 'delete_promotion', 'view_promotion',
    
    # REPORTES
    'view_sales_report', 'view_employee_report', 'view_financial_report',
    'view_kpi_dashboard', 'export_reports',
    
    # CONFIGURACIÓN
    'change_tenant_settings', 'view_tenant_settings',
    
    # ROLES (limitado)
    'view_role', 'change_role_permissions', # NO: delete_role, create_admin_role
    
    # AUDITORÍA
    'view_audit_log',
    
    # PAGOS
    'view_invoice', 'view_payment',
    
    # NO: manage_subscriptions, manage_plans, delete_tenant, etc.
]
```

**Total**: 45-50 permisos específicos (en lugar de wildcard '*')

---

### 3. MANAGER (GERENTE/SUPERVISOR)

**Definición**: Operacional diario. Supervisa staff.

**Permisos Actuales**: 13 permisos implícitos ✅

#### ✅ Estado Actual: BIEN DEFINIDO

```python
'Manager': [
    'view_appointment', 'add_appointment', 'change_appointment',
    'cancel_appointment', 'complete_appointment',
    'view_client', 'add_client', 'change_client',
    'view_employee',
    'view_service',
    'view_employee_reports', 'view_sales_reports', 'view_kpi_dashboard',
]
```

#### ✅ Qué puede hacer:
- Ver citas y clientes
- Abrir/cerrar citas
- Ver empleados y reportes
- NO puede: modificar productos, crear usuarios, editar nómina

#### ⚠️ PERO le falta:

```python
# AGREGAR A Manager:
'view_product',              # Necesita ver catálogo para verificar
'view_promotion',            # Necesita ver promociones activas
'view_cashregister',         # Necesita revisar cajas
'view_sale',                 # Necesita auditar ventas
'view_audit_log',            # Para supervisar cambios
```

#### 📋 MATRIZ RECOMENDADA PARA MANAGER:

```python
'Manager': [
    # Citas (completo)
    'view_appointment', 'add_appointment', 'change_appointment',
    'cancel_appointment', 'complete_appointment',
    
    # Clientes
    'view_client', 'add_client', 'change_client',
    
    # Empleados (lectura)
    'view_employee', 'view_employee_reports',
    
    # Servicios (lectura)
    'view_service',
    
    # Productos (lectura)
    'view_product',
    
    # Promociones (lectura)
    'view_promotion',
    
    # Ventas (lectura + auditoría)
    'view_sale', 'view_cashregister',
    
    # Reportes
    'view_sales_reports', 'view_employee_reports', 'view_kpi_dashboard',
    
    # Auditoría
    'view_audit_log',
    
    # NO: create_*, delete_*, change_product, etc.
]
```

---

### 4. CAJERA (POS OPERATOR)

**Definición**: Opera la caja. Vende productos.

**Permisos Actuales**: 15 permisos implícitos (RECIENTEMENTE CORREGIDO) ✅

```python
'Cajera': [
    'view_employee', 'view_appointment', 'add_appointment',
    'change_appointment', 'view_client', 'add_client',
    'change_client', 'view_service', 'view_sale', 'add_sale',
    'view_cashregister', 'add_cashregister', 'change_cashregister',
    'view_product', 'view_promotion',  # ← AGREGADOS
]
```

#### ✅ Qué puede hacer:
- ✅ Ver catálogo de productos
- ✅ Ver promociones activas
- ✅ Crear ventas
- ✅ Abrir/cerrar caja
- ✅ Ver clientes
- ✅ Crear citas rápidas (si el cliente no existe)

#### ❌ Qué NO puede hacer:
- ❌ Editar productos
- ❌ Crear promociones
- ❌ Eliminar ventas
- ❌ Ver salarios (nómina)
- ❌ Ver reportes financieros
- ❌ Crear usuarios

#### 🔍 VERIFICACIÓN DE CAMPO VISIBILITY:

En ProductSerializer (línea 33):
```python
fields = ['id', 'name', 'sku', 'barcode', 'price', 'stock', 'min_stock', 
          'unit', 'is_active', 'description', 'category', 'category_name', 
          'image', 'image_url']
```

✅ NO EXPONE: `supplier`, `tenant`, `cost_price`, `margin_percentage`

#### ⚠️ RIESGO RESIDUAL:

1. **Puede crear muchas citas**: Cajera podría crear 1000 citas sin límite
2. **Sin restricción de montos**: Cajera podría procesar venta de $999.999
3. **Sin aprobación de refunds**: Cajera puede hacer refund sin autorización

#### 📋 MEJORAS RECOMENDADAS:

```python
# Agregar validaciones en SaleViewSet:
- Máximo 1 refund por día por usuario
- Montos > $1000 requieren Manager approval
- Histórico de refunds es auditado
- Tiempo máximo para refund: 24 horas después de venta
```

---

### 5. ESTILISTA (OPERATIVO)

**Definición**: Empleado que da servicios.

**Permisos Actuales**: 8 permisos implícitos ✅

```python
'Estilista': [
    'view_employee', 'view_appointment', 'view_client',
    'view_service', 'view_sale', 'view_attendancerecord',
    'add_attendancerecord', 'change_attendancerecord',
]
```

#### ✅ Estado: BIEN DEFINIDO

- ✅ Ve sus citas
- ✅ Ve clientes que atiende
- ✅ Marca asistencia
- ✅ Ve sus ventas
- ❌ NO puede: editar nada, eliminar nada

#### ⚠️ PERO:

1. **Podría ver TODO los empleados**: `view_employee` es global
2. **Podría ver TODO los sales**: `view_sale` no está filtrado por empleado

#### 🔧 CORRECCIONES RECOMENDADAS:

```python
# En ViewSet, filtrar:
- EmployeeViewSet: GET /employees → solo datos públicos, no salarios
- SaleViewSet: GET /sales → solo ventas donde estilista fue asignado
- AppointmentViewSet: GET /appointments → solo citas asignadas a estilista
```

---

### 6. CLIENT-STAFF (ADMIN JR / RECEPCIÓN)

**Definición**: Staff de la empresa. Recepción, asistencia.

**Permisos Actuales**: 8 permisos implícitos ✅

```python
'Client-Staff': [
    'view_employee', 'view_appointment', 'view_client',
    'view_service', 'view_sale', 'view_attendancerecord',
    'add_attendancerecord', 'change_attendancerecord',
]
```

#### ✅ Estado: BIEN DEFINIDO (igual a Estilista)

---

### 7. UTILITY (ACCESO MÍNIMO)

**Definición**: Acceso de prueba / especial.

**Permisos Actuales**: 3 permisos implícitos ✅

```python
'Utility': ['view_employee', 'view_appointment', 'view_service']
```

#### ✅ Estado: BIEN DEFINIDO

---

### 8. SOPORTE (❌ INCOMPLETO - CRÍTICO)

**Definición**: Equipo de soporte interno. Debe poder debuggear sin modificar.

**Permisos Actuales**: ❌ NO DEFINIDO EN ROLE_IMPLICIT_PERMISSIONS

#### 🚨 IMPACTO:

Si se asigna el rol Soporte a un usuario:
- 403 en todos los endpoints
- Usuario no puede hacer nada
- Rol está quebrado

#### 📋 MATRIZ PROPUESTA PARA SOPORTE:

```python
'Soporte': [
    # LECTURA TOTAL (para debugging)
    'view_user', 'view_employee', 'view_client', 'view_appointment',
    'view_sale', 'view_product', 'view_service', 'view_promotion',
    'view_cashregister', 'view_audit_log', 'view_tenant_settings',
    
    # ACCIONES LIMITADAS
    'reset_user_password',      # Reset sin cambiar dirección
    'unlock_user_account',      # Desbloquear account lockout
    'view_employee_reports',    # Ver reportes para debugging
    
    # NO: delete_*, change_*, create_*, etc.
    # Soporte es READ-ONLY + reset password + unlock
]
```

---

## VULNERABILIDADES DETECTADAS

### Vulnerabilidades Críticas (3)

| ID | Vulnerabilidad | Ubicación | Impacto | Solución |
|-----|---|---|---|---|
| **CRIT-1** | Client-Admin wildcard '*' | tenant_permissions.py:119 | Data exposure si bypass | Reemplazar con 45 permisos específicos |
| **CRIT-2** | Rol Soporte sin permisos | tenant_permissions.py | Rol inoperativo | Agregar permisos implícitos |
| **CRIT-3** | SuperAdmin sin has_object_permission() | tenant_permissions.py:150 | Acceso sin validar tenant | Implementar defense in depth |

### Vulnerabilidades Altas (8)

| ID | Vulnerabilidad | Severidad | Mitigación |
|-----|---|---|---|
| **ALT-1** | Cajera sin límite de refunds | ALTA | Implementar aprobación de refunds > $1000 |
| **ALT-2** | Manager puede ver TODO los employees | ALTA | Filtrar por tenant en EmployeeViewSet |
| **ALT-3** | Estilista puede ver TODO los sales | ALTA | Filtrar por empleado en SaleViewSet |
| **ALT-4** | Sin rate limiting por rol | ALTA | Implementar rate limiting diferenciado |
| **ALT-5** | Permisos no validados en startup | ALTA | Crear test que valide permission_map |
| **ALT-6** | AllowAny en /api/auth/register/ | ALTA | Implementar invite-only registration |
| **ALT-7** | No hay timeout de sesión | MEDIA | Agregar session timeout (30 min) |
| **ALT-8** | Sin IP whitelist para SuperAdmin | MEDIA | Implementar IP whitelist config |

---

## MATRIZ IDEAL DE PERMISOS

### Matriz Consolidada por Rol

```
PERMISO                    | SuperAdmin | Client-Admin | Manager | Cajera | Estilista | Staff | Utility | Soporte
========================== | ========== | =========== | ======= | ====== | ========= | ===== | ======= | =======
USUARIO
add_user                   |     ✅     |      ✅      |    ❌   |   ❌   |     ❌    |  ❌   |   ❌    |   ❌
change_user                |     ✅     |      ✅      |    ❌   |   ❌   |     ❌    |  ❌   |   ❌    |   ❌
delete_user                |     ✅     |      ✅      |    ❌   |   ❌   |     ❌    |  ❌   |   ❌    |   ❌
view_user                  |     ✅     |      ✅      |    ❌   |   ❌   |     ❌    |  ❌   |   ❌    |   ✅
---------------------------|------------|-------------|--------|--------|-----------|-------|---------|-------
EMPLEADO
add_employee               |     ✅     |      ✅      |    ❌   |   ❌   |     ❌    |  ❌   |   ❌    |   ❌
change_employee            |     ✅     |      ✅      |    ❌   |   ❌   |     ❌    |  ❌   |   ❌    |   ❌
delete_employee            |     ✅     |      ✅      |    ❌   |   ❌   |     ❌    |  ❌   |   ❌    |   ❌
view_employee              |     ✅     |      ✅      |    ✅   |   ✅   |     ✅    |  ✅   |   ✅    |   ✅
view_employee_reports      |     ✅     |      ✅      |    ✅   |   ❌   |     ❌    |  ❌   |   ❌    |   ✅
---------------------------|------------|-------------|--------|--------|-----------|-------|---------|-------
CLIENTE
add_client                 |     ✅     |      ✅      |    ✅   |   ✅   |     ❌    |  ✅   |   ❌    |   ❌
change_client              |     ✅     |      ✅      |    ✅   |   ✅   |     ❌    |  ✅   |   ❌    |   ❌
delete_client              |     ✅     |      ✅      |    ✅   |   ❌   |     ❌    |  ✅   |   ❌    |   ❌
view_client                |     ✅     |      ✅      |    ✅   |   ✅   |     ✅    |  ✅   |   ❌    |   ✅
---------------------------|------------|-------------|--------|--------|-----------|-------|---------|-------
CITA
add_appointment            |     ✅     |      ✅      |    ✅   |   ✅   |     ❌    |  ✅   |   ❌    |   ❌
change_appointment         |     ✅     |      ✅      |    ✅   |   ✅   |     ❌    |  ❌   |   ❌    |   ❌
cancel_appointment         |     ✅     |      ✅      |    ✅   |   ❌   |     ❌    |  ❌   |   ❌    |   ❌
complete_appointment       |     ✅     |      ✅      |    ✅   |   ❌   |     ❌    |  ❌   |   ❌    |   ❌
view_appointment           |     ✅     |      ✅      |    ✅   |   ✅   |     ✅    |  ✅   |   ✅    |   ✅
---------------------------|------------|-------------|--------|--------|-----------|-------|---------|-------
PRODUCTO/INVENTARIO
add_product                |     ✅     |      ✅      |    ❌   |   ❌   |     ❌    |  ❌   |   ❌    |   ❌
change_product             |     ✅     |      ✅      |    ❌   |   ❌   |     ❌    |  ❌   |   ❌    |   ❌
delete_product             |     ✅     |      ✅      |    ❌   |   ❌   |     ❌    |  ❌   |   ❌    |   ❌
view_product               |     ✅     |      ✅      |    ✅   |   ✅   |     ❌    |  ❌   |   ❌    |   ✅
adjust_stock               |     ✅     |      ✅      |    ❌   |   ❌   |     ❌    |  ❌   |   ❌    |   ❌
---------------------------|------------|-------------|--------|--------|-----------|-------|---------|-------
VENTA / POS
add_sale                   |     ✅     |      ✅      |    ❌   |   ✅   |     ❌    |  ❌   |   ❌    |   ❌
change_sale                |     ✅     |      ✅      |    ❌   |   ❌   |     ❌    |  ❌   |   ❌    |   ❌
delete_sale                |     ✅     |      ✅      |    ❌   |   ❌   |     ❌    |  ❌   |   ❌    |   ❌
view_sale                  |     ✅     |      ✅      |    ✅   |   ✅   |     ✅    |  ✅   |   ❌    |   ✅
refund_sale                |     ✅     |      ✅      |    ❌   |  ⚠️*  |     ❌    |  ❌   |   ❌    |   ❌
add_promotion              |     ✅     |      ✅      |    ❌   |   ❌   |     ❌    |  ❌   |   ❌    |   ❌
view_promotion             |     ✅     |      ✅      |    ✅   |   ✅   |     ❌    |  ❌   |   ❌    |   ✅
---------------------------|------------|-------------|--------|--------|-----------|-------|---------|-------
CAJA
add_cashregister           |     ✅     |      ✅      |    ❌   |   ✅   |     ❌    |  ❌   |   ❌    |   ❌
change_cashregister        |     ✅     |      ✅      |    ❌   |   ✅   |     ❌    |  ❌   |   ❌    |   ❌
view_cashregister          |     ✅     |      ✅      |    ✅   |   ✅   |     ❌    |  ❌   |   ❌    |   ✅
---------------------------|------------|-------------|--------|--------|-----------|-------|---------|-------
ASISTENCIA
add_attendancerecord       |     ✅     |      ✅      |    ❌   |   ❌   |     ✅    |  ✅   |   ❌    |   ❌
change_attendancerecord    |     ✅     |      ✅      |    ❌   |   ❌   |     ✅    |  ✅   |   ❌    |   ❌
view_attendancerecord      |     ✅     |      ✅      |    ✅   |   ❌   |     ✅    |  ✅   |   ❌    |   ✅
---------------------------|------------|-------------|--------|--------|-----------|-------|---------|-------
REPORTES
view_sales_reports         |     ✅     |      ✅      |    ✅   |   ❌   |     ❌    |  ❌   |   ❌    |   ✅
view_employee_reports      |     ✅     |      ✅      |    ✅   |   ❌   |     ❌    |  ❌   |   ❌    |   ✅
view_financial_report      |     ✅     |      ✅      |    ❌   |   ❌   |     ❌    |  ❌   |   ❌    |   ❌
view_kpi_dashboard         |     ✅     |      ✅      |    ✅   |   ❌   |     ❌    |  ❌   |   ❌    |   ❌
---------------------------|------------|-------------|--------|--------|-----------|-------|---------|-------
AUDITORÍA
view_audit_log             |     ✅     |      ✅      |    ✅   |   ❌   |     ❌    |  ❌   |   ❌    |   ✅
---------------------------|------------|-------------|--------|--------|-----------|-------|---------|-------
CONFIGURACIÓN
change_tenant_settings     |     ✅     |      ✅      |    ❌   |   ❌   |     ❌    |  ❌   |   ❌    |   ❌
view_tenant_settings       |     ✅     |      ✅      |    ❌   |   ❌   |     ❌    |  ❌   |   ❌    |   ✅

⚠️* = Requiere aprobación de Manager para montos > $1000
```

---

## RIESGOS DE ACCESO CRUZADO (MULTI-TENANT)

### Escenario de Riesgo: Data Leakage Entre Tenants

**RIESGO CRÍTICO**: Un usuario de Salon A acceda a datos de Salon B

### Cómo podría ocurrir:

#### 1. Bug en Middleware (TenantMiddleware)

```python
# apps/tenants_api/middleware.py
def process_request(self, request):
    tenant = self._resolve_tenant(request)  # ← Si falla aquí
    request.tenant = tenant  # Podría ser None
```

**Escenario**:
```python
GET /api/inventory/products/
# Si tenant = None en request

# En ProductViewSet.get_queryset():
def get_queryset(self):
    tenant = getattr(self.request, 'tenant', None)
    if not tenant:
        return Product.objects.none()  # ✅ Protegido

# PERO si ViewSet olvida el filtro:
def get_queryset(self):
    return Product.objects.all()  # ❌ TODOS los productos
```

**Mitigación**: ✅ Actualmente hay protección `objects.none()` por defecto

#### 2. Bypass de URL Encoding

```python
# GET /api/inventory/products/?tenant_id=2

# En ViewSet:
def get_queryset(self):
    return Product.objects.filter(tenant__id=self.request.query_params.get('tenant_id'))
    # ❌ VULNERABLE - Usuario puede cambiar tenant_id

# CORRECTO:
def get_queryset(self):
    return Product.objects.filter(tenant=self.request.tenant)
    # ✅ Usa tenant del request, no del query param
```

**Mitigación**: ✅ Sistema usa `request.tenant`, no query_params

#### 3. JWT Token Hijacking

```python
# Si usuario de Salon A roba JWT de usuario de Salon B
# Y hace: GET /api/inventory/products/ con token robado
# ¿Qué pasa?

# En middleware:
def process_request(self, request):
    # Extrae user del JWT
    user_from_jwt = authenticate(token)
    request.user = user_from_jwt
    
    # Busca tenant del usuario
    request.tenant = user_from_jwt.tenant
    # ✅ Se usa tenant DEL USUARIO, no del query param
```

**Mitigación**: ✅ Correcto - Se usa tenant del usuario

#### 4. Serializer Exposing Tenant Data

```python
# En ProductSerializer
fields = '__all__'  # ❌ Podría exponer tenant_id a usuario

# En PromotionSerializer
fields = ['id', 'name', 'discount_value', 'tenant']  # ❌ Expone tenant
```

**Mitigación**: ⚠️ Verificado en ProductSerializer (línea 33)
```python
fields = ['id', 'name', 'sku', 'barcode', 'price', 'stock', ...]
# ✅ NO incluye 'tenant'
```

#### 5. SuperAdmin Bypass en Queryset

```python
# En ViewSet:
def get_queryset(self):
    if self.request.user.is_superuser:
        return Product.objects.all()  # ✅ Correcto para admin
    return Product.objects.filter(tenant=self.request.tenant)
```

**¿Es seguro?** Depende:
- ✅ Si SuperAdmin DEBERÍA ver todo
- ⚠️ Si SuperAdmin hace audit, debería logearse
- ⚠️ Si SuperAdmin es comprometido, accede a TODO

**Mitigación**: Agregar `has_object_permission()` (CRÍTICA #3)

---

### Test Manual de Acceso Cruzado

#### Test 1: Cambiar Tenant en Request Manualmente

```bash
# 1. Login como Usuario A (Salon A)
TOKEN_A=$(curl -X POST /api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user_a@salon_a.com", "password":"pass"}' \
  | jq -r '.access')

# 2. Ver su tenant
curl -H "Authorization: Bearer $TOKEN_A" /api/tenants/me/
# Retorna: {"id": 1, "name": "Salon A"}

# 3. Intentar acceder a datos de Salon B (tenant_id=2)
# INTENTO 1: Via URL (debería estar protegido)
curl -H "Authorization: Bearer $TOKEN_A" '/api/inventory/products/?tenant_id=2'
# Debería retornar: 403 o [] (productos de su tenant)

# INTENTO 2: Cambiar token.tenant (imposible - es JWT firmado)
# JWT está firmado, no se puede modificar sin secret
```

#### Test 2: Verificar Queryset Filtering

```python
# En Django Shell:

from apps.inventory_api.models import Product
from apps.tenants_api.models import Tenant
from apps.auth_api.models import User

tenant_a = Tenant.objects.get(name="Salon A")
tenant_b = Tenant.objects.get(name="Salon B")

user_a = User.objects.get(email="user_a@salon_a.com")

# Crear productos en ambos tenants
Product.objects.create(name="Prod A1", tenant=tenant_a)
Product.objects.create(name="Prod B1", tenant=tenant_b)

# Simular request de usuario A
class FakeRequest:
    user = user_a
    tenant = tenant_a

# ProductViewSet.get_queryset()
products = Product.objects.filter(tenant=FakeRequest.tenant)
print(products)  # Debería: [Prod A1] (no Prod B1)
```

#### Test 3: Verificar JWT Decoding

```bash
# Extraer JWT y decodificar (sin secret, solo header+payload)
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Decodificar (base64):
echo "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" | base64 -d
# {"alg":"HS256","typ":"JWT"}

# ¿Se puede modificar sin secret? NO
# JWT está firmado. Si lo modificas, signature no valida.
```

---

## VALIDACIONES PROPUESTAS

### Checklist de Seguridad RBAC

```
ANTES DE LANZAR PRODUCCIÓN:

[ ] 1. ROLES DEFINIDOS
    [ ] SuperAdmin - validado
    [ ] Client-Admin - 45 permisos específicos (no wildcard)
    [ ] Manager - 15 permisos
    [ ] Cajera - 15 permisos (incluyendo view_product, view_promotion)
    [ ] Estilista - 8 permisos
    [ ] Client-Staff - 8 permisos
    [ ] Utility - 3 permisos
    [ ] Soporte - 12 permisos

[ ] 2. ENDPOINT SECURITY
    [ ] Todos los ViewSets tienen permission_map completo
    [ ] Todos los @action tienen permisos asociados
    [ ] No hay @api_view sin @permission_classes
    [ ] Todo endpoint expone solo campos que rol puede ver

[ ] 3. MULTI-TENANT ISOLATION
    [ ] Todos los ViewSets filtran por tenant en get_queryset()
    [ ] Fallback a objects.none() si no hay tenant
    [ ] Serializers no exponen tenant_id o foreign_key a otros tenants
    [ ] SuperAdmin tiene has_object_permission() implementado

[ ] 4. PERMISSION MAP VALIDATION
    [ ] Los codenames en permission_map existen en BD (Django Permission)
    [ ] Los codenames son consistentes entre ViewSets
    [ ] No hay typos en permission_map (ej: 'vew_product' vs 'view_product')

[ ] 5. RATE LIMITING
    [ ] GlobalRateThrottle: 1000 req/hora para usuarios
    [ ] UserRateThrottle: 100 req/minuto por usuario
    [ ] SuperAdmin: 10.000 req/hora (mayor límite)
    [ ] Endpoints públicos: 50 req/minuto

[ ] 6. SESSION MANAGEMENT
    [ ] JWT timeout: 30 minutos
    [ ] Refresh timeout: 7 días
    [ ] Logout invalida token
    [ ] IP whitelisting para SuperAdmin (si aplica)

[ ] 7. AUDIT LOGGING
    [ ] Todo cambio de CRUD es loggeado
    [ ] Todo acceso a datos sensibles es loggeado
    [ ] Log incluye: usuario, acción, tabla, valores antes/después, timestamp, IP
    [ ] Logs son inmutables (no se pueden borrar)

[ ] 8. FIELD-LEVEL SECURITY
    [ ] Salarios NO se exponen a Cajera/Estilista
    [ ] Costos internos NO se exponen a Cajera
    [ ] Márgenes NO se exponen a roles operacionales
    [ ] Datos bancarios NO se exponen fuera de Client-Admin

[ ] 9. ACTION-LEVEL SECURITY
    [ ] delete_* no se puede hacer sin DUAL APPROVAL (para críticos)
    [ ] change_salary requiere Manager approval
    [ ] refund > $1000 requiere Manager approval
    [ ] change_tenant requiere SuperAdmin

[ ] 10. FRONTEND-BACKEND ALIGNMENT
    [ ] Botones que están ocultos en frontend usan permission_classes en backend
    [ ] Si usuario manipula JS, backend sigue rechazando con 403
    [ ] No confiar en frontend para seguridad
```

---

## PLAN DE CORRECCIONES

### FASE 1: CRÍTICA (HOY - 2 horas)

```python
# 1. Reemplazar wildcard en Client-Admin
# Archivo: apps/core/tenant_permissions.py

OLD:
'Client-Admin': '*',

NEW:
'Client-Admin': [
    'add_user', 'change_user', 'delete_user', 'view_user',
    'add_employee', 'change_employee', 'delete_employee', 'view_employee',
    'add_client', 'change_client', 'delete_client', 'view_client',
    'add_service', 'change_service', 'delete_service', 'view_service',
    'add_product', 'change_product', 'delete_product', 'view_product',
    'add_appointment', 'change_appointment', 'cancel_appointment',
    'complete_appointment', 'view_appointment',
    'add_sale', 'change_sale', 'delete_sale', 'view_sale', 'refund_sale',
    'add_cashregister', 'change_cashregister', 'view_cashregister',
    'add_promotion', 'change_promotion', 'delete_promotion', 'view_promotion',
    'view_sales_report', 'view_employee_report', 'view_financial_report',
    'view_kpi_dashboard', 'adjust_stock', 'view_supplier',
    'change_tenant_settings', 'view_tenant_settings',
    'view_audit_log', 'view_role', 'change_role_permissions',
    'view_invoice', 'view_payment',
],
```

#### 2. Agregar rol Soporte

```python
# Archivo: apps/core/tenant_permissions.py

'Soporte': [
    'view_user', 'view_employee', 'view_client', 'view_appointment',
    'view_sale', 'view_product', 'view_service', 'view_promotion',
    'view_cashregister', 'view_audit_log', 'view_tenant_settings',
    'reset_user_password', 'unlock_user_account',
    'view_employee_reports', 'view_sales_reports',
],
```

#### 3. Implementar has_object_permission()

```python
# Archivo: apps/core/tenant_permissions.py

class TenantPermissionByAction(BasePermission):
    def has_permission(self, request, view):
        # ... código existente ...
        pass
    
    def has_object_permission(self, request, view, obj):
        """Validación de objeto (defense in depth)"""
        if request.user.is_superuser:
            # SuperAdmin puede acceder, pero debería logearse
            from apps.audit_api.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action='SUPERADMIN_ACCESS',
                description=f'SuperAdmin accedió a {obj.__class__.__name__} {obj.id}',
                source='SYSTEM'
            )
            return True
        
        # Usuario normal: validar tenant
        tenant = resolve_request_tenant(request)
        if hasattr(obj, 'tenant'):
            return obj.tenant == tenant
        
        # Si objeto no tiene tenant, denegar (seguridad default)
        return False
```

### FASE 2: ALTA PRIORIDAD (Esta semana - 8 horas)

```
[ ] Crear test suite RBAC matriz completa
    - Test que cada rol SOLO vea lo que le corresponde
    - Test que cada rol NO vea lo que no le corresponde
    - Test de acceso cruzado entre tenants

[ ] Validar permission_map en startup
    - Verificar que todos los codenames existan en Django Permission
    - Alertar si hay typos
    - Crear management command que list todos los permisos

[ ] Implementar rate limiting diferenciado
    - SuperAdmin: 10k req/hora
    - Client-Admin: 5k req/hora
    - Manager: 1k req/hora
    - Otros: 500 req/hora

[ ] Agregar 2FA para SuperAdmin (obligatorio)
    - TOTP (Google Authenticator)
    - SMS como backup

[ ] Crear dashboard de auditoría RBAC
    - Ver cambios de permisos
    - Ver accesos por rol
    - Detectar anomalías
```

### FASE 3: MANTENIMIENTO (Mensual)

```
[ ] Auditar cambios de roles (una vez por mes)
[ ] Revisar logs de acceso cruzado
[ ] Prueba de penetración RBAC (cada 3 meses)
[ ] Actualizar matriz de permisos según nuevas features
[ ] Capacitación a admin sobre seguridad RBAC
```

---

## RECOMENDACIONES CTO

### Si yo fuera CTO, estos serían los cambios NOW:

#### 1. **Eliminar Permiso Wildcard** (CRÍTICO)

**Por qué**: El wildcard '*' es el error más peligroso en sistemas RBAC. Viola el principio de "Least Privilege" que es la base de RBAC seguro.

**Impacto**: Si hay un bug en el middleware o en queryset filtering, un Client-Admin accede a TODO.

**Fix**: Línea única, 5 minutos.

```python
# ANTES: Línea 119
'Client-Admin': '*',

# DESPUÉS:
'Client-Admin': [
    # 45 permisos específicos
    # (ver arriba en FASE 1)
],
```

---

#### 2. **Implementar Defense in Depth** (CRÍTICO)

**Actual**: Solo middleware + permission_classes validan tenant.

**Problema**: Si middleware falla, objetos quedan expuestos.

**Recomendación**: Agregar `has_object_permission()` en CADA ViewSet.

```python
# En TenantPermissionByAction:
def has_object_permission(self, request, view, obj):
    # Validar que objeto pertenece al tenant del user
    if request.user.is_superuser:
        return True  # pero logearlo
    
    if hasattr(obj, 'tenant'):
        return obj.tenant == request.tenant
    
    return False  # Fail-secure
```

---

#### 3. **Crear Matriz de Permisos Versionada** (IMPORTANTE)

**Problema**: Hoy está en código hardcoded. Si cambias un rol, no hay auditoría de cambio.

**Recomendación**: Crear tabla `RolePermissionSnapshot` que guarde historia de cambios.

```python
class RolePermissionSnapshot(models.Model):
    role = ForeignKey(Role)
    permissions_json = JSONField()  # Snapshot de permisos en ese momento
    changed_by = ForeignKey(User)
    changed_at = DateTimeField(auto_now_add=True)
    change_reason = CharField(max_length=500)
    
    class Meta:
        verbose_name_plural = 'Role Permission Snapshots'
```

**Beneficio**: Auditoria de cambios, rollback fácil, detectar cambios no autorizados.

---

#### 4. **Crear Role Templates Reutilizables** (IMPORTANTE)

**Problema**: Hoy está todo hardcodeado. Agregar nuevo rol requiere modificar código.

**Recomendación**: Role templates en DB.

```python
class RoleTemplate(models.Model):
    """Plantilla reutilizable de roles"""
    name = CharField(max_length=100)  # ej: "POS_OPERATOR"
    description = TextField()
    permissions = ManyToManyField(Permission)
    
    def create_role_from_template(self, tenant, custom_name=None):
        """Crear un rol instanciando la plantilla"""
        role_name = custom_name or self.name
        role = Role.objects.create(
            name=role_name,
            scope='TENANT',
            description=self.description
        )
        role.permissions.set(self.permissions.all())
        return role
```

**Beneficio**: Nuevas empresas usan templates predefinidos, reducir errores.

---

#### 5. **Implementar Permission Bundles** (IMPORTANTE)

**Problema**: Los permisos están dispersos. Un Manager tiene 13 permisos, un Client-Admin tiene 45. No hay lógica clara.

**Recomendación**: Agrupar permisos en "bundles" temáticos.

```python
PERMISSION_BUNDLES = {
    'POS_FULL': [
        'add_sale', 'change_sale', 'delete_sale', 'view_sale',
        'add_cashregister', 'change_cashregister', 'view_cashregister',
        'add_promotion', 'change_promotion', 'delete_promotion', 'view_promotion',
        'view_product', 'view_client',
    ],
    'POS_OPERATOR': [
        'add_sale', 'view_sale', 'view_promotion', 'view_product', 'view_client',
    ],
    'REPORTS_ANALYTICS': [
        'view_sales_report', 'view_employee_report', 'view_kpi_dashboard',
        'view_financial_report',
    ],
    'HR_MANAGEMENT': [
        'add_employee', 'change_employee', 'delete_employee', 'view_employee',
        'view_employee_reports',
    ],
}

# Luego:
'Manager': expand_bundle('REPORTS_ANALYTICS') + expand_bundle('APPOINTMENT_MANAGEMENT'),
```

**Beneficio**: Reutilización, menos errores, fácil de mantener.

---

#### 6. **Crear Integration Tests para RBAC** (CRÍTICO)

**Hoy**: No hay tests que validen que cada rol SOLO puede hacer lo que le corresponde.

**Recomendación**: Test suite que pruebe cada rol vs cada endpoint.

```python
# tests/test_rbac_matrix.py

class RBACMatrixTest(TestCase):
    def test_cajera_can_view_products(self):
        cajera = self._create_user_with_role('Cajera')
        response = self.client.get('/api/inventory/products/', 
                                  HTTP_AUTHORIZATION=f'Bearer {cajera.token}')
        self.assertEqual(response.status_code, 200)
    
    def test_cajera_cannot_delete_products(self):
        cajera = self._create_user_with_role('Cajera')
        product = Product.objects.create(...)
        response = self.client.delete(f'/api/inventory/products/{product.id}/', 
                                      HTTP_AUTHORIZATION=f'Bearer {cajera.token}')
        self.assertEqual(response.status_code, 403)
    
    def test_estilista_cannot_view_salaries(self):
        estilista = self._create_user_with_role('Estilista')
        response = self.client.get('/api/employees/payroll/', 
                                   HTTP_AUTHORIZATION=f'Bearer {estilista.token}')
        self.assertEqual(response.status_code, 403)

# Ejecutar: pytest tests/test_rbac_matrix.py
```

**Beneficio**: Detectar regresiones de permisos automáticamente.

---

#### 7. **Implementar Audit Logging Inmutable** (IMPORTANTE)

**Hoy**: Audit logs pueden teóricamente ser modificados.

**Recomendación**: Hash chain similar a blockchain.

```python
class AuditLog(models.Model):
    # ... campos actuales ...
    
    previous_log_hash = CharField(max_length=256, null=True)
    current_log_hash = CharField(max_length=256)
    
    def save(self, *args, **kwargs):
        # Calcular hash basado en datos + hash anterior
        if self.pk:
            previous = AuditLog.objects.get(pk=self.pk)
            self.previous_log_hash = previous.current_log_hash
        
        # Crear hash
        data_to_hash = f"{self.user_id}{self.action}{self.timestamp}{self.previous_log_hash}"
        self.current_log_hash = hashlib.sha256(data_to_hash.encode()).hexdigest()
        
        super().save(*args, **kwargs)
    
    @staticmethod
    def verify_chain():
        """Verificar que la cadena de hashes es válida"""
        logs = AuditLog.objects.all().order_by('id')
        previous_hash = None
        
        for log in logs:
            if log.previous_log_hash != previous_hash:
                return False  # Cadena rota = tampering detectado
            previous_hash = log.current_log_hash
        
        return True
```

**Beneficio**: Detect tampering automáticamente, cumple compliance.

---

#### 8. **Crear Feature Flags para Roles** (IMPORTANTE)

**Problema**: Un rol nuevo no debería poder acceder a features de nueva versión.

**Recomendación**: Integrar feature flags con RBAC.

```python
ROLE_FEATURE_FLAGS = {
    'Manager': ['reports.v2', 'appointments.calendar_view'],
    'Cajera': ['pos.v1'],
    'Estilista': ['appointments.scheduler'],
    'SuperAdmin': '*',  # Acceso a todo
}

# En ViewSet:
def is_feature_enabled_for_role(role, feature):
    flags = ROLE_FEATURE_FLAGS.get(role, [])
    if flags == '*':
        return True
    return feature in flags
```

---

#### 9. **Documentar RBAC Como Código** (IMPORTANTE)

**Problema**: RBAC solo existe en código. No hay documentación clara.

**Recomendación**: Generar documentación automáticamente.

```python
# management/commands/document_rbac.py

def generate_rbac_docs():
    """Generar documentación de RBAC desde código"""
    
    output = "# RBAC Matrix\n\n"
    
    for role_name, permissions in ROLE_IMPLICIT_PERMISSIONS.items():
        output += f"## {role_name}\n\n"
        output += "**Permisos**:\n"
        for perm in permissions:
            output += f"- {perm}\n"
        output += "\n"
    
    with open('docs/RBAC_MATRIX_GENERATED.md', 'w') as f:
        f.write(output)

# python manage.py document_rbac
```

---

### Summary: Las 3 Cosas que Haría Ahora Mismo

```
1. REEMPLAZAR WILDCARD '*' EN CLIENT-ADMIN
   Tiempo: 5 minutos
   Riesgo: CRÍTICO si no se hace
   
2. IMPLEMENTAR has_object_permission() EN TENANTPERMISSIONBYACTION
   Tiempo: 30 minutos
   Riesgo: ALTO - Defense in depth

3. CREAR TEST SUITE RBAC MATRIX
   Tiempo: 4 horas
   Beneficio: Evitar regresiones de permisos
```

---

## RESUMEN FINAL

### ✅ Lo que está bien:

1. ✅ Multi-tenant aislado correctamente
2. ✅ Jerarquía de roles clara
3. ✅ Permission classes centralizadas y reutilizables
4. ✅ Audit logging implementado
5. ✅ Endpoints públicos identificados

### 🚨 Lo que necesita correción (Prioridad):

| Prioridad | Item |
|-----------|------|
| **CRÍTICA** | Reemplazar wildcard en Client-Admin |
| **CRÍTICA** | Agregar rol Soporte a permisos implícitos |
| **CRÍTICA** | Implementar has_object_permission() |
| ALTA | Crear test suite RBAC matrix |
| ALTA | Validar permission_map en startup |
| ALTA | Rate limiting diferenciado por rol |
| MEDIA | 2FA para SuperAdmin |
| MEDIA | Session timeout |
| MEDIA | Audit logging inmutable |

### 🎯 Próximo Paso:

**Implementar FASE 1 (Crítica)** antes de lanzar a producción.

Estimado: 2-3 horas
Impacto de seguridad: **ALTÍSIMO**

---

**Documento generado**: 2026-04-26  
**Clasificación**: CONFIDENCIAL  
**Auditor**: Senior Django + DRF RBAC Specialist
