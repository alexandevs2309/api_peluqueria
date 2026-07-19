# 🔍 AUDITORÍA INFRAESTRUCTURA MULTI-TENANT

**Sistema:** Django SaaS con subdominios dinámicos
**Fecha:** 2024
**Criticidad:** PRODUCCIÓN

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## FASE 1 — DNS Y SUBDOMINIOS
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 🔴 HALLAZGOS CRÍTICOS

#### 1. ALLOWED_HOSTS no soporta wildcard
**Ubicación:** `settings.py` línea 42
```python
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost', "api_peluqueria-web-1"])
```

**Problema:**
- ❌ NO acepta subdominios dinámicos
- ❌ Cada tenant requiere registro manual
- ❌ Bloqueará `tenant1.app.com`, `tenant2.app.com`, etc.

**Riesgo:** 🔴 **CRÍTICO** - Sistema NO funciona con subdominios

---

#### 2. Nginx NO configurado para wildcard
**Ubicación:** `nginx/nginx.conf` línea 16
```nginx
server_name localhost;
```

**Problema:**
- ❌ Solo acepta `localhost`
- ❌ NO acepta `*.app.com`
- ❌ Rechazará todos los subdominios

**Riesgo:** 🔴 **CRÍTICO** - Nginx bloqueará subdominios

---

#### 3. Detección de tenant vulnerable
**Ubicación:** `serializers.py` línea 14
```python
host = request.META.get('HTTP_HOST', '')
if '.' in host:
    tenant_subdomain = host.split('.')[0]
```

**Vulnerabilidades:**
- ⚠️ Confía en header `Host` sin validación
- ⚠️ Susceptible a Host Header Injection
- ⚠️ No valida formato de subdominio

**Riesgo:** 🟠 **ALTO** - Manipulación de header

---

### 📊 CLASIFICACIÓN FASE 1: 🔴 **VULNERABLE**

**Razones:**
1. ALLOWED_HOSTS bloquea subdominios
2. Nginx no configurado para wildcard
3. Detección de tenant sin validación

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## FASE 2 — SSL Y CERTIFICADOS
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 🔴 HALLAZGOS CRÍTICOS

#### 1. Sin configuración SSL
**Ubicación:** `nginx/nginx.conf` línea 16
```nginx
listen 80;
```

**Problema:**
- ❌ Solo HTTP (puerto 80)
- ❌ Sin HTTPS (puerto 443)
- ❌ Sin certificados SSL

**Riesgo:** 🔴 **CRÍTICO** - Tráfico sin cifrar

---

#### 2. HSTS deshabilitado
**Ubicación:** `nginx/nginx.conf` línea 61
```nginx
# add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

**Problema:** Comentado, no activo

---

### 📊 CLASIFICACIÓN FASE 2: 🔴 **NO APTO PRODUCCIÓN**

**Requiere:**
- Certificado wildcard `*.app.com`
- Configuración HTTPS en Nginx
- HSTS habilitado

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## FASE 3 — COOKIES Y SESIÓN
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 🔴 HALLAZGOS CRÍTICOS

#### 1. SESSION_COOKIE_DOMAIN no configurado
**Ubicación:** `settings.py` - AUSENTE

**Problema:**
- ❌ Cookies NO se comparten entre subdominios
- ❌ Login en `tenant1.app.com` NO válido en `tenant2.app.com`
- ⚠️ Pero esto es CORRECTO para aislamiento

**Estado:** ✅ **CORRECTO** (aislamiento por defecto)

---

#### 2. CSRF_COOKIE_DOMAIN no configurado
**Ubicación:** `settings.py` - AUSENTE

**Estado:** ✅ **CORRECTO** (aislamiento por defecto)

---

#### 3. SESSION_COOKIE_SAMESITE = 'Strict'
**Ubicación:** `settings.py` línea 346
```python
SESSION_COOKIE_SAMESITE = 'Strict' if not DEBUG else 'Lax'
```

**Análisis:**
- ✅ `Strict` previene CSRF
- ✅ Cookies NO se envían entre subdominios
- ✅ Aislamiento fuerte entre tenants

**Estado:** ✅ **CORRECTO**

---

### 📊 CLASIFICACIÓN FASE 3: 🟢 **AISLAMIENTO FUERTE**

**Configuración actual:**
- ✅ Cookies aisladas por subdominio
- ✅ Login en tenant1 NO válido en tenant2
- ✅ Protección CSRF correcta

**Recomendación:** Mantener configuración actual

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## FASE 4 — CORS Y SEGURIDAD
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 🔴 HALLAZGOS CRÍTICOS

#### 1. CORS_ALLOWED_ORIGINS estático
**Ubicación:** `settings.py` línea 157
```python
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=['http://localhost:4200'])
```

**Problema:**
- ❌ Solo permite `localhost:4200`
- ❌ NO permite subdominios dinámicos
- ❌ Bloqueará `tenant1.app.com`, `tenant2.app.com`

**Riesgo:** 🔴 **CRÍTICO** - CORS bloqueará subdominios

---

#### 2. Sin CORS_ALLOWED_ORIGIN_REGEXES
**Ubicación:** `settings.py` - AUSENTE

**Falta:**
```python
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://[\w-]+\.app\.com$",
]
```

---

#### 3. ALLOWED_HOSTS sin wildcard
**Ya mencionado en Fase 1**

---

### 📊 CLASIFICACIÓN FASE 4: 🔴 **VULNERABLE**

**Razones:**
1. CORS bloqueará subdominios
2. Sin regex para wildcard
3. ALLOWED_HOSTS sin wildcard

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## FASE 5 — JWT Y TENANT VALIDATION
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### ✅ HALLAZGOS POSITIVOS

#### 1. JWT incluye tenant_id
**Ubicación:** `serializers.py` línea 177
```python
token['tenant_id'] = user.tenant.id
token['tenant_subdomain'] = user.tenant.subdomain
```

**Estado:** ✅ **CORRECTO**

---

#### 2. Middleware valida tenant
**Ubicación:** `middleware.py` línea 59
```python
if request.user.tenant_id != tenant_id:
    return JsonResponse({'error': 'TENANT_MISMATCH'}, status=403)
```

**Estado:** ✅ **CORRECTO**

---

### 🟠 HALLAZGOS MEDIOS

#### 1. Validación de tenant en login débil
**Ubicación:** `serializers.py` línea 14
```python
host = request.META.get('HTTP_HOST', '')
tenant_subdomain = host.split('.')[0]
```

**Problema:**
- ⚠️ No valida formato
- ⚠️ No valida contra lista permitida
- ⚠️ Acepta cualquier valor

**Riesgo:** 🟠 **MEDIO** - Host header injection

---

### 📊 CLASIFICACIÓN FASE 5: 🟠 **PARCIAL**

**Positivo:**
- ✅ JWT con tenant_id
- ✅ Middleware valida tenant

**Negativo:**
- ⚠️ Detección de tenant sin validación

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## FASE 6 — PREPARACIÓN PRODUCCIÓN
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 🔴 BLOQUEADORES CRÍTICOS

1. ❌ ALLOWED_HOSTS sin wildcard
2. ❌ Nginx sin wildcard
3. ❌ CORS sin regex
4. ❌ Sin SSL/HTTPS
5. ❌ Detección tenant sin validación

### 🟠 MEJORAS NECESARIAS

6. ⚠️ Sin certificado wildcard
7. ⚠️ Sin validación de formato de subdominio
8. ⚠️ Sin protección Host Header Injection

### 🟡 MEJORAS OPCIONALES

9. ⚠️ Sin soporte dominios personalizados
10. ⚠️ Sin CDN configurado

---

### 📊 CLASIFICACIÓN FINAL: 🔴 **NO APTO PRODUCCIÓN**

**Razones:**
- 🔴 5 bloqueadores críticos
- 🟠 3 mejoras necesarias
- Sistema NO funciona con subdominios actualmente

---

## 🛠️ CONFIGURACIÓN RECOMENDADA

### 1. ALLOWED_HOSTS con wildcard

```python
# settings.py
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[
    'localhost',
    '127.0.0.1',
    '.app.com',  # ✅ Acepta *.app.com
])

# Validación adicional
ALLOWED_SUBDOMAIN_PATTERN = r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$'
```

### 2. Nginx con wildcard

```nginx
server {
    listen 443 ssl http2;
    server_name ~^(?<tenant>[\w-]+)\.app\.com$;
    
    ssl_certificate /etc/letsencrypt/live/app.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.com/privkey.pem;
    
    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Tenant-Subdomain $tenant;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

### 3. CORS con regex

```python
# settings.py
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://[\w-]+\.app\.com$",
    r"^http://[\w-]+\.localhost:4200$",  # Dev
]
CORS_ALLOW_CREDENTIALS = True
```

### 4. Validación de tenant segura

```python
# apps/auth_api/serializers.py
import re

SUBDOMAIN_PATTERN = re.compile(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$')

def validate(self, data):
    request = self.context.get('request')
    host = request.META.get('HTTP_HOST', '')
    
    # Extraer subdominio
    if '.' in host:
        tenant_subdomain = host.split('.')[0]
    else:
        raise ValidationError('Accede desde tu subdominio')
    
    # ✅ VALIDAR FORMATO
    if not SUBDOMAIN_PATTERN.match(tenant_subdomain):
        raise ValidationError('Subdominio inválido')
    
    # ✅ VALIDAR EXISTENCIA
    try:
        tenant = Tenant.objects.get(
            subdomain=tenant_subdomain,
            is_active=True,
            deleted_at__isnull=True
        )
    except Tenant.DoesNotExist:
        raise ValidationError('Credenciales inválidas')
    
    # Continuar validación...
```

### 5. Middleware de validación de Host

```python
# apps/tenants_api/middleware.py
class HostValidationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_pattern = re.compile(r'^[\w-]+\.app\.com$')
    
    def __call__(self, request):
        host = request.META.get('HTTP_HOST', '').split(':')[0]
        
        # Permitir localhost en dev
        if settings.DEBUG and 'localhost' in host:
            return self.get_response(request)
        
        # Validar patrón
        if not self.allowed_pattern.match(host):
            return JsonResponse({
                'error': 'Invalid host',
                'code': 'INVALID_HOST'
            }, status=400)
        
        return self.get_response(request)
```

---

## 🚨 RIESGOS REALES

### Riesgo 1: Host Header Injection
**Severidad:** 🔴 CRÍTICA
**Explotación:**
```bash
curl -H "Host: malicious.com" https://app.com/api/auth/login/
```
**Impacto:** Redirección a sitio malicioso

**Mitigación:** Validar Host en middleware

---

### Riesgo 2: Login cruzado entre subdominios
**Severidad:** 🟠 ALTA
**Explotación:**
```bash
# Login en tenant1
curl https://tenant1.app.com/api/auth/login/

# Usar token en tenant2
curl -H "Authorization: Bearer <token>" https://tenant2.app.com/api/data/
```
**Impacto:** Acceso a datos de otro tenant

**Mitigación:** Middleware valida tenant_id en JWT (✅ ya implementado)

---

### Riesgo 3: CORS bypass
**Severidad:** 🟠 ALTA
**Explotación:**
```javascript
// Desde sitio malicioso
fetch('https://tenant1.app.com/api/data/', {
  credentials: 'include'
})
```
**Impacto:** Robo de datos si CORS mal configurado

**Mitigación:** CORS_ALLOWED_ORIGIN_REGEXES estricto

---

## ✅ CHECKLIST PRODUCCIÓN SAAS

### DNS y Subdominios
- [ ] Wildcard DNS configurado (`*.app.com`)
- [ ] ALLOWED_HOSTS con `.app.com`
- [ ] Nginx con `server_name ~^(?<tenant>[\w-]+)\.app\.com$`
- [ ] Validación de formato de subdominio
- [ ] Middleware de validación de Host

### SSL y Certificados
- [ ] Certificado wildcard `*.app.com`
- [ ] HTTPS habilitado (puerto 443)
- [ ] HTTP → HTTPS redirect
- [ ] HSTS habilitado
- [ ] SSL Labs A+ rating

### Cookies y Sesión
- [x] SESSION_COOKIE_SAMESITE = 'Strict'
- [x] CSRF_COOKIE_SAMESITE = 'Strict'
- [x] SESSION_COOKIE_HTTPONLY = True
- [x] Aislamiento entre subdominios
- [ ] SESSION_COOKIE_SECURE = True (requiere HTTPS)

### CORS y Seguridad
- [ ] CORS_ALLOWED_ORIGIN_REGEXES configurado
- [ ] CORS_ALLOW_CREDENTIALS = True
- [ ] Validación de origen estricta
- [ ] CSP headers configurados

### JWT y Tenant
- [x] JWT incluye tenant_id
- [x] Middleware valida tenant
- [ ] Validación de formato de subdominio
- [ ] Protección Host Header Injection

### Infraestructura
- [ ] Load balancer configurado
- [ ] CDN para estáticos
- [ ] Rate limiting por tenant
- [ ] Monitoreo de subdominios
- [ ] Backup automatizado

---

## 📊 EVALUACIÓN FINAL

| Fase | Estado | Nivel |
|------|--------|-------|
| DNS y Subdominios | 🔴 Vulnerable | 2/10 |
| SSL y Certificados | 🔴 No apto | 0/10 |
| Cookies y Sesión | 🟢 Seguro | 9/10 |
| CORS y Seguridad | 🔴 Vulnerable | 3/10 |
| JWT y Tenant | 🟠 Parcial | 7/10 |
| Preparación Producción | 🔴 No apto | 3/10 |

### **NIVEL GENERAL: 🔴 NO APTO PRODUCCIÓN SAAS (4/10)**

**Bloqueadores críticos:**
1. ALLOWED_HOSTS sin wildcard
2. Nginx sin wildcard
3. CORS sin regex
4. Sin SSL/HTTPS
5. Detección tenant sin validación

**Tiempo estimado de corrección:** 2-3 días

**Prioridad:** 🔴 CRÍTICA - Sistema NO funciona con subdominios actualmente
