# Celery - Automatización de Tareas

## Configuración Completada ✅

Se ha implementado Celery para automatización de citas y notificaciones.

## Tareas Automáticas Configuradas

### 1. **Marcar citas vencidas** (Cada 15 minutos)
- Marca citas como `no_show` si pasó la hora y siguen en `scheduled`
- Notifica al estilista

### 2. **Recordatorios diarios** (Diario a las 8 AM)
- Envía recordatorios de citas programadas para hoy
- Notifica a estilistas

### 3. **Notificar citas próximas** (Cada hora)
- Notifica citas que empiezan en 1 hora
- Alerta al estilista

### 4. **Limpieza de notificaciones** (Domingos a las 3 AM)
- Elimina notificaciones leídas mayores a 30 días

## Signals Implementados

### Cambios de Estado
- `scheduled` → `completed`: "Cita completada"
- `scheduled` → `cancelled`: "Cita cancelada"
- `scheduled` → `no_show`: "Cliente no asistió"

### Reprogramación
- Detecta cambios en `date_time` y notifica

## Ejecución con Docker (RECOMENDADO)

### Iniciar todos los servicios
```bash
docker-compose up -d
```

Esto inicia automáticamente:
- ✅ PostgreSQL
- ✅ Redis
- ✅ Django (web)
- ✅ Celery Worker
- ✅ Celery Beat (scheduler)
- ✅ Nginx

### Ver logs de Celery
```bash
# Worker
docker-compose logs -f celery

# Beat (scheduler)
docker-compose logs -f celery-beat
```

### Reiniciar solo Celery
```bash
docker-compose restart celery celery-beat
```

## Ejecución Manual (Desarrollo)

Si prefieres ejecutar sin Docker:

### 1. Iniciar Redis
```bash
docker run -d -p 6379:6379 redis
```

### 2. Iniciar Celery Worker
```bash
celery -A backend worker -l info --pool=solo
```

### 3. Iniciar Celery Beat
```bash
celery -A backend beat -l info
```

### 4. Iniciar Django
```bash
python manage.py runserver
```

## Verificación

### Ver tareas registradas
```bash
celery -A api_peluqueria inspect registered
```

### Ver tareas programadas
```bash
celery -A api_peluqueria inspect scheduled
```

### Ejecutar tarea manualmente (testing)
```python
from apps.notifications_api.tasks import mark_expired_appointments
result = mark_expired_appointments.delay()
print(result.get())
```

## Configuración de Producción

En `.env` agregar:
```env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
REDIS_URL=redis://localhost:6379/0
```

## Monitoreo con Flower (Opcional)

```bash
pip install flower
celery -A api_peluqueria flower
```

Acceder a: http://localhost:5555

## Troubleshooting

### Error: "No module named 'celery'"
```bash
pip install celery redis
```

### Error: "Connection refused" (Redis)
Verificar que Redis esté corriendo:
```bash
redis-cli ping
# Debe responder: PONG
```

### Tareas no se ejecutan
1. Verificar que Celery Worker esté corriendo
2. Verificar que Celery Beat esté corriendo
3. Revisar logs en la consola

## Logs

Los logs de Celery se muestran en la consola donde ejecutaste el worker/beat.

Para producción, configurar logging en `settings.py`.
