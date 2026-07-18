# Backups Multi-Región

## Objetivo
Backups automáticos diarios con replicación a 2 regiones (disaster recovery)

## Arquitectura
```
┌─────────────┐
│  PostgreSQL │
└──────┬──────┘
       │ pg_dump diario
       ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  S3 Primary │─────▶│ S3 Secondary│─────▶│ S3 Glacier  │
│  us-east-1  │      │  eu-west-1  │      │  (30 días)  │
└─────────────┘      └─────────────┘      └─────────────┘
```

## scripts/backup_db.sh

```bash
#!/bin/bash
set -e

# Variables
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/tmp/backups"
BACKUP_FILE="backup_${TIMESTAMP}.sql.gz"
S3_PRIMARY="s3://barbershop-backups-primary"
S3_SECONDARY="s3://barbershop-backups-secondary"

# Crear directorio temporal
mkdir -p ${BACKUP_DIR}

echo "[$(date)] Iniciando backup..."

# Backup PostgreSQL
PGPASSWORD=${DB_PASSWORD} pg_dump \
  -h ${DB_HOST} \
  -U ${DB_USER} \
  -d ${DB_NAME} \
  --format=custom \
  --compress=9 \
  --file=${BACKUP_DIR}/${BACKUP_FILE}

echo "[$(date)] Backup creado: ${BACKUP_FILE}"

# Subir a S3 primary
aws s3 cp ${BACKUP_DIR}/${BACKUP_FILE} ${S3_PRIMARY}/${BACKUP_FILE} \
  --storage-class STANDARD_IA

echo "[$(date)] Subido a S3 primary"

# Verificar integridad
aws s3api head-object \
  --bucket barbershop-backups-primary \
  --key ${BACKUP_FILE} \
  --checksum-mode ENABLED

echo "[$(date)] Integridad verificada"

# Limpiar local
rm -f ${BACKUP_DIR}/${BACKUP_FILE}

echo "[$(date)] Backup completado exitosamente"

# Notificar Slack (opcional)
if [ ! -z "${SLACK_WEBHOOK}" ]; then
  curl -X POST ${SLACK_WEBHOOK} \
    -H 'Content-Type: application/json' \
    -d "{\"text\":\"✅ Backup completado: ${BACKUP_FILE}\"}"
fi
```

## scripts/restore_db.sh

```bash
#!/bin/bash
set -e

if [ -z "$1" ]; then
  echo "Uso: ./restore_db.sh <backup_file>"
  echo "Ejemplo: ./restore_db.sh backup_20260226_120000.sql.gz"
  exit 1
fi

BACKUP_FILE=$1
BACKUP_DIR="/tmp/backups"
S3_PRIMARY="s3://barbershop-backups-primary"

echo "⚠️  ADVERTENCIA: Esto sobrescribirá la base de datos actual"
read -p "¿Continuar? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
  echo "Restore cancelado"
  exit 0
fi

# Descargar backup
mkdir -p ${BACKUP_DIR}
aws s3 cp ${S3_PRIMARY}/${BACKUP_FILE} ${BACKUP_DIR}/${BACKUP_FILE}

echo "[$(date)] Backup descargado"

# Restore
PGPASSWORD=${DB_PASSWORD} pg_restore \
  -h ${DB_HOST} \
  -U ${DB_USER} \
  -d ${DB_NAME} \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  ${BACKUP_DIR}/${BACKUP_FILE}

echo "[$(date)] Restore completado"

# Limpiar
rm -f ${BACKUP_DIR}/${BACKUP_FILE}

# Notificar
if [ ! -z "${SLACK_WEBHOOK}" ]; then
  curl -X POST ${SLACK_WEBHOOK} \
    -H 'Content-Type: application/json' \
    -d "{\"text\":\"⚠️ Restore ejecutado: ${BACKUP_FILE}\"}"
fi
```

## Terraform (AWS S3 + Replicación)

```hcl
# terraform/s3_backups.tf

# Bucket primary (us-east-1)
resource "aws_s3_bucket" "backups_primary" {
  bucket = "barbershop-backups-primary"
  
  tags = {
    Environment = "production"
    Purpose     = "database-backups"
  }
}

# Versionado
resource "aws_s3_bucket_versioning" "backups_primary" {
  bucket = aws_s3_bucket.backups_primary.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Encriptación
resource "aws_s3_bucket_server_side_encryption_configuration" "backups_primary" {
  bucket = aws_s3_bucket.backups_primary.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle (mover a Glacier después de 30 días)
resource "aws_s3_bucket_lifecycle_configuration" "backups_primary" {
  bucket = aws_s3_bucket.backups_primary.id
  
  rule {
    id     = "archive-old-backups"
    status = "Enabled"
    
    transition {
      days          = 30
      storage_class = "GLACIER"
    }
    
    expiration {
      days = 90
    }
  }
}

# Bucket secondary (eu-west-1)
resource "aws_s3_bucket" "backups_secondary" {
  provider = aws.eu-west-1
  bucket   = "barbershop-backups-secondary"
  
  tags = {
    Environment = "production"
    Purpose     = "database-backups-replica"
  }
}

# Replicación cross-region
resource "aws_s3_bucket_replication_configuration" "backups_replication" {
  bucket = aws_s3_bucket.backups_primary.id
  role   = aws_iam_role.replication.arn
  
  rule {
    id     = "replicate-all"
    status = "Enabled"
    
    destination {
      bucket        = aws_s3_bucket.backups_secondary.arn
      storage_class = "STANDARD_IA"
    }
  }
}

# IAM Role para replicación
resource "aws_iam_role" "replication" {
  name = "s3-backup-replication-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "s3.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "replication" {
  role = aws_iam_role.replication.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetReplicationConfiguration",
          "s3:ListBucket"
        ]
        Effect = "Allow"
        Resource = aws_s3_bucket.backups_primary.arn
      },
      {
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl"
        ]
        Effect = "Allow"
        Resource = "${aws_s3_bucket.backups_primary.arn}/*"
      },
      {
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete"
        ]
        Effect = "Allow"
        Resource = "${aws_s3_bucket.backups_secondary.arn}/*"
      }
    ]
  })
}
```

## Cron Job (Celery Beat)

```python
# backend/settings.py

CELERY_BEAT_SCHEDULE = {
    # ... tareas existentes
    'daily-database-backup': {
        'task': 'apps.core.tasks.backup_database',
        'schedule': crontab(hour=2, minute=0),  # 2:00 AM diario
    },
}
```

```python
# apps/core/tasks.py

import subprocess
from celery import shared_task
from django.conf import settings

@shared_task(bind=True, max_retries=3)
def backup_database(self):
    """
    Ejecuta backup diario de PostgreSQL
    """
    try:
        result = subprocess.run(
            ['/code/scripts/backup_db.sh'],
            capture_output=True,
            text=True,
            timeout=3600  # 1 hora max
        )
        
        if result.returncode != 0:
            raise Exception(f"Backup failed: {result.stderr}")
        
        return f"Backup completed: {result.stdout}"
        
    except Exception as e:
        # Retry con exponential backoff
        raise self.retry(exc=e, countdown=300)  # 5 min
```

## Testing

### 1. Test backup manual
```bash
cd /path/to/project
./scripts/backup_db.sh
```

### 2. Test restore
```bash
# Listar backups disponibles
aws s3 ls s3://barbershop-backups-primary/

# Restore
./scripts/restore_db.sh backup_20260226_120000.sql.gz
```

### 3. Test replicación cross-region
```bash
# Verificar que archivo existe en ambas regiones
aws s3 ls s3://barbershop-backups-primary/ --region us-east-1
aws s3 ls s3://barbershop-backups-secondary/ --region eu-west-1
```

## Costo AWS
- S3 Standard-IA: $0.0125/GB/mes
- S3 Glacier: $0.004/GB/mes
- Replicación cross-region: $0.02/GB
- **Estimado (100GB backups):** ~$5-10/mes

## Monitoreo

### CloudWatch Alarm
```hcl
resource "aws_cloudwatch_metric_alarm" "backup_failed" {
  alarm_name          = "database-backup-failed"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "NumberOfObjects"
  namespace           = "AWS/S3"
  period              = "86400"  # 24 horas
  statistic           = "Average"
  threshold           = "1"
  alarm_description   = "No se creó backup en últimas 24h"
  
  dimensions = {
    BucketName = aws_s3_bucket.backups_primary.id
  }
}
```

## Próximos pasos
- Semana 2: Load balancer + Secrets Manager + APM
