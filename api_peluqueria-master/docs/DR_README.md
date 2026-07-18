# Disaster Recovery - Guía de Uso

## Estructura de Archivos

```
ops/
├── backup/
│   └── pg_backup_daily.sh          # Backup diario automatizado
├── restore/
│   ├── pg_restore_full.sh          # Restore completo
│   └── pg_restore_pitr.sh          # Point-in-Time Recovery
└── monitoring/
    └── validate_backups.sh         # Validación de backups
```

## Configuración Inicial

### 1. Variables de Entorno

```bash
export DB_HOST="localhost"
export DB_USER="backup_user"
export S3_BUCKET="s3://saas-backups-prod"
export SLACK_WEBHOOK="https://hooks.slack.com/services/XXX"
```

### 2. Permisos de Ejecución

```bash
chmod +x ops/backup/*.sh
chmod +x ops/restore/*.sh
chmod +x ops/monitoring/*.sh
```

### 3. Configurar Cron

```bash
# Backup diario a las 2 AM
0 2 * * * /path/to/ops/backup/pg_backup_daily.sh

# Validación diaria a las 3 AM
0 3 * * * /path/to/ops/monitoring/validate_backups.sh
```

## Uso de Scripts

### Backup Manual

```bash
# Ejecutar backup inmediato
./ops/backup/pg_backup_daily.sh
```

### Restore Completo

```bash
# Listar backups disponibles
./ops/restore/pg_restore_full.sh

# Restaurar backup específico
./ops/restore/pg_restore_full.sh 20240115_020000
```

### Point-in-Time Recovery

```bash
# Restaurar a punto específico en el tiempo
./ops/restore/pg_restore_pitr.sh 20240115_020000 '2024-01-15 14:20:00'
```

### Validar Backups

```bash
# Ejecutar validación
./ops/monitoring/validate_backups.sh
```

## Escenarios de Emergencia

### Escenario 1: Caída Total de DB

```bash
# 1. Verificar que DB está caída
systemctl status postgresql

# 2. Intentar restart
systemctl restart postgresql

# 3. Si falla, ejecutar restore
./ops/restore/pg_restore_full.sh [TIMESTAMP]
```

### Escenario 2: Corrupción de Datos

```bash
# 1. Detener escrituras (escalar app a 0)
kubectl scale deployment/django-api --replicas=0

# 2. Identificar último punto bueno
# Revisar logs o consultar con equipo

# 3. Ejecutar PITR
./ops/restore/pg_restore_pitr.sh [BACKUP] '[TARGET_TIME]'

# 4. Validar datos
psql -U postgres -c "SELECT COUNT(*) FROM tenants;"

# 5. Restaurar app
kubectl scale deployment/django-api --replicas=3
```

### Escenario 3: Eliminación Accidental

```bash
# Si fue hace menos de 15 minutos
./ops/restore/pg_restore_pitr.sh [BACKUP] '[TIME_BEFORE_DELETE]'
```

## Monitoreo

### Verificar Último Backup

```bash
aws s3 ls s3://saas-backups-prod/daily/ | tail -1
```

### Verificar WAL Archiving

```bash
aws s3 ls s3://saas-backups-prod/wal/ | tail -5
```

### Verificar Logs

```bash
tail -f /var/log/pg_backup.log
tail -f /var/log/pg_restore.log
tail -f /var/log/backup_validation.log
```

## Troubleshooting

### Error: "Espacio insuficiente"

```bash
# Limpiar /tmp
rm -rf /tmp/pg_backup_*
rm -rf /tmp/restore/*

# Verificar espacio
df -h /tmp
```

### Error: "Backup no encontrado en S3"

```bash
# Listar backups disponibles
aws s3 ls s3://saas-backups-prod/daily/

# Verificar credenciales AWS
aws sts get-caller-identity
```

### Error: "PostgreSQL no responde después de restore"

```bash
# Revisar logs
tail -100 /var/log/postgresql/postgresql-14-main.log

# Verificar permisos
ls -la /var/lib/postgresql/14/main

# Verificar configuración
cat /var/lib/postgresql/14/main/postgresql.auto.conf
```

## Contactos de Emergencia

- **CTO:** [TELÉFONO]
- **DevOps Lead:** [TELÉFONO]
- **AWS Support:** +1-XXX-XXX-XXXX

## Documentación Adicional

- [disaster_recovery.md](../../disaster_recovery.md) - Plan completo de DR
- [dr_monthly_test_checklist.md](../../dr_monthly_test_checklist.md) - Tests mensuales
- [dr_quarterly_audit_checklist.md](../../dr_quarterly_audit_checklist.md) - Auditoría trimestral
