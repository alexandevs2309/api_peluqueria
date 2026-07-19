# CHECKLIST OPERATIVO: IMPLEMENTACIÓN DE OBSERVABILIDAD

## PRE-REQUISITOS

### 1. Instalar Dependencias

```bash
pip install python-json-logger
pip install sentry-sdk
```

Actualizar `requirements.txt`:
```bash
pip freeze > requirements.txt
```

### 2. Configurar Variables de Entorno

Agregar a `.env`:
```bash
# Sentry
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
SENTRY_ENVIRONMENT=production
SENTRY_RELEASE=1.0.0

# Opcional
LOG_QUERIES=false  # true solo para debugging
ENABLE_DEBUG_TOOLBAR=false  # true solo en staging
```

### 3. Crear Directorio de Logs

```bash
mkdir -p logs
chmod 755 logs
```

---

## IMPLEMENTACIÓN (4 horas)

### PASO 1: Actualizar settings.py (30 min)

- [ ] Copiar configuración de `ops/observability_settings.py`
- [ ] Reemplazar sección de Sentry
- [ ] Reemplazar sección de LOGGING
- [ ] Agregar middlewares de observabilidad
- [ ] Agregar task `calculate_daily_mrr` a CELERY_BEAT_SCHEDULE

### PASO 2: Crear Archivos Nuevos (30 min)

- [ ] Crear `apps/utils/__init__.py` (si no existe)
- [ ] Copiar `apps/utils/middleware.py`
- [ ] Copiar `apps/utils/views.py`
- [ ] Copiar `apps/billing_api/metrics.py`

### PASO 3: Actualizar Código Existente (1 hora)

#### 3.1 Actualizar webhooks

- [ ] Abrir `apps/billing_api/webhooks_idempotent.py`
- [ ] Agregar import: `from apps.billing_api.metrics import FinancialMetrics`
- [ ] En `handle_payment_succeeded()` agregar:
  ```python
  FinancialMetrics.record_payment_success(
      amount=invoice_data['amount_paid'] / 100,
      tenant_id=user.tenant.id if hasattr(user, 'tenant') and user.tenant else None,
      user_id=user.id
  )
  ```
- [ ] En `handle_payment_failed()` agregar:
  ```python
  FinancialMetrics.record_payment_failure(
      reason=invoice_data.get('failure_reason', 'Unknown'),
      tenant_id=user.tenant.id if hasattr(user, 'tenant') and user.tenant else None,
      user_id=user.id
  )
  ```

#### 3.2 Agregar task de MRR

- [ ] Abrir `apps/billing_api/tasks.py`
- [ ] Agregar import: `from apps.billing_api.metrics import FinancialMetrics`
- [ ] Copiar función `calculate_daily_mrr()` de `ops/mrr_task.py`

#### 3.3 Agregar endpoints de métricas

- [ ] Abrir `backend/urls.py`
- [ ] Agregar:
  ```python
  from apps.utils.views import metrics_dashboard, health_check
  
  urlpatterns = [
      # ... existentes ...
      path('api/metrics/dashboard/', metrics_dashboard, name='metrics-dashboard'),
      path('api/health/', health_check, name='health-check'),
  ]
  ```

### PASO 4: Configurar Sentry UI (30 min)

#### 4.1 Crear Alertas

Ir a: https://sentry.io → Alerts → Create Alert Rule

**Alerta 1: Error Rate Alto**
- Name: `High Error Rate`
- Condition: `Error rate > 1%`
- Time window: `5 minutes`
- Action: `Email to team@company.com`

**Alerta 2: Webhooks Fallidos**
- Name: `Webhook Failures`
- Condition: `Event count > 3`
- Filter: `message contains "webhook"`
- Time window: `10 minutes`
- Action: `Email + Slack`

**Alerta 3: Celery Retries**
- Name: `Celery Task Retries`
- Condition: `Event count > 5`
- Filter: `message contains "retry"`
- Time window: `15 minutes`
- Action: `Email`

**Alerta 4: Payment Spike**
- Name: `Payment Failure Spike`
- Condition: `Event count > 5`
- Filter: `message contains "Payment failure spike"`
- Time window: `10 minutes`
- Action: `Email + PagerDuty`

**Alerta 5: MRR Drop**
- Name: `MRR Drop Detected`
- Condition: `Event count > 1`
- Filter: `message contains "MRR drop"`
- Time window: `1 hour`
- Action: `Email to finance@company.com`

### PASO 5: Deploy (30 min)

```bash
# 1. Commit cambios
git add .
git commit -m "feat: implement professional observability"

# 2. Reiniciar servicios
docker-compose restart web celery celery-beat

# 3. Verificar logs
docker-compose logs -f web | grep "api.requests"
```

---

## VALIDACIÓN POST-DEPLOY (1 hora)

### Test 1: Logging Estructurado

```bash
# Hacer request a API
curl http://localhost/api/tenants/

# Verificar log JSON
tail -1 logs/app.log | jq
```

**Esperado:**
```json
{
  "request_id": "uuid",
  "method": "GET",
  "path": "/api/tenants/",
  "status_code": 200,
  "duration_ms": 45.2,
  "user_id": 1,
  "tenant_id": 1
}
```

### Test 2: Métricas Financieras

```bash
# Simular pago exitoso (webhook test en Stripe)
# O ejecutar manualmente:
docker exec api_peluqueria-api-1 python manage.py shell
```

```python
from apps.billing_api.metrics import FinancialMetrics
FinancialMetrics.record_payment_success(amount=100, tenant_id=1)
```

**Verificar:**
```bash
tail logs/metrics.log | jq
```

### Test 3: Dashboard de Métricas

```bash
# Obtener token de admin
TOKEN="your-admin-token"

# Consultar dashboard
curl -H "Authorization: Bearer $TOKEN" http://localhost/api/metrics/dashboard/ | jq
```

**Esperado:**
```json
{
  "timestamp": "2024-01-15T10:00:00Z",
  "database": {
    "active_connections": 5
  },
  "financial": {
    "mrr": 1500.0,
    "payments_success_today": 10,
    "payments_failure_today": 1,
    "error_rate": 9.09
  },
  "celery": {
    "active_tasks": 2,
    "workers": 1
  }
}
```

### Test 4: Health Check

```bash
curl http://localhost/api/health/ | jq
```

**Esperado:**
```json
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "cache": "ok",
    "celery": "ok"
  }
}
```

### Test 5: Sentry Integration

```bash
# Forzar error para probar Sentry
docker exec api_peluqueria-api-1 python manage.py shell
```

```python
import sentry_sdk
sentry_sdk.capture_message("Test observability", level='info')
```

**Verificar en Sentry UI:**
- Ir a: https://sentry.io → Issues
- Buscar: "Test observability"
- Verificar tags: `tenant_id`, `user_id`

### Test 6: Slow Query Detection

```bash
# Ejecutar query lenta intencionalmente
docker exec api_peluqueria-api-1 python manage.py shell
```

```python
from django.db import connection
import time
with connection.cursor() as cursor:
    cursor.execute("SELECT pg_sleep(0.3)")
```

**Verificar en Sentry:**
- Buscar: "Slow queries detected"

---

## MONITOREO CONTINUO

### Diario

- [ ] Revisar Sentry dashboard
- [ ] Verificar alertas recibidas
- [ ] Revisar logs de errores: `tail -100 logs/app.log | grep ERROR`

### Semanal

- [ ] Revisar métricas financieras
- [ ] Verificar MRR trend
- [ ] Revisar slow queries acumuladas

### Mensual

- [ ] Validar alertas configuradas
- [ ] Revisar y ajustar thresholds
- [ ] Actualizar documentación

---

## TROUBLESHOOTING

### Problema: Logs no aparecen en JSON

**Solución:**
```bash
# Verificar que python-json-logger está instalado
pip list | grep json

# Verificar configuración
docker exec api_peluqueria-api-1 python manage.py shell
>>> from django.conf import settings
>>> settings.LOGGING['formatters']['json']
```

### Problema: Sentry no captura eventos

**Solución:**
```bash
# Verificar SENTRY_DSN
docker exec api_peluqueria-api-1 python manage.py shell
>>> from django.conf import settings
>>> settings.SENTRY_DSN

# Test manual
>>> import sentry_sdk
>>> sentry_sdk.capture_message("Test", level='info')
```

### Problema: Métricas no se guardan

**Solución:**
```bash
# Verificar Redis
docker exec api_peluqueria-redis-1 redis-cli PING

# Verificar cache
docker exec api_peluqueria-api-1 python manage.py shell
>>> from django.core.cache import cache
>>> cache.set('test', 'ok')
>>> cache.get('test')
```

### Problema: Dashboard retorna 403

**Solución:**
- Verificar que el usuario es admin
- Verificar token JWT válido
- Verificar permisos: `IsAdminUser`

---

## ROLLBACK (Si algo falla)

```bash
# 1. Revertir cambios
git revert HEAD

# 2. Reiniciar servicios
docker-compose restart web celery

# 3. Verificar sistema funcional
curl http://localhost/api/health/
```

---

## SCORE FINAL ESPERADO

| Fase | Score |
|------|-------|
| Error Monitoring | 13/14 (93%) |
| Performance Monitoring | 8/10 (80%) |
| Métricas Financieras | 8/8 (100%) |
| Logging Estructurado | 8/8 (100%) |

**TOTAL: 37/40 (92.5%)** ✅

---

## PRÓXIMOS PASOS (OPCIONAL)

1. Configurar Grafana dashboards
2. Implementar distributed tracing (OpenTelemetry)
3. Agregar anomaly detection con ML
4. Configurar SLO/SLI tracking
