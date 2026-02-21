# Procedimientos de Backup y Restore - SaaS Peluquería

## RPO y RTO Definidos

- **RPO (Recovery Point Objective)**: 24 horas
- **RTO (Recovery Time Objective)**: 15 minutos

## 1. Backup Automático

### Configuración
```bash
# Cron job (ejecutar como root)
crontab -e
# Agregar:
0 2 * * * /path/to/ops/backup/backup_db.sh >> /var/log/backup.log 2>&1
```

### Verificación Manual
```bash
# Ejecutar backup manual
./ops/backup/backup_db.sh

# Verificar backups existentes
ls -la /backups/
```

### Logs
```bash
# Ver logs de backup
tail -f /backups/backup.log

# Ver métricas de último backup
cat /tmp/backup_metrics.prom
```

## 2. Procedimiento de Restore

### Restore de Prueba (Recomendado)
```bash
# Listar backups disponibles
ls -la /backups/*.sql.gz

# Restore a DB temporal
./ops/restore/restore_db.sh /backups/peluqueria_db_20240115_020001.sql.gz

# Verificar datos en DB temporal
psql -h localhost -U postgres -d peluqueria_db_restore_20240115_120000
```

### Restore de Producción (CRÍTICO)
```bash
# 1. DETENER APLICACIÓN
docker-compose stop web celery

# 2. Backup actual por seguridad
pg_dump -h localhost -U postgres peluqueria_db | gzip > /backups/emergency_backup_$(date +%Y%m%d_%H%M%S).sql.gz

# 3. Restore
./ops/restore/restore_db.sh /backups/peluqueria_db_YYYYMMDD_HHMMSS.sql.gz peluqueria_db_new

# 4. Intercambiar bases de datos
psql -h localhost -U postgres -c "ALTER DATABASE peluqueria_db RENAME TO peluqueria_db_old;"
psql -h localhost -U postgres -c "ALTER DATABASE peluqueria_db_new RENAME TO peluqueria_db;"

# 5. REINICIAR APLICACIÓN
docker-compose start web celery

# 6. Verificar funcionamiento
curl http://localhost/health/
```

## 3. Monitoreo y Alertas

### Health Check
```bash
# Verificar estado general
curl http://localhost/health/ | jq

# Verificar métricas
curl http://localhost/metrics/ | jq
```

### Configurar Alertas
```bash
# Configurar variables de entorno
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
export ALERT_EMAIL="admin@tuempresa.com"

# Cron job para monitoreo (cada 5 minutos)
*/5 * * * * /path/to/ops/monitoring/service_monitor.sh
```

## 4. Comandos de Emergencia

### Verificar Estado de Servicios
```bash
# Docker containers
docker ps
docker-compose ps

# Logs en tiempo real
docker-compose logs -f web
docker-compose logs -f db
docker-compose logs -f redis
docker-compose logs -f celery
```

### Reinicio de Emergencia
```bash
# Reinicio completo
docker-compose down
docker-compose up -d

# Reinicio solo aplicación
docker-compose restart web celery
```

### Verificar Conectividad
```bash
# Base de datos
docker exec -it $(docker ps -q -f name=db) pg_isready -U postgres

# Redis
docker exec -it $(docker ps -q -f name=redis) redis-cli ping

# Celery workers
docker exec -it $(docker ps -q -f name=celery) celery -A backend inspect active
```

## 5. Métricas Críticas a Monitorear

### Aplicación
- Response time del health endpoint < 2 segundos
- Error rate < 1% (últimos 5 minutos)
- Uptime > 99.5%

### Base de Datos
- Conexiones activas < 80% del máximo
- Query time promedio < 100ms
- Backup exitoso diario

### Infraestructura
- CPU usage < 80%
- Memory usage < 85%
- Disk usage < 80%
- Network latency < 50ms

## 6. Escalación de Incidentes

### Severidad CRITICAL
- DB no disponible
- Aplicación completamente caída
- Pérdida de datos
- **Acción**: Llamar inmediatamente + Slack

### Severidad HIGH
- Degradación significativa de performance
- Celery workers caídos
- Redis no disponible
- **Acción**: Slack + Email

### Severidad WARNING
- Disk space > 80%
- Error rate elevado pero no crítico
- **Acción**: Email

## 7. Testing de Procedimientos

### Test Mensual de Backup/Restore
```bash
# 1. Ejecutar backup
./ops/backup/backup_db.sh

# 2. Restore a ambiente de prueba
./ops/restore/restore_db.sh [último_backup] test_restore_db

# 3. Verificar integridad de datos
psql -h localhost -U postgres -d test_restore_db -c "SELECT COUNT(*) FROM django_migrations;"

# 4. Limpiar
dropdb -h localhost -U postgres test_restore_db
```

### Test de Alertas
```bash
# Simular caída de servicio
docker-compose stop web

# Verificar que lleguen alertas (5 minutos máximo)
# Restaurar servicio
docker-compose start web
```