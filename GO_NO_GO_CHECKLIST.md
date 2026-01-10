# CHECKLIST GO/NO-GO - PRIMER DESPLIEGUE

## 🚦 CRITERIOS DE DECISIÓN

### ✅ GO - Listo para desplegar
### ❌ NO-GO - Detener despliegue
### ⚠️ REVISAR - Evaluar riesgo

---

## 1. CONFIGURACIÓN CRÍTICA

### Django Settings
- [ ] `DEBUG = False` ✋ **CRÍTICO**
- [ ] `SECRET_KEY` único y seguro
- [ ] `ALLOWED_HOSTS` configurados correctamente
- [ ] SSL/TLS obligatorio activado
- [ ] Headers de seguridad configurados

**Comando de validación:**
```bash
python manage.py check --deploy
```
**Resultado esperado:** `System check identified no issues (0 silenced).`

### Variables de Entorno
- [ ] Todas las variables obligatorias presentes
- [ ] No hay variables prohibidas en producción
- [ ] Credenciales válidas y funcionales

**Comando de validación:**
```bash
python backend/env_validator.py
```
**Resultado esperado:** `✅ Validación de entorno: APROBADA`

---

## 2. BASE DE DATOS

### Configuración PostgreSQL
- [ ] Conexión SSL activa
- [ ] RLS (Row Level Security) funcionando
- [ ] Migraciones aplicadas completamente
- [ ] Políticas RLS en tablas críticas

**Comando de validación:**
```bash
./scripts/backup_strategy.sh validate
```
**Resultado esperado:** `✅ Base de datos validada correctamente`

### Backup Strategy
- [ ] Backup automático configurado
- [ ] Restauración probada en entorno de prueba
- [ ] Retención de backups configurada

**Test crítico:**
```bash
# Crear backup de prueba
./scripts/backup_strategy.sh backup

# Verificar integridad
./scripts/backup_strategy.sh verify /path/to/latest/backup.dump
```

---

## 3. SERVICIOS EXTERNOS

### Redis y Celery
- [ ] Redis accesible y funcionando
- [ ] Workers de Celery activos
- [ ] Beat scheduler ejecutando tareas
- [ ] Tareas críticas funcionando

**Comando de validación:**
```bash
python manage.py validate_celery
```
**Resultado esperado:** `✅ Celery listo para producción`

### Email (SendGrid)
- [ ] API key válida
- [ ] Envío de email funcionando
- [ ] Templates configurados

**Test manual:**
```bash
python manage.py shell -c "
from django.core.mail import send_mail
send_mail('Test', 'Test message', 'from@domain.com', ['test@domain.com'])
"
```

### Sentry
- [ ] DSN configurado
- [ ] Errores llegando a Sentry
- [ ] Alertas configuradas

**Test manual:**
```bash
python manage.py shell -c "
import sentry_sdk
sentry_sdk.capture_message('Test deployment message')
"
```

---

## 4. SEGURIDAD

### Autenticación
- [ ] JWT configurado correctamente
- [ ] Rate limiting activo
- [ ] CORS configurado (no wildcards)
- [ ] Endpoints sensibles protegidos

**Test de seguridad:**
```bash
# Verificar rate limiting
for i in {1..10}; do curl -w "%{http_code}\n" https://domain.com/api/auth/login/; done

# Verificar headers de seguridad
curl -I https://domain.com/api/
```

### Endpoints
- [ ] `/admin/` protegido o deshabilitado
- [ ] `/api/docs/` acceso controlado
- [ ] No hay endpoints de debug expuestos

---

## 5. DOCKER Y INFRAESTRUCTURA

### Contenedores
- [ ] Todas las imágenes construyen correctamente
- [ ] Servicios inician en orden correcto
- [ ] Volúmenes persistentes configurados
- [ ] Redes internas funcionando

**Comando de validación:**
```bash
docker-compose -f docker-compose.prod.yml config
docker-compose -f docker-compose.prod.yml up --dry-run
```

### Health Checks
- [ ] Endpoint de health check funcionando
- [ ] Todos los servicios reportan healthy

**Test de health:**
```bash
curl https://domain.com/api/health/
```
**Respuesta esperada:** `{"status": "healthy", "timestamp": "..."}`

---

## 6. PRUEBAS FUNCIONALES CRÍTICAS

### Flujo de Autenticación
- [ ] Login funciona correctamente
- [ ] Logout invalida tokens
- [ ] Refresh tokens funcionan
- [ ] MFA funciona (si está habilitado)

### Flujos de Negocio Críticos
- [ ] Crear cliente funciona
- [ ] Registrar venta funciona
- [ ] Calcular nómina funciona
- [ ] Soft delete y restore funcionan

### Multi-tenancy
- [ ] Aislamiento por tenant funciona
- [ ] RLS previene acceso cruzado
- [ ] Auditoría registra tenant correctamente

---

## 7. MONITOREO Y OBSERVABILIDAD

### Logging
- [ ] Logs estructurados funcionando
- [ ] Nivel de logging apropiado
- [ ] No hay información sensible en logs
- [ ] Rotación de logs configurada

### Métricas
- [ ] Sentry recibiendo errores
- [ ] Logs llegando al sistema de logging
- [ ] Métricas de performance disponibles

---

## 🚦 DECISIÓN FINAL

### ✅ GO - Todos los criterios cumplidos
**Condiciones:**
- Todos los ✅ marcados
- Todos los tests pasan
- Backup y restauración probados
- Equipo de soporte disponible

### ❌ NO-GO - Detener despliegue
**Condiciones críticas que impiden despliegue:**
- `DEBUG = True`
- Variables de entorno faltantes
- Base de datos no accesible
- Servicios críticos caídos
- Tests de seguridad fallan

### ⚠️ REVISAR - Evaluar riesgo
**Condiciones que requieren evaluación:**
- Warnings en validaciones
- Performance degradada
- Servicios no críticos con problemas
- Documentación incompleta

---

## 📋 CHECKLIST DE EJECUCIÓN

### Pre-despliegue (30 min antes)
- [ ] Ejecutar todos los comandos de validación
- [ ] Verificar que el equipo de soporte está disponible
- [ ] Confirmar ventana de mantenimiento
- [ ] Backup de seguridad creado

### Durante el despliegue
- [ ] Monitorear logs en tiempo real
- [ ] Verificar health checks cada 2 minutos
- [ ] Probar flujos críticos inmediatamente
- [ ] Confirmar que Sentry recibe eventos

### Post-despliegue (primeros 30 min)
- [ ] Ejecutar smoke tests completos
- [ ] Verificar métricas de performance
- [ ] Confirmar que todos los servicios están healthy
- [ ] Documentar cualquier issue encontrado

---

## 🆘 PLAN DE ROLLBACK

### Criterios para Rollback Inmediato
- Errores 5xx > 5% del tráfico
- Base de datos inaccesible
- Servicios críticos caídos > 5 minutos
- Pérdida de datos detectada

### Procedimiento de Rollback
1. Detener tráfico nuevo
2. Restaurar versión anterior
3. Verificar integridad de datos
4. Restaurar backup si es necesario
5. Comunicar status al equipo

**Tiempo objetivo de rollback:** < 15 minutos