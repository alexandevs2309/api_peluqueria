# 🚀 CHECKLIST GO / NO-GO - PRIMER DESPLIEGUE

## ⚡ VALIDACIONES AUTOMÁTICAS

### 🔧 Scripts de Validación
```bash
# 1. Validar variables de entorno
python scripts/validate_env.py --env-file .env.production

# 2. Validar configuración Django
python manage.py check --deploy --settings=backend.settings_production

# 3. Validar Celery
python scripts/validate_celery.py

# 4. Validar seguridad
python manage.py check --tag security --settings=backend.settings_production

# 5. Validar OpenAPI
curl -f http://localhost:8000/api/schema/ > /dev/null
```

### ✅ Criterios Automáticos GO
- [ ] Todas las validaciones automáticas pasan sin errores críticos
- [ ] Tests de seguridad exitosos
- [ ] Variables de entorno validadas
- [ ] Conexiones a servicios externos funcionando
- [ ] Docker containers arrancan sin errores

## 🔍 VALIDACIONES MANUALES

### 🔒 Seguridad Crítica
- [ ] `DEBUG = False` confirmado
- [ ] `SECRET_KEY` único y seguro (50+ caracteres)
- [ ] `ALLOWED_HOSTS` específico (sin '*')
- [ ] HTTPS configurado y funcionando
- [ ] Headers de seguridad presentes
- [ ] CORS restrictivo configurado
- [ ] Rate limiting activo y probado

### 🗄️ Base de Datos
- [ ] PostgreSQL conectando correctamente
- [ ] RLS habilitado y funcionando
- [ ] Migraciones aplicadas sin errores
- [ ] Backup inicial creado y verificado
- [ ] Usuario de BD con permisos mínimos necesarios

### 🔴 Redis y Celery
- [ ] Redis conectando y respondiendo
- [ ] Celery workers activos (mínimo 1)
- [ ] Celery Beat programando tareas
- [ ] Tareas críticas ejecutándose sin errores
- [ ] Cola de tareas funcionando

### 📧 Servicios Externos
- [ ] Sentry recibiendo eventos correctamente
- [ ] SendGrid enviando emails de prueba
- [ ] Stripe (si aplica) en modo producción
- [ ] Logs estructurados llegando a destino

### 🌐 Conectividad
- [ ] Nginx sirviendo contenido estático
- [ ] SSL/TLS certificados válidos
- [ ] Frontend puede conectar a API
- [ ] Health checks respondiendo correctamente

## 🧪 PRUEBAS MANUALES CRÍTICAS

### 🔐 Autenticación
```bash
# Test de login
curl -X POST https://api.tu-dominio.com/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Debe retornar tokens JWT válidos
```

### 👥 Multi-tenancy
```bash
# Test de aislamiento de tenants
# 1. Crear usuario en tenant A
# 2. Intentar acceder a datos de tenant B
# 3. Debe fallar con 403/404
```

### 💰 Funcionalidades Críticas
- [ ] Crear cliente nuevo
- [ ] Agendar cita
- [ ] Procesar venta en POS
- [ ] Calcular nómina
- [ ] Generar reporte básico

### 📊 Monitoreo
- [ ] Logs aparecen en Sentry
- [ ] Métricas de performance visibles
- [ ] Alertas configuradas y funcionando
- [ ] Health checks monitoreados

## 🚨 CRITERIOS NO-GO (DETENER DESPLIEGUE)

### ❌ Errores Críticos
- [ ] DEBUG=True en producción
- [ ] SECRET_KEY por defecto o inseguro
- [ ] Base de datos no conecta
- [ ] RLS no funciona correctamente
- [ ] Celery no arranca
- [ ] Sentry no recibe eventos
- [ ] SSL/HTTPS no funciona
- [ ] CORS permite todos los orígenes
- [ ] Rate limiting no activo

### ❌ Funcionalidades Rotas
- [ ] Login no funciona
- [ ] Multi-tenancy roto
- [ ] APIs críticas fallan
- [ ] Emails no se envían
- [ ] Backups fallan

### ❌ Seguridad Comprometida
- [ ] Endpoints sin autenticación
- [ ] Datos sensibles expuestos
- [ ] Headers de seguridad faltantes
- [ ] Permisos incorrectos

## ⚠️ CRITERIOS PRECAUCIÓN (EVALUAR)

### 🟡 Advertencias Aceptables
- [ ] Logs muy verbosos (ajustar post-despliegue)
- [ ] Rate limiting permisivo (endurecer gradualmente)
- [ ] Algunos tests unitarios fallan (no críticos)
- [ ] Performance subóptima (optimizar después)

### 🟡 Monitoreo Incompleto
- [ ] Algunas métricas faltantes
- [ ] Alertas no configuradas completamente
- [ ] Dashboards básicos

## 🎯 CHECKLIST FINAL GO

### ✅ Antes de Lanzar
- [ ] Todos los criterios NO-GO resueltos
- [ ] Validaciones automáticas exitosas
- [ ] Pruebas manuales completadas
- [ ] Backups funcionando
- [ ] Monitoreo básico activo
- [ ] Plan de rollback preparado
- [ ] Equipo de soporte alertado

### ✅ Momento del Lanzamiento
- [ ] Tráfico dirigido gradualmente
- [ ] Logs monitoreados en tiempo real
- [ ] Métricas de performance observadas
- [ ] Equipo disponible para incidentes
- [ ] Rollback listo si es necesario

## 📋 COMANDOS DE VALIDACIÓN FINAL

### Pre-Despliegue
```bash
#!/bin/bash
echo "🔍 VALIDACIÓN FINAL PRE-DESPLIEGUE"

# 1. Variables de entorno
python scripts/validate_env.py --env-file .env.production || exit 1

# 2. Configuración Django
python manage.py check --deploy --settings=backend.settings_production || exit 1

# 3. Seguridad
python manage.py check --tag security --settings=backend.settings_production || exit 1

# 4. Base de datos
python manage.py migrate --check --settings=backend.settings_production || exit 1

# 5. Archivos estáticos
python manage.py collectstatic --dry-run --settings=backend.settings_production || exit 1

echo "✅ Todas las validaciones pasaron - LISTO PARA DESPLIEGUE"
```

### Post-Despliegue
```bash
#!/bin/bash
echo "🔍 VALIDACIÓN POST-DESPLIEGUE"

# 1. Health check
curl -f https://api.tu-dominio.com/api/healthz/ || exit 1

# 2. API funcionando
curl -f https://api.tu-dominio.com/api/auth/login/ -X POST \
  -H "Content-Type: application/json" \
  -d '{}' | grep -q "error" || exit 1

# 3. SSL funcionando
curl -I https://api.tu-dominio.com/ | grep -q "200 OK" || exit 1

# 4. Celery activo
docker exec saas_peluquerias_celery celery -A backend inspect ping || exit 1

echo "✅ Despliegue exitoso - SISTEMA OPERATIVO"
```

## 🚀 DECISIÓN FINAL

### ✅ GO - Proceder con Despliegue
**Condiciones:**
- Todas las validaciones automáticas pasan
- Criterios NO-GO resueltos
- Pruebas manuales exitosas
- Equipo preparado para monitoreo

### ❌ NO-GO - Detener Despliegue
**Condiciones:**
- Cualquier criterio NO-GO presente
- Validaciones críticas fallan
- Funcionalidades básicas rotas
- Seguridad comprometida

### 🟡 GO CON PRECAUCIÓN
**Condiciones:**
- Solo advertencias menores
- Funcionalidades críticas funcionan
- Monitoreo activo disponible
- Rollback preparado

---

**REGLA DE ORO:** En caso de duda, NO-GO. Es mejor retrasar que lanzar con problemas críticos.