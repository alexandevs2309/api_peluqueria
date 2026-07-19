# 🚨 ANÁLISIS DE RIESGOS DE SEGURIDAD MULTI-TENANT

**Sistema:** Django Multi-Tenant SaaS con JWT
**Fecha:** 2024
**Criticidad:** ALTA

---

## 🔴 RIESGO 1: ESCALADA HORIZONTAL (TENANT HOPPING)

### ⚠️ SEVERIDAD: CRÍTICA (9/10)

### Vectores de Ataque Identificados:

#### 1.1 Login sin tenant_subdomain

**Ubicación:** `apps/auth_api/serializers.py` línea 48-56

```python
def validate(self, data):
    if tenant_subdomain:
        tenant = Tenant.objects.get(subdomain=tenant_subdomain)
        user = User.objects.get(email=email, tenant=tenant)
    else:
        user = User.objects.filter(email=email).first()  # ⚠️ PELIGRO
        tenant = user.tenant
```

**Escenario de Ataque:**
```bash
# Paso 1: Atacante descubre email de empleado de Tenant A
POST /api/auth/login/
{
  "email": "empleado@mail.com",
  "password": "password123"
  # ⚠️ Sin tenant_subdomain
}

# Sistema retorna PRIMER usuario con ese email
# Si existe en múltiples tenants, accede al primero encontrado
```

**Impacto:**
- ✅ Acceso a datos de otro tenant
- ✅ Bypass de aislamiento multi-tenant
- ✅ Violación de privacidad de datos

**Estado Actual:** 🔴 VULNERABLE

**Mitigación Actual:**
- Middleware valida tenant en JWT después del login
- Pero el JWT ya fue generado con tenant incorrecto

**Prueba de Concepto:**
```python
# Crear usuarios duplicados en diferentes tenants
User.objects.create(email="test@mail.com", tenant=tenant_a, password="pass123")
User.objects.create(email="test@mail.com", tenant=tenant_b, password="pass123")

# Login sin tenant_subdomain
response = client.post('/api/auth/login/', {
    'email': 'test@mail.com',
    'password': 'pass123'
})

# ⚠️ Accede al primer tenant encontrado (orden no determinístico)
```

---

#### 1.2 Manipulación de JWT Claims

**Ubicación:** `apps/tenants_api/middleware.py` línea 50-65

```python
# Middleware extrae tenant_id del JWT
tenant_id = validated_token.get('tenant_id')
if tenant_id:
    tenant = Tenant.objects.get(id=tenant_id)
    request.tenant = tenant
```

**Escenario de Ataque:**
```bash
# Paso 1: Usuario legítimo obtiene JWT de Tenant A
{
  "user_id": 123,
  "tenant_id": 1,  # Tenant A
  "tenant_subdomain": "barberia-a"
}

# Paso 2: Atacante intenta modificar JWT (firmado, no funciona)
# Pero... ¿qué pasa si el atacante tiene acceso a SECRET_KEY?
```

**Estado Actual:** 🟢 PROTEGIDO (JWT firmado con HS256)

**Pero:**
- Si SECRET_KEY se compromete → Escalada horizontal total
- No hay rotación de SECRET_KEY
- No hay detección de JWT manipulados

---

#### 1.3 Reutilización de Email entre Tenants

**Ubicación:** `apps/auth_api/models.py` línea 30

```python
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, max_length=255)  # ⚠️ GLOBAL UNIQUE
```

**Estado Actual:** 🔴 VULNERABLE

**Problema:**
- Email es UNIQUE a nivel global
- NO permite mismo email en diferentes tenants
- Limita casos de uso legítimos (ej: franquicias)

**Escenario Real:**
```python
# Tenant A: Barbería en Santo Domingo
User.objects.create(email="juan@gmail.com", tenant=tenant_a)

# Tenant B: Barbería en Santiago
User.objects.create(email="juan@gmail.com", tenant=tenant_b)
# ❌ IntegrityError: duplicate key value violates unique constraint
```

**Impacto:**
- ❌ Imposible tener mismo email en múltiples tenants
- ❌ Limita escalabilidad del SaaS
- ⚠️ Pero PREVIENE escalada horizontal por email duplicado

**Recomendación:** Cambiar a `unique_together=['email', 'tenant']`

---

#### 1.4 Bypass de Tenant via QuerySet

**Ubicación:** `apps/tenants_api/mixins.py` línea 14-30

```python
def get_queryset(self):
    queryset = super().get_queryset()
    user = self.request.user
    
    # SuperAdmin puede ver todo
    if user.is_superuser:
        return queryset  # ⚠️ Sin filtro
    
    # Usar tenant del middleware
    tenant = getattr(self.request, 'tenant', None)
    if tenant:
        return queryset.filter(tenant=tenant)
```

**Estado Actual:** 🟢 PROTEGIDO

**Validación:**
- ✅ Todos los ViewSets heredan de TenantFilterMixin
- ✅ Filtro automático por tenant
- ✅ SuperAdmin explícitamente permitido

**Pero falta validación en:**
```python
# Endpoints que NO usan TenantFilterMixin
UserViewSet  # ⚠️ Implementa su propio get_queryset
```

---

## 🔴 RIESGO 2: ESCALADA VERTICAL (PRIVILEGE ESCALATION)

### ⚠️ SEVERIDAD: CRÍTICA (10/10)

#### 2.1 ClientAdmin puede crear SuperAdmin

**Ubicación:** `apps/auth_api/views.py` línea 680-690

```python
def create(self, request, *args, **kwargs):
    # ...
    if 'role' in request.data:
        role_name = request.data.get('role')
        user.role = role_name  # ⚠️ SIN VALIDACIÓN
        user.save()
```

**Escenario de Ataque:**
```bash
# ClientAdmin autenticado
POST /api/auth/users/
{
  "email": "hacker@mail.com",
  "full_name": "Hacker",
  "password": "pass123",
  "role": "SuperAdmin"  # ⚠️ Sin restricción
}

# Sistema crea usuario con rol SuperAdmin
# Atacante ahora tiene acceso total al sistema
```

**Estado Actual:** 🔴 VULNERABLE

**Prueba de Concepto:**
```python
# Login como ClientAdmin
client.login(email="admin@tenant-a.com", password="pass")

# Crear usuario con rol SuperAdmin
response = client.post('/api/auth/users/', {
    'email': 'escalated@mail.com',
    'password': 'pass123',
    'role': 'SuperAdmin'
})

# ✅ Usuario creado con privilegios de SuperAdmin
# ✅ Puede acceder a todos los tenants
# ✅ Puede modificar configuración global
```

**Impacto:**
- ✅ Acceso total al sistema
- ✅ Acceso a todos los tenants
- ✅ Modificación de configuración global
- ✅ Eliminación de datos de cualquier tenant

---

#### 2.2 Modificación de is_superuser

**Ubicación:** `apps/auth_api/serializers.py` línea 103-130

```python
class EmployeeUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'full_name', 'phone', 'password', 'tenant', 'role', 'is_active']
        # ⚠️ is_superuser NO está en fields, pero...
```

**Escenario de Ataque:**
```bash
POST /api/auth/users/
{
  "email": "hacker@mail.com",
  "is_superuser": true  # ⚠️ Intentar inyectar
}
```

**Estado Actual:** 🟢 PROTEGIDO

**Razón:**
- `is_superuser` no está en `fields` del serializer
- Django ignora campos no declarados
- Pero falta validación explícita

---

#### 2.3 Modificación de Tenant de Usuario

**Ubicación:** `apps/auth_api/views.py` línea 700-720

```python
def update(self, request, *args, **kwargs):
    # ...
    if 'role' in request.data:
        role_name = request.data.get('role')
        user.role = role_name  # ⚠️ Sin validación
        user.save()
```

**Escenario de Ataque:**
```bash
# ClientAdmin de Tenant A
PATCH /api/auth/users/123/
{
  "tenant": 2  # ⚠️ Intentar cambiar a Tenant B
}
```

**Estado Actual:** 🟡 PARCIALMENTE PROTEGIDO

**Validación:**
```python
# En EmployeeUserSerializer.update()
tenant = validated_data.pop('tenant', None)
if tenant is not None:
    instance.tenant = tenant  # ⚠️ Permite cambio
```

**Problema:**
- ClientAdmin puede cambiar tenant de sus usuarios
- Pero solo si tiene acceso al ID del otro tenant
- Middleware valida después, pero usuario ya fue modificado

---

## 🔴 RIESGO 3: BYPASS DE TENANT VIA HEADER

### ⚠️ SEVERIDAD: MEDIA (6/10)

#### 3.1 Manipulación de HTTP_HOST

**Ubicación:** `apps/auth_api/serializers.py` línea 44

```python
tenant_subdomain = request.META.get('HTTP_HOST', '').split('.')[0]
```

**Escenario de Ataque:**
```bash
# Atacante manipula header Host
POST /api/auth/login/
Host: tenant-b.app.com
{
  "email": "empleado@tenant-a.com",
  "password": "pass123"
}

# Sistema intenta autenticar en tenant-b
# Falla porque usuario no existe en tenant-b
```

**Estado Actual:** 🟢 PROTEGIDO

**Razón:**
- Login valida que usuario pertenezca al tenant
- Si no existe en ese tenant, falla autenticación

---

#### 3.2 Manipulación de Authorization Header

**Ubicación:** `apps/tenants_api/middleware.py` línea 50

```python
auth_header = request.META.get('HTTP_AUTHORIZATION', '')
if auth_header.startswith('Bearer '):
    token_str = auth_header.split(' ')[1]
```

**Escenario de Ataque:**
```bash
# Atacante intenta inyectar JWT de otro tenant
GET /api/employees/
Authorization: Bearer eyJ...  # JWT de Tenant B
```

**Estado Actual:** 🟢 PROTEGIDO

**Razón:**
- JWT está firmado con SECRET_KEY
- Middleware valida firma antes de extraer claims
- Si JWT es inválido, rechaza request

**Pero:**
- Si atacante obtiene JWT válido de otro tenant → Acceso total
- No hay validación de que JWT corresponda al usuario actual

---

## 🔴 RIESGO 4: REUTILIZACIÓN DE EMAIL

### ⚠️ SEVERIDAD: ALTA (8/10)

#### 4.1 Constraint de Email Único Global

**Ubicación:** `apps/auth_api/models.py` línea 30

```python
email = models.EmailField(unique=True, max_length=255)
```

**Problema:**
```python
# Escenario legítimo: Franquicia con múltiples locales
# Local A: juan@gmail.com es gerente
# Local B: juan@gmail.com es estilista

# ❌ Imposible crear segundo usuario
User.objects.create(email="juan@gmail.com", tenant=local_b)
# IntegrityError: duplicate key value violates unique constraint
```

**Impacto:**
- ❌ Limita casos de uso reales
- ❌ Fuerza emails únicos globalmente
- ⚠️ Pero PREVIENE ataques de suplantación

**Recomendación:**
```python
class User(AbstractBaseUser):
    email = models.EmailField(max_length=255)  # Remover unique=True
    
    class Meta:
        unique_together = [['email', 'tenant']]  # Único por tenant
        indexes = [
            models.Index(fields=['email', 'tenant']),
        ]
```

---

#### 4.2 Validación de Email en Login

**Ubicación:** `apps/auth_api/serializers.py` línea 52

```python
user = User.objects.filter(email=email).first()
```

**Problema:**
- Si se permite email duplicado entre tenants
- `.first()` retorna resultado no determinístico
- Puede autenticar en tenant incorrecto

**Solución:**
```python
# SIEMPRE requerir tenant_subdomain
if not tenant_subdomain:
    raise ValidationError('tenant_subdomain es requerido')

tenant = Tenant.objects.get(subdomain=tenant_subdomain)
user = User.objects.get(email=email, tenant=tenant)
```

---

## 📊 RESUMEN DE VULNERABILIDADES

| Riesgo | Severidad | Estado | Explotable |
|--------|-----------|--------|------------|
| **Login sin tenant** | 🔴 Crítica | Vulnerable | ✅ Sí |
| **Escalada a SuperAdmin** | 🔴 Crítica | Vulnerable | ✅ Sí |
| **Email único global** | 🟠 Alta | Limitante | ⚠️ Parcial |
| **Manipulación JWT** | 🟢 Baja | Protegido | ❌ No |
| **Bypass QuerySet** | 🟢 Baja | Protegido | ❌ No |
| **Header manipulation** | 🟢 Baja | Protegido | ❌ No |

---

## 🛡️ MITIGACIONES RECOMENDADAS

### Prioridad 1 (CRÍTICO - Implementar YA)

#### 1. Forzar tenant_subdomain en Login

```python
class LoginSerializer(serializers.Serializer):
    tenant_subdomain = serializers.CharField(required=True)  # ⚠️ OBLIGATORIO
    
    def validate(self, data):
        tenant_subdomain = data.get('tenant_subdomain')
        
        if not tenant_subdomain:
            raise ValidationError({
                'tenant_subdomain': 'Este campo es obligatorio'
            })
        
        try:
            tenant = Tenant.objects.get(subdomain=tenant_subdomain)
            user = User.objects.get(
                email=data['email'],
                tenant=tenant  # ⚠️ Filtro estricto
            )
        except (Tenant.DoesNotExist, User.DoesNotExist):
            raise ValidationError('Credenciales inválidas')
        
        if not user.check_password(data['password']):
            raise ValidationError('Credenciales inválidas')
        
        data['user'] = user
        data['tenant'] = tenant
        return data
```

#### 2. Validar Rol en Creación de Usuario

```python
ROLE_HIERARCHY = {
    'SuperAdmin': ['SuperAdmin', 'Client-Admin', 'Client-Staff'],
    'Client-Admin': ['Client-Staff', 'Estilista', 'Cajera', 'Manager'],
    'Client-Staff': []  # No puede crear usuarios
}

class UserViewSet(viewsets.ModelViewSet):
    def create(self, request, *args, **kwargs):
        requested_role = request.data.get('role')
        creator_role = request.user.role
        
        # Validar jerarquía de roles
        allowed_roles = ROLE_HIERARCHY.get(creator_role, [])
        if requested_role not in allowed_roles:
            return Response({
                'error': 'No puedes asignar ese rol',
                'your_role': creator_role,
                'allowed_roles': allowed_roles
            }, status=403)
        
        # Prevenir creación de SuperAdmin
        if requested_role == 'SuperAdmin' and not request.user.is_superuser:
            return Response({
                'error': 'Solo SuperAdmin puede crear SuperAdmin'
            }, status=403)
        
        # Continuar con creación...
```

#### 3. Cambiar Email a Unique por Tenant

```python
# Migration
class Migration(migrations.Migration):
    operations = [
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(max_length=255),  # Remover unique=True
        ),
        migrations.AlterUniqueTogether(
            name='user',
            unique_together={('email', 'tenant')},
        ),
    ]
```

### Prioridad 2 (ALTO - Implementar esta semana)

#### 4. Validar Tenant en JWT vs User

```python
class StrictTenantMiddleware:
    def process_request(self, request):
        if not request.user.is_authenticated:
            return None
        
        # Extraer tenant del JWT
        token_tenant_id = request.auth.get('tenant_id') if request.auth else None
        
        # Validar coincidencia
        if token_tenant_id:
            if request.user.tenant_id != token_tenant_id:
                return JsonResponse({
                    'error': 'TENANT_MISMATCH',
                    'message': 'Token no corresponde al usuario',
                    'expected_tenant': request.user.tenant_id,
                    'token_tenant': token_tenant_id
                }, status=403)
        
        return None
```

#### 5. Auditar Cambios de Rol

```python
from django.db.models.signals import pre_save
from django.dispatch import receiver

@receiver(pre_save, sender=User)
def audit_role_change(sender, instance, **kwargs):
    if instance.pk:
        old_instance = User.objects.get(pk=instance.pk)
        if old_instance.role != instance.role:
            # Log cambio de rol
            AdminActionLog.objects.create(
                user=instance,
                action=f'Role changed from {old_instance.role} to {instance.role}',
                ip_address='system',
                user_agent='system'
            )
            
            # Alertar si se crea SuperAdmin
            if instance.role == 'SuperAdmin':
                send_security_alert.delay(
                    f'SECURITY ALERT: User {instance.email} promoted to SuperAdmin'
                )
```

### Prioridad 3 (MEDIO - Implementar este mes)

#### 6. Rate Limiting por Tenant

```python
from django_ratelimit.decorators import ratelimit

class LoginView(APIView):
    @ratelimit(key='user_or_ip', rate='5/m', method='POST')
    @ratelimit(key='header:tenant-subdomain', rate='20/m', method='POST')
    def post(self, request):
        # Login logic...
```

#### 7. Rotación de SECRET_KEY

```python
# settings.py
SIMPLE_JWT = {
    'SIGNING_KEY': env('JWT_SECRET_KEY'),  # Separado de SECRET_KEY
    'ALGORITHM': 'HS256',
    'ROTATE_REFRESH_TOKENS': True,
}

# Implementar rotación mensual de JWT_SECRET_KEY
# Invalidar todos los tokens al rotar
```

---

## 🧪 TESTS DE SEGURIDAD RECOMENDADOS

```python
class SecurityTests(TestCase):
    def test_cannot_login_without_tenant(self):
        """Login debe fallar sin tenant_subdomain"""
        response = self.client.post('/api/auth/login/', {
            'email': 'user@mail.com',
            'password': 'pass123'
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('tenant_subdomain', response.data)
    
    def test_cannot_create_superadmin_as_client_admin(self):
        """ClientAdmin no puede crear SuperAdmin"""
        self.client.force_authenticate(user=self.client_admin)
        response = self.client.post('/api/auth/users/', {
            'email': 'hacker@mail.com',
            'role': 'SuperAdmin'
        })
        self.assertEqual(response.status_code, 403)
    
    def test_email_unique_per_tenant(self):
        """Mismo email puede existir en diferentes tenants"""
        User.objects.create(email='test@mail.com', tenant=self.tenant_a)
        user_b = User.objects.create(email='test@mail.com', tenant=self.tenant_b)
        self.assertIsNotNone(user_b.id)
    
    def test_cannot_access_other_tenant_data(self):
        """Usuario no puede acceder a datos de otro tenant"""
        self.client.force_authenticate(user=self.user_tenant_a)
        response = self.client.get(f'/api/employees/{self.employee_tenant_b.id}/')
        self.assertEqual(response.status_code, 404)
```

---

## 📋 CONCLUSIÓN

### Estado Actual de Seguridad: 🔴 CRÍTICO

**Vulnerabilidades Críticas:**
1. ✅ Login sin tenant permite escalada horizontal
2. ✅ ClientAdmin puede crear SuperAdmin
3. ⚠️ Email único global limita funcionalidad

**Recomendación:** Implementar mitigaciones de Prioridad 1 INMEDIATAMENTE antes de producción.

**Nivel de Riesgo:** 🔴 **ALTO** (8/10)
- Arquitectura: 7/10
- Implementación: 4/10
- Seguridad: 3/10

