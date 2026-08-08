# PostgreSQL High Availability Setup

## Objetivo
Configurar PostgreSQL con streaming replication (1 primary + 1 replica read-only)

## Arquitectura
```
┌─────────────┐      ┌─────────────┐
│  Primary    │─────▶│  Replica    │
│  (Write)    │      │  (Read)     │
└─────────────┘      └─────────────┘
```

## Opción 1: Docker Compose (Desarrollo/Staging)

### docker-compose.yml
```yaml
services:
  db-primary:
    image: postgres:16
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_REPLICATION_USER: replicator
      POSTGRES_REPLICATION_PASSWORD: ${REPLICATION_PASSWORD}
    command: |
      postgres
      -c wal_level=replica
      -c max_wal_senders=3
      -c max_replication_slots=3
      -c hot_standby=on
    volumes:
      - postgres_primary_data:/var/lib/postgresql/data
    networks:
      - backend

  db-replica:
    image: postgres:16
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      PGUSER: ${DB_USER}
      PGPASSWORD: ${DB_PASSWORD}
    command: |
      bash -c "
      until pg_basebackup --pgdata=/var/lib/postgresql/data -R --slot=replication_slot --host=db-primary --port=5432
      do
        echo 'Waiting for primary to connect...'
        sleep 1s
      done
      echo 'Backup done, starting replica...'
      chmod 0700 /var/lib/postgresql/data
      postgres
      "
    depends_on:
      - db-primary
    volumes:
      - postgres_replica_data:/var/lib/postgresql/data
    networks:
      - backend

volumes:
  postgres_primary_data:
  postgres_replica_data:
```

### settings.py - Database Router
```python
# backend/settings.py

DATABASES = {
    'default': {
        'ENGINE': 'django_prometheus.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST', default='db-primary'),
        'PORT': env('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'
        }
    },
    'replica': {
        'ENGINE': 'django_prometheus.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_REPLICA_HOST', default='db-replica'),
        'PORT': env('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'
        }
    }
}

DATABASE_ROUTERS = ['backend.db_router.PrimaryReplicaRouter']
```

### backend/db_router.py
```python
class PrimaryReplicaRouter:
    """
    Router para dirigir reads a replica y writes a primary
    """
    
    def db_for_read(self, model, **hints):
        """
        Reads van a replica (si está disponible)
        """
        return 'replica'
    
    def db_for_write(self, model, **hints):
        """
        Writes siempre van a primary
        """
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        """
        Permitir relaciones entre objetos de ambas DBs
        """
        return True
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Migraciones solo en primary
        """
        return db == 'default'
```

## Opción 2: AWS RDS (Producción) - RECOMENDADO

### Terraform (Infrastructure as Code)
```hcl
# terraform/rds.tf

resource "aws_db_instance" "primary" {
  identifier           = "barbershop-primary"
  engine              = "postgres"
  engine_version      = "16.1"
  instance_class      = "db.t3.medium"
  allocated_storage   = 100
  storage_encrypted   = true
  
  db_name  = var.db_name
  username = var.db_user
  password = var.db_password
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"
  
  multi_az               = false  # Replica manual es más barata
  publicly_accessible    = false
  
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  
  tags = {
    Environment = "production"
    Role        = "primary"
  }
}

resource "aws_db_instance" "replica" {
  identifier             = "barbershop-replica"
  replicate_source_db    = aws_db_instance.primary.identifier
  instance_class         = "db.t3.medium"
  
  publicly_accessible    = false
  
  tags = {
    Environment = "production"
    Role        = "replica"
  }
}
```

### Costo AWS RDS
- Primary (db.t3.medium): ~$60/mes
- Replica (db.t3.medium): ~$60/mes
- Storage (100GB): ~$12/mes
- **Total: ~$132/mes**

## Testing

### 1. Verificar replicación
```bash
# En primary
docker exec -it api_peluqueria-db-primary-1 psql -U postgres -c "SELECT * FROM pg_stat_replication;"

# Debe mostrar 1 conexión activa
```

### 2. Test failover manual
```python
# management/commands/test_db_failover.py
from django.core.management.base import BaseCommand
from django.db import connections

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Test write en primary
        with connections['default'].cursor() as cursor:
            cursor.execute("SELECT 1")
            self.stdout.write("✅ Primary OK")
        
        # Test read en replica
        with connections['replica'].cursor() as cursor:
            cursor.execute("SELECT 1")
            self.stdout.write("✅ Replica OK")
```

## Rollback Plan
Si algo falla, revertir a single DB:
```yaml
# docker-compose.yml (rollback)
services:
  db:
    image: postgres:16
    # ... configuración original
```

## Próximos pasos
- Día 3-4: Redis Sentinel
- Día 5-6: Backups multi-región
