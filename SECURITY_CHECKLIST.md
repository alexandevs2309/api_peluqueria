# CHECKLIST DE SEGURIDAD PRE-PRODUCCIÓN

## ✅ CONFIGURACIÓN DJANGO

### Settings Críticos
- [ ] `DEBUG = False` ✋ CRÍTICO
- [ ] `SECRET_KEY` único y seguro (50+ caracteres)
- [ ] `ALLOWED_HOSTS` específicos (NO wildcards)
- [ ] `CSRF_TRUSTED_ORIGINS` configurados
- [ ] SSL/TLS obligatorio (`SECURE_SSL_REDIRECT = True`)
- [ ] Cookies seguras (`SESSION_COOKIE_SECURE = True`)

### Headers de Seguridad
- [ ] `X_FRAME_OPTIONS = 'DENY'`
- [ ] `SECURE_CONTENT_TYPE_NOSNIFF = True`
- [ ] `SECURE_BROWSER_XSS_FILTER = True`
- [ ] HSTS configurado (31536000 segundos)

## ✅ AUTENTICACIÓN Y AUTORIZACIÓN

### JWT Configuration
- [ ] `ACCESS_TOKEN_LIFETIME` apropiado (8 horas máximo)
- [ ] `REFRESH_TOKEN_LIFETIME` controlado (30 días máximo)
- [ ] `ROTATE_REFRESH_TOKENS = True`
- [ ] `BLACKLIST_AFTER_ROTATION = True`

### Permisos DRF
- [ ] `DEFAULT_PERMISSION_CLASSES = ['IsAuthenticated']`
- [ ] Rate limiting activado y configurado
- [ ] Throttling por usuario y anónimo

## ✅ CORS Y ORÍGENES

### CORS Configuration
- [ ] `CORS_ALLOWED_ORIGINS` específicos (NO wildcards)
- [ ] `CORS_ALLOW_CREDENTIALS = True` solo si necesario
- [ ] NO `CORS_ALLOW_ALL_ORIGINS = True` ✋ PROHIBIDO

## ✅ ENDPOINTS SENSIBLES

### Endpoints a Revisar
- [ ] `/admin/` protegido o deshabilitado
- [ ] `/api/schema/` acceso controlado
- [ ] `/api/docs/` acceso controlado
- [ ] Endpoints de debug deshabilitados

### Validaciones de Seguridad
```bash
# Verificar que admin requiere autenticación
curl -I https://tu-dominio.com/admin/

# Verificar headers de seguridad
curl -I https://tu-dominio.com/api/

# Verificar rate limiting
for i in {1..10}; do curl https://tu-dominio.com/api/auth/login/; done
```

## ✅ BASE DE DATOS

### PostgreSQL Security
- [ ] RLS (Row Level Security) activo
- [ ] Usuario de aplicación con permisos mínimos
- [ ] SSL/TLS obligatorio (`sslmode=require`)
- [ ] Connection pooling configurado

### Validación RLS
```sql
-- Verificar que RLS está activo
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE rowsecurity = true;

-- Verificar políticas RLS
SELECT schemaname, tablename, policyname, cmd, qual 
FROM pg_policies;
```

## ✅ REDIS Y CELERY

### Redis Security
- [ ] Password configurado
- [ ] Bind a interfaces específicas
- [ ] NO acceso público

### Celery Tasks
- [ ] `CELERY_TASK_ALWAYS_EAGER = False`
- [ ] Workers monitoreados
- [ ] Beat schedule validado

## 🚨 ERRORES COMUNES A EVITAR

### Configuración
- ❌ `DEBUG = True` en producción
- ❌ `ALLOWED_HOSTS = ['*']`
- ❌ `SECRET_KEY` hardcodeado
- ❌ Credenciales en código fuente

### CORS
- ❌ `CORS_ALLOW_ALL_ORIGINS = True`
- ❌ Wildcards en origins (`*.ejemplo.com`)

### Base de Datos
- ❌ Usuario con permisos de superuser
- ❌ Conexiones sin SSL
- ❌ RLS desactivado

### Logging
- ❌ Logs con información sensible
- ❌ Nivel DEBUG en producción
- ❌ Logs sin rotación

## COMANDOS DE VALIDACIÓN

```bash
# Validar configuración Django
python manage.py check --deploy

# Verificar variables de entorno
python backend/env_validator.py

# Test de seguridad básico
python manage.py shell -c "
from django.conf import settings
print('DEBUG:', settings.DEBUG)
print('ALLOWED_HOSTS:', settings.ALLOWED_HOSTS)
print('SECURE_SSL_REDIRECT:', settings.SECURE_SSL_REDIRECT)
"

# Verificar RLS
python manage.py shell -c "
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('SELECT current_setting(\'row_security\')')
    print('RLS Status:', cursor.fetchone()[0])
"
```