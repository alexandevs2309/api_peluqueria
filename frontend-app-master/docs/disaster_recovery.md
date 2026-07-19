# Disaster Recovery Plan - SaaS Multi-tenant

**Versión:** 1.0  
**Última actualización:** 2024  
**Responsable:** CTO  
**Revisión:** Trimestral

---

## 1. OBJETIVOS DE RECUPERACIÓN

### RTO (Recovery Time Objective)

| Componente | RTO | Justificación |
|------------|-----|---------------|
| Base de datos PostgreSQL | **4 horas** | Crítico - Sin DB no hay servicio |
| API Backend (Django) | **30 minutos** | Crítico - Core del negocio |
| Celery Workers | **1 hora** | Alto - Pagos y notificaciones |
| Redis Cache | **15 minutos** | Medio - Degrada performance |
| Archivos estáticos/media | **2 horas** | Bajo - No bloquea operación |

**RTO Global del Sistema: 4 horas**

### RPO (Recovery Point Objective)

| Tipo de dato | RPO | Método |
|--------------|-----|--------|
| Datos transaccionales (pagos, usuarios) | **15 minutos** | WAL archiving continuo |
| Datos operacionales (logs, analytics) | **1 hora** | Snapshots incrementales |
| Configuración y código | **0 minutos** | Git + IaC |
| Archivos subidos por usuarios | **1 hora** | S3 versioning |

**RPO Global: 15 minutos**

---

## 2. ESTRATEGIA DE BACKUPS

### 2.1 PostgreSQL

#### Backups Automáticos

```bash
# Configuración PostgreSQL (postgresql.conf)
wal_level = replica
archive_mode = on
archive_command = 'aws s3 cp %p s3://backup-bucket/wal/%f'
archive_timeout = 300  # 5 minutos
```

**Frecuencia:**
- **WAL archiving:** Continuo (cada 5 min o 16MB)
- **Full backup:** Diario a las 02:00 UTC
- **Incremental:** Cada 6 horas (02:00, 08:00, 14:00, 20:00)

**Script de backup diario:**

```bash
#!/bin/bash
# /opt/scripts/pg_backup_daily.sh

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/tmp/pg_backup_${TIMESTAMP}"
S3_BUCKET="s3://saas-backups-prod"
RETENTION_DAYS=30

# Base backup con pg_basebackup
pg_basebackup -D ${BACKUP_DIR} -Ft -z -P -U backup_user

# Upload a S3
aws s3 sync ${BACKUP_DIR} ${S3_BUCKET}/daily/${TIMESTAMP}/ \
  --storage-class STANDARD_IA

# Cleanup local
rm -rf ${BACKUP_DIR}

# Cleanup backups antiguos
aws s3 ls ${S3_BUCKET}/daily/ | \
  awk '{print $2}' | \
  head -n -${RETENTION_DAYS} | \
  xargs -I {} aws s3 rm --recursive ${S3_BUCKET}/daily/{}

# Verificación
aws s3 ls ${S3_BUCKET}/daily/${TIMESTAMP}/ || exit 1

echo "Backup completado: ${TIMESTAMP}"
```

**Cron:**
```cron
0 2 * * * /opt/scripts/pg_backup_daily.sh >> /var/log/pg_backup.log 2>&1
```

#### Retención

| Tipo | Retención | Storage Class |
|------|-----------|---------------|
| WAL archives | 7 días | STANDARD |
| Daily backups | 30 días | STANDARD_IA |
| Weekly backups | 90 días | GLACIER |
| Monthly backups | 1 año | DEEP_ARCHIVE |

**Script de retención:**

```bash
#!/bin/bash
# /opt/scripts/pg_backup_retention.sh

S3_BUCKET="s3://saas-backups-prod"

# Promover backup diario a weekly (domingos)
if [ $(date +%u) -eq 7 ]; then
  LATEST=$(aws s3 ls ${S3_BUCKET}/daily/ | tail -1 | awk '{print $2}')
  aws s3 sync ${S3_BUCKET}/daily/${LATEST} ${S3_BUCKET}/weekly/${LATEST}
fi

# Promover backup weekly a monthly (día 1)
if [ $(date +%d) -eq 01 ]; then
  LATEST=$(aws s3 ls ${S3_BUCKET}/weekly/ | tail -1 | awk '{print $2}')
  aws s3 sync ${S3_BUCKET}/weekly/${LATEST} ${S3_BUCKET}/monthly/${LATEST} \
    --storage-class DEEP_ARCHIVE
fi

# Cleanup WAL > 7 días
find /var/lib/postgresql/wal_archive -mtime +7 -delete

# Cleanup weekly > 90 días
aws s3 ls ${S3_BUCKET}/weekly/ | \
  awk '{print $2}' | \
  head -n -13 | \
  xargs -I {} aws s3 rm --recursive ${S3_BUCKET}/weekly/{}

# Cleanup monthly > 365 días
aws s3 ls ${S3_BUCKET}/monthly/ | \
  awk '{print $2}' | \
  head -n -12 | \
  xargs -I {} aws s3 rm --recursive ${S3_BUCKET}/monthly/{}
```

### 2.2 Archivos de Usuario (S3)

```bash
# Habilitar versioning
aws s3api put-bucket-versioning \
  --bucket saas-media-prod \
  --versioning-configuration Status=Enabled

# Lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
  --bucket saas-media-prod \
  --lifecycle-configuration file://s3-lifecycle.json
```

**s3-lifecycle.json:**
```json
{
  "Rules": [
    {
      "Id": "archive-old-versions",
      "Status": "Enabled",
      "NoncurrentVersionTransitions": [
        {
          "NoncurrentDays": 30,
          "StorageClass": "GLACIER"
        }
      ],
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 90
      }
    }
  ]
}
```

### 2.3 Configuración y Código

- **Git:** Todo en repositorio privado
- **IaC:** Terraform state en S3 con versioning
- **Secrets:** AWS Secrets Manager con rotación automática
- **Docker images:** Registry con retention de 30 tags

### 2.4 Redis

**No requiere backup persistente:**
- Datos en cache son regenerables
- Celery tasks en PostgreSQL como fallback
- Reconstrucción automática en <15 min

---

## 3. PROCEDIMIENTOS DE RESTORE

### 3.1 Restore PostgreSQL Completo

**Tiempo estimado: 2-4 horas**

#### Paso 1: Preparar servidor destino

```bash
# Detener PostgreSQL si está corriendo
systemctl stop postgresql

# Limpiar data directory
rm -rf /var/lib/postgresql/14/main/*
```

#### Paso 2: Descargar último backup

```bash
# Identificar último backup válido
LATEST_BACKUP=$(aws s3 ls s3://saas-backups-prod/daily/ | tail -1 | awk '{print $2}')

# Descargar
aws s3 sync s3://saas-backups-prod/daily/${LATEST_BACKUP} /tmp/restore/

# Extraer
cd /var/lib/postgresql/14/main
tar -xzf /tmp/restore/base.tar.gz
```

#### Paso 3: Configurar recovery

```bash
# Crear recovery.conf (PostgreSQL <12) o recovery.signal (PostgreSQL 12+)
touch /var/lib/postgresql/14/main/recovery.signal

# Configurar postgresql.auto.conf
cat >> /var/lib/postgresql/14/main/postgresql.auto.conf <<EOF
restore_command = 'aws s3 cp s3://saas-backups-prod/wal/%f %p'
recovery_target_time = '2024-01-15 14:30:00'  # Opcional: PITR
EOF
```

#### Paso 4: Iniciar recovery

```bash
# Cambiar ownership
chown -R postgres:postgres /var/lib/postgresql/14/main

# Iniciar PostgreSQL
systemctl start postgresql

# Monitorear logs
tail -f /var/log/postgresql/postgresql-14-main.log
```

#### Paso 5: Validar integridad

```bash
# Conectar a DB
psql -U postgres

-- Verificar tablas críticas
SELECT COUNT(*) FROM tenants;
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM subscriptions WHERE status='active';

-- Verificar último registro
SELECT MAX(created_at) FROM payments;

-- Verificar integridad
\dt+  -- Listar tablas y tamaños
```

#### Paso 6: Promover a producción

```bash
# Promover replica a master (si aplica)
SELECT pg_promote();

# Actualizar DNS/Load Balancer
# Actualizar connection string en aplicación
# Reiniciar servicios Django
```

### 3.2 Restore Point-in-Time (PITR)

**Escenario:** Corrupción de datos detectada a las 14:35, último estado bueno a las 14:20

```bash
# En recovery.conf o postgresql.auto.conf
recovery_target_time = '2024-01-15 14:20:00'
recovery_target_action = 'promote'

# Iniciar recovery (pasos 1-4 anteriores)
# PostgreSQL se detendrá automáticamente en el punto especificado
```

### 3.3 Restore Tabla Individual

**Tiempo estimado: 30 minutos**

```bash
# Restaurar en DB temporal
createdb temp_restore
pg_restore -d temp_restore /tmp/restore/base.tar.gz

# Exportar tabla específica
pg_dump -t payments temp_restore > payments_restore.sql

# Importar en producción (con precaución)
psql production_db < payments_restore.sql

# Cleanup
dropdb temp_restore
```

---

## 4. PROCEDIMIENTOS DE FAILOVER

### 4.1 Failover Automático (Replication)

**Arquitectura:**
```
Primary DB (RW) → Streaming Replication → Standby DB (RO)
                ↓
              WAL Archive (S3)
```

**Configuración Primary:**

```bash
# postgresql.conf
wal_level = replica
max_wal_senders = 3
wal_keep_size = 1GB
synchronous_commit = on
synchronous_standby_names = 'standby1'
```

**Configuración Standby:**

```bash
# Crear standby desde primary
pg_basebackup -h primary-db -D /var/lib/postgresql/14/main -U replication -P

# standby.signal
touch /var/lib/postgresql/14/main/standby.signal

# postgresql.auto.conf
primary_conninfo = 'host=primary-db port=5432 user=replication password=xxx'
restore_command = 'aws s3 cp s3://saas-backups-prod/wal/%f %p'
```

**Script de failover automático:**

```bash
#!/bin/bash
# /opt/scripts/pg_failover.sh

PRIMARY_HOST="primary-db.internal"
STANDBY_HOST="standby-db.internal"

# Verificar si primary está caído
if ! pg_isready -h ${PRIMARY_HOST} -t 5; then
  echo "PRIMARY DOWN - Iniciando failover"
  
  # Promover standby a primary
  ssh postgres@${STANDBY_HOST} "pg_ctl promote -D /var/lib/postgresql/14/main"
  
  # Esperar promoción
  sleep 10
  
  # Actualizar DNS (Route53)
  aws route53 change-resource-record-sets \
    --hosted-zone-id Z1234567890ABC \
    --change-batch file://failover-dns.json
  
  # Notificar equipo
  curl -X POST https://hooks.slack.com/services/XXX \
    -d '{"text":"🚨 FAILOVER EJECUTADO: Standby promovido a Primary"}'
  
  # Actualizar configuración aplicación
  kubectl set env deployment/django-api DATABASE_HOST=${STANDBY_HOST}
  
  echo "Failover completado"
else
  echo "Primary OK"
fi
```

**Cron de health check:**
```cron
*/2 * * * * /opt/scripts/pg_failover.sh >> /var/log/pg_failover.log 2>&1
```

### 4.2 Failover Manual

**Checklist de ejecución:**

- [ ] **Confirmar primary irrecuperable** (timeout >5 min)
- [ ] **Verificar lag de replicación** (`SELECT pg_last_wal_receive_lsn()`)
- [ ] **Promover standby:** `pg_ctl promote`
- [ ] **Actualizar DNS:** TTL 60s, cambiar A record
- [ ] **Actualizar app config:** DATABASE_HOST en secrets
- [ ] **Reiniciar pods Django:** `kubectl rollout restart deployment/django-api`
- [ ] **Verificar conectividad:** Health checks OK
- [ ] **Notificar stakeholders:** Slack + Email
- [ ] **Documentar incidente:** Post-mortem

**Tiempo total: 15-30 minutos**

---

## 5. PROCEDIMIENTOS DE EMERGENCIA

### 5.1 Caída Total de Base de Datos

**Síntomas:**
- Health checks fallan
- Logs: "connection refused" / "server closed connection"
- Monitoring: DB CPU/Memory flatline

**Procedimiento:**

```bash
# 1. Verificar estado
systemctl status postgresql
journalctl -u postgresql -n 50

# 2. Intentar restart
systemctl restart postgresql

# 3. Si falla, verificar logs
tail -100 /var/log/postgresql/postgresql-14-main.log

# 4. Problemas comunes:
# - Disco lleno: df -h
# - Corrupción: pg_resetwal (ÚLTIMO RECURSO)
# - OOM killer: dmesg | grep -i kill

# 5. Si irrecuperable → RESTORE desde backup (Sección 3.1)
```

**Tiempo de decisión: 15 minutos**  
Si no se resuelve en 15 min → Ejecutar restore completo

### 5.2 Corrupción de Datos

**Síntomas:**
- Queries fallan con "invalid page header"
- Datos inconsistentes entre tablas
- Reportes de usuarios sobre datos perdidos

**Procedimiento:**

```bash
# 1. DETENER ESCRITURAS INMEDIATAMENTE
# Poner aplicación en modo read-only
kubectl scale deployment/django-api --replicas=0

# 2. Identificar alcance
psql -c "SELECT * FROM pg_stat_database WHERE datname='production';"

# 3. Intentar reparación (solo si corrupción menor)
reindexdb --all
vacuumdb --all --analyze

# 4. Si falla → PITR al último punto bueno
# Ver sección 3.2

# 5. Validar integridad post-restore
python manage.py check_data_integrity
```

**Decisión crítica:**  
- Corrupción <1 tabla → Restore tabla individual
- Corrupción >1 tabla → PITR completo

### 5.3 Caída de Celery Workers

**Síntomas:**
- Tareas pendientes acumulándose
- Pagos no procesados
- Emails no enviados

**Procedimiento:**

```bash
# 1. Verificar workers
celery -A config inspect active
celery -A config inspect stats

# 2. Verificar queue depth
redis-cli LLEN celery

# 3. Restart workers
kubectl rollout restart deployment/celery-worker

# 4. Si persiste, purge tareas corruptas
celery -A config purge

# 5. Re-queue tareas críticas
python manage.py requeue_failed_payments --last-hour=2
```

**Prioridad de recuperación:**
1. Payments queue (crítico)
2. Notifications queue (alto)
3. Reports queue (bajo)

### 5.4 Ataque o Security Breach

**Procedimiento INMEDIATO:**

```bash
# 1. AISLAR SISTEMA (< 5 minutos)
# Bloquear tráfico externo
aws ec2 modify-security-group-rules --group-id sg-xxx --remove

# 2. PRESERVAR EVIDENCIA
# Snapshot de instancias
aws ec2 create-snapshot --volume-id vol-xxx --description "breach-evidence"

# Copiar logs
aws s3 sync /var/log/ s3://incident-logs/$(date +%Y%m%d)/

# 3. ROTAR CREDENCIALES
aws secretsmanager rotate-secret --secret-id prod/db/password
aws secretsmanager rotate-secret --secret-id prod/stripe/api-key

# 4. ANÁLISIS FORENSE
# Revisar accesos sospechosos
SELECT * FROM audit_log WHERE created_at > NOW() - INTERVAL '24 hours'
  ORDER BY created_at DESC;

# Revisar queries anómalas
SELECT * FROM pg_stat_statements 
  WHERE calls > 1000 AND mean_exec_time > 1000;

# 5. NOTIFICACIÓN LEGAL
# Contactar legal team si hay exposición de PII
# Preparar notificación GDPR (72 horas)
```

**Equipo de respuesta:**
- CTO (líder)
- DevOps (contención)
- Legal (compliance)
- Customer Success (comunicación)

---

## 6. TESTING Y VALIDACIÓN

### 6.1 Checklist Mensual de Pruebas

**Ejecutar primer lunes de cada mes**

#### Test 1: Restore de Backup

- [ ] Descargar último backup daily
- [ ] Restaurar en ambiente staging
- [ ] Validar integridad de datos
- [ ] Medir tiempo de restore (debe ser <4h)
- [ ] Documentar resultados

```bash
# Script de test
#!/bin/bash
# /opt/scripts/test_restore_monthly.sh

START_TIME=$(date +%s)

# Restore en staging
./pg_restore_staging.sh

# Validar
psql staging -c "SELECT COUNT(*) FROM tenants;" || exit 1
psql staging -c "SELECT COUNT(*) FROM users;" || exit 1

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "Restore completado en ${DURATION} segundos"

if [ ${DURATION} -gt 14400 ]; then
  echo "⚠️  WARNING: Restore excedió RTO de 4 horas"
fi
```

#### Test 2: Failover Simulado

- [ ] Programar ventana de mantenimiento
- [ ] Detener primary DB manualmente
- [ ] Verificar promoción automática de standby
- [ ] Validar conectividad de aplicación
- [ ] Medir tiempo total (debe ser <30min)
- [ ] Revertir a configuración original

#### Test 3: Validación de Backups

- [ ] Verificar existencia de backups (daily, weekly, monthly)
- [ ] Validar checksums de archivos
- [ ] Confirmar WAL archives completos
- [ ] Revisar logs de backup por errores

```bash
# Validación automática
#!/bin/bash
# /opt/scripts/validate_backups.sh

# Verificar backup de hoy
TODAY=$(date +%Y%m%d)
aws s3 ls s3://saas-backups-prod/daily/ | grep ${TODAY} || {
  echo "❌ Backup de hoy no encontrado"
  exit 1
}

# Verificar WAL continuidad
LAST_WAL=$(aws s3 ls s3://saas-backups-prod/wal/ | tail -1 | awk '{print $4}')
AGE=$(( $(date +%s) - $(date -r ${LAST_WAL} +%s) ))

if [ ${AGE} -gt 600 ]; then
  echo "⚠️  Último WAL tiene más de 10 minutos"
fi

echo "✅ Backups validados"
```

#### Test 4: Recovery de Tabla Individual

- [ ] Seleccionar tabla no crítica
- [ ] Simular corrupción (DELETE)
- [ ] Restaurar desde backup
- [ ] Validar datos restaurados
- [ ] Medir tiempo (debe ser <30min)

### 6.2 Checklist de Auditoría Trimestral

**Ejecutar cada trimestre (Q1, Q2, Q3, Q4)**

#### Auditoría de Backups

- [ ] Revisar retención policy (30/90/365 días)
- [ ] Validar costos de storage S3
- [ ] Confirmar encriptación habilitada (AES-256)
- [ ] Verificar cross-region replication
- [ ] Revisar access logs de S3

#### Auditoría de Procedimientos

- [ ] Revisar y actualizar runbooks
- [ ] Validar contactos de emergencia actualizados
- [ ] Confirmar accesos de equipo on-call
- [ ] Revisar post-mortems de incidentes
- [ ] Actualizar matriz de riesgos

#### Auditoría de Compliance

- [ ] Documentar RPO/RTO alcanzados vs objetivo
- [ ] Revisar audit logs de acceso a backups
- [ ] Validar rotación de credenciales
- [ ] Confirmar tests de restore ejecutados
- [ ] Preparar reporte para stakeholders

#### Métricas Clave

```sql
-- Generar reporte trimestral
SELECT 
  DATE_TRUNC('month', incident_date) as month,
  COUNT(*) as total_incidents,
  AVG(resolution_time_minutes) as avg_resolution_time,
  MAX(resolution_time_minutes) as max_resolution_time,
  SUM(CASE WHEN met_rto = true THEN 1 ELSE 0 END) as met_rto_count
FROM incident_log
WHERE incident_date >= NOW() - INTERVAL '3 months'
GROUP BY month
ORDER BY month;
```

---

## 7. MATRIZ DE RIESGOS

| Riesgo | Probabilidad | Impacto | Severidad | Mitigación | RTO | RPO |
|--------|--------------|---------|-----------|------------|-----|-----|
| **Fallo hardware DB** | Media | Crítico | 🔴 Alta | Replication + Backups | 30min | 15min |
| **Corrupción datos** | Baja | Crítico | 🔴 Alta | PITR + Checksums | 4h | 15min |
| **Eliminación accidental** | Media | Alto | 🟡 Media | Soft deletes + Backups | 1h | 15min |
| **Ataque ransomware** | Baja | Crítico | 🔴 Alta | Immutable backups + Segmentación | 4h | 1h |
| **Fallo región cloud** | Muy Baja | Crítico | 🔴 Alta | Cross-region backups | 8h | 1h |
| **Error humano (DROP)** | Media | Alto | 🟡 Media | Permisos + Audit log | 2h | 15min |
| **Fallo Celery workers** | Media | Medio | 🟢 Baja | Auto-scaling + Queue monitoring | 15min | 0min |
| **Disco lleno** | Media | Alto | 🟡 Media | Monitoring + Auto-cleanup | 30min | 0min |
| **Breach de seguridad** | Baja | Crítico | 🔴 Alta | Secrets rotation + Audit | 2h | N/A |
| **Pérdida acceso AWS** | Muy Baja | Crítico | 🔴 Alta | Multi-account + MFA | 4h | 1h |

### Cálculo de Severidad

**Severidad = Probabilidad × Impacto**

- 🔴 **Alta (>15):** Requiere plan de mitigación activo
- 🟡 **Media (8-15):** Monitoreo y procedimientos documentados
- 🟢 **Baja (<8):** Aceptable con monitoreo básico

---

## 8. CONTACTOS DE EMERGENCIA

### Equipo Interno

| Rol | Nombre | Teléfono | Email | Horario |
|-----|--------|----------|-------|---------|
| CTO (Primary) | [NOMBRE] | +XX XXX XXX XXX | cto@company.com | 24/7 |
| DevOps Lead | [NOMBRE] | +XX XXX XXX XXX | devops@company.com | 24/7 |
| Backend Lead | [NOMBRE] | +XX XXX XXX XXX | backend@company.com | On-call |
| Security Lead | [NOMBRE] | +XX XXX XXX XXX | security@company.com | On-call |

### Proveedores Externos

| Servicio | Contacto | Soporte | SLA |
|----------|----------|---------|-----|
| AWS Support | Enterprise Support | +1-XXX-XXX-XXXX | <15min |
| Database Consultant | [EMPRESA] | support@dbconsult.com | <1h |
| Security Incident Response | [EMPRESA] | incident@security.com | <30min |

### Escalación

1. **Nivel 1 (0-15 min):** DevOps on-call intenta resolución
2. **Nivel 2 (15-30 min):** Escala a Backend Lead + CTO
3. **Nivel 3 (30+ min):** Activa proveedores externos + Stakeholders

---

## 9. MONITOREO Y ALERTAS

### Alertas Críticas (PagerDuty)

```yaml
# alerts.yml
alerts:
  - name: database_down
    condition: pg_up == 0
    duration: 2m
    severity: critical
    action: page_oncall
    
  - name: replication_lag
    condition: pg_replication_lag_seconds > 300
    duration: 5m
    severity: critical
    action: page_oncall
    
  - name: backup_failed
    condition: backup_last_success_timestamp < now() - 25h
    severity: critical
    action: page_oncall
    
  - name: disk_space_critical
    condition: disk_usage_percent > 90
    duration: 5m
    severity: high
    action: page_oncall
```

### Dashboard de DR

**Métricas clave a monitorear:**

- ✅ Último backup exitoso (timestamp)
- ✅ Replication lag (segundos)
- ✅ WAL archive status
- ✅ Disk space (%)
- ✅ Backup size trend
- ✅ Restore test results (pass/fail)

---

## 10. CHANGELOG Y VERSIONES

| Versión | Fecha | Cambios | Autor |
|---------|-------|---------|-------|
| 1.0 | 2024-01 | Versión inicial | CTO |
| | | | |
| | | | |

---

## APÉNDICES

### A. Scripts de Automatización

Ubicación: `/opt/scripts/disaster-recovery/`

- `pg_backup_daily.sh` - Backup diario automatizado
- `pg_backup_retention.sh` - Gestión de retención
- `pg_restore_staging.sh` - Restore en staging
- `pg_failover.sh` - Failover automático
- `validate_backups.sh` - Validación de backups
- `test_restore_monthly.sh` - Test mensual

### B. Configuraciones

Ubicación: `/etc/postgresql/14/main/`

- `postgresql.conf` - Configuración principal
- `pg_hba.conf` - Autenticación
- `recovery.conf.template` - Template para recovery

### C. Runbooks Detallados

Ubicación: `docs/runbooks/`

- `runbook_db_restore.md`
- `runbook_failover.md`
- `runbook_security_incident.md`
- `runbook_data_corruption.md`

---

**FIN DEL DOCUMENTO**

**Próxima revisión:** [FECHA + 3 meses]  
**Aprobado por:** [CTO]  
**Fecha de aprobación:** [FECHA]
