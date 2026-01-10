# CHECKLIST DE SEGURIDAD PRE-PRODUCCIÓN

## 🔒 CONFIGURACIÓN DJANGO

### ✅ Settings Críticos
- [ ] `DEBUG = False` en producción
- [ ] `SECRET_KEY` único y seguro (50+ caracteres)
- [ ] `ALLOWED_HOSTS` específico (sin '*')
- [ ] `CSRF_TRUSTED_ORIGINS` configurado
- [ ] `SECURE_SSL_REDIRECT = True`
- [ ] `SESSION_COOKIE_SECURE = True`
- [ ] `CSRF_COOKIE_SECURE = True`
- [ ] `SECURE_HSTS_SECONDS = 31536000`

### ✅ Headers de Seguridad
- [ ] `X_FRAME_OPTIONS = 'DENY'`
- [ ] `SECURE_CONTENT_TYPE_NOSNIFF = True`
- [ ] `SECURE_BROWSER_XSS_FILTER = True`
- [ ] `SECURE_REFERRER_POLICY` configurado

## 🌐 CORS Y ORÍGENES

### ✅ CORS Restrictivo
- [ ] `CORS_ALLOW_ALL_ORIGINS = False`
- [ ] `CORS_ALLOWED_ORIGINS` solo dominios específicos
- [ ] Sin 'localhost' en orígenes de producción
- [ ] `CORS_ALLOW_CREDENTIALS = True` solo si necesario

### ✅ Validación de Orígenes
```bash
# Verificar que estos NO estén en producción:
grep -r "localhost" .env*
grep -r "127.0.0.1" .env*
grep -r "CORS_ALLOW_ALL_ORIGINS.*True" .
```

## 🚦 RATE LIMITING

### ✅ Límites Estrictos
- [ ] `user: 300/hour` (máximo)
- [ ] `anon: 30/hour` (máximo)
- [ ] `login: 3/min` (máximo)
- [ ] `register: 2/hour` (máximo)
- [ ] `password_reset: 2/hour` (máximo)

### ✅ Endpoints Críticos
- [ ] Login protegido contra brute force
- [ ] Registro limitado contra spam
- [ ] Password reset limitado
- [ ] APIs de pago con límites estrictos

## 🔐 AUTENTICACIÓN Y AUTORIZACIÓN

### ✅ JWT Configuración
- [ ] `ACCESS_TOKEN_LIFETIME` apropiado (8 horas máx)
- [ ] `REFRESH_TOKEN_LIFETIME` apropiado (30 días máx)
- [ ] `ROTATE_REFRESH_TOKENS = True`
- [ ] `BLACKLIST_AFTER_ROTATION = True`
- [ ] `TOKEN_BLACKLIST_ENABLED = True`

### ✅ Permisos DRF
- [ ] `DEFAULT_PERMISSION_CLASSES` restrictivo
- [ ] Sin `AllowAny` en endpoints sensibles
- [ ] Validación de tenant en todos los endpoints
- [ ] RLS activo en PostgreSQL

## 🗄️ BASE DE DATOS

### ✅ PostgreSQL Seguro
- [ ] SSL requerido (`sslmode=require`)
- [ ] Usuario específico (no postgres)
- [ ] Password fuerte (16+ caracteres)
- [ ] RLS habilitado y funcionando
- [ ] Conexiones limitadas

### ✅ Validación RLS
```sql
-- Verificar que RLS está activo
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname NOT IN ('information_schema', 'pg_catalog');

-- Debe mostrar rowsecurity = true para tablas críticas
```

## 📧 SERVICIOS EXTERNOS

### ✅ SendGrid
- [ ] API Key de producción (no test)
- [ ] Dominio verificado
- [ ] From email del dominio propio
- [ ] Templates configurados

### ✅ Sentry
- [ ] DSN de producción
- [ ] `send_default_pii = False`
- [ ] Filtros de datos sensibles activos
- [ ] Environment correcto

### ✅ Stripe (si aplica)
- [ ] Claves de producción (sk_live_, pk_live_)
- [ ] Webhooks configurados
- [ ] SSL verificado

## 🔍 ENDPOINTS SENSIBLES

### ✅ Revisión Manual
- [ ] `/admin/` protegido o deshabilitado
- [ ] `/api/docs/` requiere autenticación
- [ ] `/api/schema/` requiere autenticación
- [ ] Endpoints de debug deshabilitados
- [ ] Health checks sin información sensible

### ✅ Comandos de Verificación
```bash
# Buscar endpoints peligrosos
grep -r "AllowAny" apps/
grep -r "permission_classes.*\[\]" apps/
grep -r "authentication_classes.*\[\]" apps/

# Verificar que no hay prints/debug
grep -r "print(" apps/
grep -r "pdb.set_trace" apps/
grep -r "import pdb" apps/
```

## 🚨 ERRORES COMUNES DE SEGURIDAD

### ❌ NUNCA en Producción
- [ ] `DEBUG = True`
- [ ] `ALLOWED_HOSTS = ['*']`
- [ ] `CORS_ALLOW_ALL_ORIGINS = True`
- [ ] Passwords hardcodeados
- [ ] Tokens reales en código
- [ ] Logs con información sensible
- [ ] Endpoints sin autenticación

### ❌ Configuraciones Peligrosas
```python
# NUNCA hacer esto:
CORS_ALLOW_ALL_ORIGINS = True
ALLOWED_HOSTS = ['*']
DEBUG = True
SECRET_KEY = 'django-insecure-...'
DATABASES = {'default': {'PASSWORD': 'password123'}}
```

## 🔧 HERRAMIENTAS DE VALIDACIÓN

### ✅ Scripts de Seguridad
```bash
# Ejecutar validador de entorno
python scripts/validate_env.py --env-file .env.production

# Django security check
python manage.py check --deploy --settings=backend.settings_production

# Verificar configuración SSL
python manage.py check --tag security --settings=backend.settings_production
```

### ✅ Tests de Seguridad
```python
# Crear tests específicos
class SecurityTests(TestCase):
    def test_debug_false_in_production(self):
        self.assertFalse(settings.DEBUG)
    
    def test_secure_headers_present(self):
        response = self.client.get('/')
        self.assertIn('X-Frame-Options', response)
    
    def test_cors_not_allow_all(self):
        self.assertFalse(getattr(settings, 'CORS_ALLOW_ALL_ORIGINS', False))
```

## 🎯 CHECKLIST FINAL DE SEGURIDAD

### Antes del Despliegue
- [ ] Todas las validaciones automáticas pasan
- [ ] Review manual de configuración completado
- [ ] Tests de seguridad ejecutados
- [ ] Endpoints críticos verificados manualmente
- [ ] Logs no contienen información sensible
- [ ] Variables de entorno validadas
- [ ] SSL/TLS configurado correctamente
- [ ] Rate limiting probado
- [ ] Autenticación funcionando correctamente
- [ ] RLS validado en base de datos

### Post-Despliegue
- [ ] Monitoreo de Sentry activo
- [ ] Logs estructurados funcionando
- [ ] Rate limiting efectivo
- [ ] SSL/HTTPS funcionando
- [ ] Headers de seguridad presentes
- [ ] Endpoints protegidos correctamente

## 🚨 SEÑALES DE ALERTA

### Detener Despliegue Si:
- ❌ DEBUG=True en producción
- ❌ SECRET_KEY por defecto
- ❌ CORS permite todos los orígenes
- ❌ Endpoints críticos sin autenticación
- ❌ RLS no funciona correctamente
- ❌ Variables de entorno faltantes
- ❌ SSL no configurado
- ❌ Sentry no funciona

### Continuar Con Precaución Si:
- ⚠️ Rate limiting muy permisivo
- ⚠️ Logs muy verbosos
- ⚠️ Algunos endpoints sin documentar
- ⚠️ Tests de seguridad incompletos