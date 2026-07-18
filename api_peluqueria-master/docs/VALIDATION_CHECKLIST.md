# Checklist de Validación - Producción

## ✅ Pre-Deploy

- [ ] Variables de entorno configuradas en `.env`
- [ ] Webhook de Slack configurado y probado
- [ ] Email de alertas configurado
- [ ] Certificados SSL en lugar (si aplica)
- [ ] Firewall configurado
- [ ] Backup de datos existentes (si aplica)

## ✅ Deploy

```bash
# 1. Ejecutar setup inicial
./ops/setup_production.sh

# 2. Levantar servicios
docker-compose -f ops/docker-compose.production.yml up -d

# 3. Verificar que todos los containers están corriendo
docker-compose -f ops/docker-compose.production.yml ps
```

## ✅ Validación Post-Deploy

### Health Checks
```bash
# Health endpoint responde
curl -f http://localhost/health/ | jq '.status'
# Debe retornar: "healthy"

# Métricas disponibles
curl -f http://localhost/metrics/ | jq '.timestamp'
# Debe retornar timestamp actual
```

### Base de Datos
```bash
# Conectividad
docker exec $(docker ps -q -f name=db) pg_isready -U postgres
# Debe retornar: accepting connections

# Migrations aplicadas
docker exec $(docker ps -q -f name=web) python manage.py showmigrations
# Debe mostrar todas las migraciones con [X]
```

### Redis y Celery
```bash
# Redis funcionando
docker exec $(docker ps -q -f name=redis) redis-cli ping
# Debe retornar: PONG

# Celery workers activos
docker exec $(docker ps -q -f name=celery) celery -A backend inspect active
# Debe mostrar workers activos
```

### Backup System
```bash
# Ejecutar backup manual
./ops/backup/backup_db.sh

# Verificar archivo creado
ls -la /backups/*.sql.gz | tail -1
# Debe mostrar archivo reciente

# Validar integridad
gunzip -t /backups/$(ls -t /backups/*.sql.gz | head -1)
# No debe mostrar errores
```

### Restore Test
```bash
# Test de restore (NO DESTRUCTIVO)
LATEST_BACKUP=$(ls -t /backups/*.sql.gz | head -1)
./ops/restore/restore_db.sh $LATEST_BACKUP test_restore_$(date +%s)

# Verificar que se creó la DB de prueba
docker exec $(docker ps -q -f name=db) psql -U postgres -l | grep test_restore

# Limpiar DB de prueba
docker exec $(docker ps -q -f name=db) dropdb -U postgres test_restore_*
```

### Monitoring y Alertas
```bash
# Ejecutar monitor manual
./ops/monitoring/service_monitor.sh

# Verificar logs
tail -5 /var/log/service_monitor.log
# Debe mostrar estado actual de servicios

# Test de alerta (simular caída)
docker-compose -f ops/docker-compose.production.yml stop web
sleep 60  # Esperar 1 minuto
# Verificar que llegó alerta por Slack/Email

# Restaurar servicio
docker-compose -f ops/docker-compose.production.yml start web
```

### Cron Jobs
```bash
# Verificar cron jobs instalados
crontab -l
# Debe mostrar:
# 0 2 * * * .../backup_db.sh
# */5 * * * * .../service_monitor.sh
```

### Performance Básico
```bash
# Response time del health endpoint
time curl -s http://localhost/health/ > /dev/null
# Debe ser < 2 segundos

# Verificar logs de errores
docker-compose -f ops/docker-compose.production.yml logs web | grep ERROR | tail -5
# No debe haber errores críticos recientes
```

## ✅ Validación Semanal

### Backup Integrity
```bash
# Verificar backups de la semana
find /backups -name "*.sql.gz" -mtime -7 -ls

# Test de restore semanal
WEEKLY_BACKUP=$(find /backups -name "*.sql.gz" -mtime -7 | head -1)
./ops/restore/restore_db.sh $WEEKLY_BACKUP weekly_test_$(date +%s)
# Verificar datos y limpiar
```

### Disk Space
```bash
# Verificar espacio disponible
df -h /
# Debe tener > 20% libre

# Limpiar backups antiguos si es necesario
find /backups -name "*.sql.gz" -mtime +30 -delete
```

### Log Review
```bash
# Revisar logs de errores
grep -i error /var/log/peluqueria/*.log | tail -10

# Revisar logs de backup
grep -i "backup completado" /var/log/peluqueria/backup.log | tail -7
# Debe mostrar 7 backups exitosos
```

## ✅ Validación Mensual

### Full Disaster Recovery Test
```bash
# 1. Backup completo actual
./ops/backup/backup_db.sh

# 2. Simular pérdida total
docker-compose -f ops/docker-compose.production.yml down -v

# 3. Restore completo
docker-compose -f ops/docker-compose.production.yml up -d db redis
sleep 30
LATEST_BACKUP=$(ls -t /backups/*.sql.gz | head -1)
./ops/restore/restore_db.sh $LATEST_BACKUP peluqueria_db

# 4. Levantar aplicación
docker-compose -f ops/docker-compose.production.yml up -d

# 5. Verificar funcionamiento completo
curl -f http://localhost/health/
```

### Security Check
```bash
# Verificar puertos expuestos
nmap localhost

# Verificar logs de acceso sospechoso
grep -i "failed\|denied\|unauthorized" /var/log/auth.log | tail -10

# Verificar actualizaciones de seguridad
sudo apt list --upgradable | grep -i security
```

## 🚨 Criterios de Fallo

**CRÍTICO - Detener deploy:**
- Health endpoint no responde
- Base de datos no conecta
- Backup falla
- Restore test falla

**WARNING - Investigar:**
- Response time > 3 segundos
- Error rate > 1%
- Disk space < 20%
- Alertas no llegan

## 📞 Contactos de Emergencia

- **DevOps Lead**: [tu-email]
- **DBA**: [dba-email]  
- **Slack Channel**: #alerts-produccion
- **Escalación**: [manager-email]

## 📋 Métricas de Éxito

- **Uptime**: > 99.5%
- **Response Time**: < 2 segundos
- **Backup Success Rate**: 100%
- **RTO Actual**: < 15 minutos
- **RPO Actual**: < 24 horas