# Redis Sentinel High Availability

## Objetivo
Configurar Redis con Sentinel (1 master + 2 replicas + 3 sentinels)

## Arquitectura
```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Master     │─────▶│  Replica 1  │      │  Replica 2  │
│  (Write)    │      │  (Read)     │◀─────│  (Read)     │
└─────────────┘      └─────────────┘      └─────────────┘
      ▲                     ▲                     ▲
      │                     │                     │
┌─────┴─────────────────────┴─────────────────────┴─────┐
│              Sentinel (3 nodos)                        │
│         Monitorea y hace failover automático           │
└────────────────────────────────────────────────────────┘
```

## docker-compose.yml

```yaml
services:
  redis-master:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --masterauth ${REDIS_PASSWORD}
    volumes:
      - redis_master_data:/data
    networks:
      - backend

  redis-replica-1:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --masterauth ${REDIS_PASSWORD} --replicaof redis-master 6379
    depends_on:
      - redis-master
    volumes:
      - redis_replica1_data:/data
    networks:
      - backend

  redis-replica-2:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --masterauth ${REDIS_PASSWORD} --replicaof redis-master 6379
    depends_on:
      - redis-master
    volumes:
      - redis_replica2_data:/data
    networks:
      - backend

  redis-sentinel-1:
    image: redis:7-alpine
    command: >
      sh -c "echo 'port 26379
      sentinel monitor mymaster redis-master 6379 2
      sentinel auth-pass mymaster ${REDIS_PASSWORD}
      sentinel down-after-milliseconds mymaster 5000
      sentinel parallel-syncs mymaster 1
      sentinel failover-timeout mymaster 10000' > /tmp/sentinel.conf &&
      redis-sentinel /tmp/sentinel.conf"
    depends_on:
      - redis-master
    networks:
      - backend

  redis-sentinel-2:
    image: redis:7-alpine
    command: >
      sh -c "echo 'port 26379
      sentinel monitor mymaster redis-master 6379 2
      sentinel auth-pass mymaster ${REDIS_PASSWORD}
      sentinel down-after-milliseconds mymaster 5000
      sentinel parallel-syncs mymaster 1
      sentinel failover-timeout mymaster 10000' > /tmp/sentinel.conf &&
      redis-sentinel /tmp/sentinel.conf"
    depends_on:
      - redis-master
    networks:
      - backend

  redis-sentinel-3:
    image: redis:7-alpine
    command: >
      sh -c "echo 'port 26379
      sentinel monitor mymaster redis-master 6379 2
      sentinel auth-pass mymaster ${REDIS_PASSWORD}
      sentinel down-after-milliseconds mymaster 5000
      sentinel parallel-syncs mymaster 1
      sentinel failover-timeout mymaster 10000' > /tmp/sentinel.conf &&
      redis-sentinel /tmp/sentinel.conf"
    depends_on:
      - redis-master
    networks:
      - backend

volumes:
  redis_master_data:
  redis_replica1_data:
  redis_replica2_data:
```

## settings.py

```python
# backend/settings.py

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': [
            f'redis://:{env("REDIS_PASSWORD")}@redis-sentinel-1:26379/0',
            f'redis://:{env("REDIS_PASSWORD")}@redis-sentinel-2:26379/0',
            f'redis://:{env("REDIS_PASSWORD")}@redis-sentinel-3:26379/0',
        ],
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.SentinelClient',
            'PASSWORD': env('REDIS_PASSWORD'),
            'SENTINEL_KWARGS': {
                'password': env('REDIS_PASSWORD'),
            },
            'CONNECTION_POOL_KWARGS': {
                'service_name': 'mymaster',
                'socket_connect_timeout': 5,
                'socket_timeout': 5,
            },
        }
    }
}

# Celery con Sentinel
CELERY_BROKER_URL = f'sentinel://:{env("REDIS_PASSWORD")}@redis-sentinel-1:26379;sentinel://:{env("REDIS_PASSWORD")}@redis-sentinel-2:26379;sentinel://:{env("REDIS_PASSWORD")}@redis-sentinel-3:26379'
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'master_name': 'mymaster',
    'sentinel_kwargs': {
        'password': env('REDIS_PASSWORD'),
    },
}
```

## requirements.txt

```txt
redis==5.0.1
django-redis==5.4.0
```

## Testing

### 1. Verificar replicación
```bash
# Conectar a master
docker exec -it api_peluqueria-redis-master-1 redis-cli -a ${REDIS_PASSWORD}

# Ver info replicación
INFO replication

# Debe mostrar 2 replicas conectadas
```

### 2. Test failover automático
```bash
# Matar master
docker stop api_peluqueria-redis-master-1

# Esperar 5-10 segundos
# Sentinel promoverá una replica a master

# Verificar nuevo master
docker exec -it api_peluqueria-redis-sentinel-1-1 redis-cli -p 26379
SENTINEL get-master-addr-by-name mymaster

# Debe mostrar nueva IP
```

### 3. Test desde Django
```python
# management/commands/test_redis_ha.py
from django.core.management.base import BaseCommand
from django.core.cache import cache

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Test write
        cache.set('test_key', 'test_value', 60)
        self.stdout.write("✅ Write OK")
        
        # Test read
        value = cache.get('test_key')
        assert value == 'test_value'
        self.stdout.write("✅ Read OK")
        
        # Test failover (manual)
        self.stdout.write("Mata el master y vuelve a ejecutar este comando")
```

## Costo
- Docker Compose: $0 (solo recursos locales)
- AWS ElastiCache (producción): ~$150/mes (3 nodos cache.t3.small)

## Rollback Plan
```yaml
# docker-compose.yml (rollback)
services:
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    # ... configuración original
```

## Próximos pasos
- Día 5-6: Backups multi-región
