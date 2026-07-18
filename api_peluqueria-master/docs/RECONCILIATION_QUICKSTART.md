# Guía Rápida de Implementación - Reconciliación Financiera

## Checklist de Implementación (30 minutos)

### 1. Aplicar Migraciones (5 min)

```bash
cd /path/to/api_peluqueria
python manage.py makemigrations billing_api
python manage.py migrate billing_api
```

**Verifica:**
```bash
python manage.py shell
>>> from apps.billing_api.reconciliation_models import ProcessedStripeEvent
>>> ProcessedStripeEvent.objects.count()  # Debe retornar 0
```

---

### 2. Actualizar URLs (2 min)

**Archivo:** `backend/urls.py`

```python
from apps.billing_api.webhooks_idempotent import stripe_webhook

urlpatterns = [
    # ... rutas existentes ...
    path('api/billing/webhook/stripe/', stripe_webhook, name='stripe-webhook'),
]
```

**Comentar o eliminar webhook antiguo si existe.**

---

### 3. Configurar Variables de Entorno (3 min)

**Archivo:** `.env`

```bash
# Stripe (ya existentes)
STRIPE_SECRET_KEY=sk_live_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx

# NUEVO: Webhook secret
STRIPE_WEBHOOK_SECRET=whsec_xxxxx

# NUEVO: Emails para alertas financieras
FINANCE_ALERT_EMAILS=finance@company.com,cfo@company.com
```

**Obtener STRIPE_WEBHOOK_SECRET:**
1. Ir a Stripe Dashboard → Developers → Webhooks
2. Seleccionar webhook existente o crear nuevo
3. Copiar "Signing secret"

---

### 4. Actualizar Webhook en Stripe (5 min)

**Stripe Dashboard → Developers → Webhooks:**

1. **Endpoint URL:** `https://yourdomain.com/api/billing/webhook/stripe/`
2. **Eventos a escuchar:**
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
   - `customer.subscription.deleted`
   - `invoice.created`
3. **Guardar** y copiar "Signing secret" a `.env`

---

### 5. Reiniciar Servicios (2 min)

```bash
# Docker
docker-compose restart web celery celery-beat

# O sin Docker
sudo systemctl restart gunicorn
sudo systemctl restart celery
sudo systemctl restart celery-beat
```

---

### 6. Verificar Celery Beat (3 min)

```bash
# Ver schedule
docker exec -it api_peluqueria-celery-beat-1 celery -A backend inspect scheduled

# Debe aparecer:
# - daily-financial-reconciliation (4:00 AM)
```

**Si no aparece:**
```bash
# Reiniciar celery-beat
docker-compose restart celery-beat
```

---

### 7. Test Manual de Webhook (5 min)

**Opción A: Stripe CLI**
```bash
stripe listen --forward-to localhost:8000/api/billing/webhook/stripe/
stripe trigger invoice.payment_succeeded
```

**Opción B: cURL**
```bash
curl -X POST http://localhost:8000/api/billing/webhook/stripe/ \
  -H "Content-Type: application/json" \
  -H "Stripe-Signature: test" \
  -d '{"id": "evt_test_123", "type": "invoice.payment_succeeded", "data": {...}}'
```

**Verificar en Admin:**
- `/admin/billing_api/processedevent/` → Debe aparecer evento

---

### 8. Ejecutar Reconciliación Manual (5 min)

```bash
# Desde Django shell
python manage.py shell

>>> from apps.billing_api.tasks import daily_financial_reconciliation
>>> result = daily_financial_reconciliation.apply()
>>> print(result.result)
```

**Verificar en Admin:**
- `/admin/billing_api/reconciliationlog/` → Debe aparecer log con status "completed"

---

## Verificación Post-Implementación

### ✅ Checklist de Validación

- [ ] Migraciones aplicadas sin errores
- [ ] ProcessedStripeEvent table existe
- [ ] ReconciliationLog table existe
- [ ] ReconciliationAlert table existe
- [ ] Webhook URL actualizada en Stripe
- [ ] STRIPE_WEBHOOK_SECRET configurado
- [ ] Celery Beat ejecutando
- [ ] Task `daily-financial-reconciliation` en schedule
- [ ] Webhook test exitoso
- [ ] Evento registrado en ProcessedStripeEvent
- [ ] Reconciliación manual ejecutada
- [ ] Log creado en ReconciliationLog

---

## Monitoreo Primeras 24 Horas

### Logs a Revisar

```bash
# Webhooks
docker logs -f api_peluqueria-web-1 | grep "stripe_webhook"

# Reconciliación
docker logs -f api_peluqueria-celery-1 | grep "Reconciliation"

# Errores
docker logs -f api_peluqueria-web-1 | grep "ERROR"
```

### Métricas Esperadas

| Métrica | Esperado | Acción si Falla |
|---------|----------|-----------------|
| Webhooks recibidos | >0 | Verificar URL en Stripe |
| Eventos procesados | 100% | Revisar logs de error |
| Reconciliación ejecutada | 1x/día | Verificar Celery Beat |
| Discrepancias encontradas | <5% | Investigar alertas |

---

## Rollback (Si es Necesario)

### Paso 1: Revertir Webhook

**Stripe Dashboard:**
- Cambiar URL a webhook antiguo
- O deshabilitar webhook temporalmente

### Paso 2: Revertir Migración

```bash
python manage.py migrate billing_api 0001_initial
```

### Paso 3: Revertir Código

```bash
git revert <commit_hash>
docker-compose restart web celery celery-beat
```

---

## Soporte

**Errores Comunes:**

1. **"Invalid signature"**
   - Verificar STRIPE_WEBHOOK_SECRET en .env
   - Verificar que webhook apunta a URL correcta

2. **"ProcessedStripeEvent matching query does not exist"**
   - Ejecutar migraciones: `python manage.py migrate billing_api`

3. **"Task not registered"**
   - Reiniciar Celery: `docker-compose restart celery celery-beat`

4. **"Reconciliation failed: Stripe API error"**
   - Verificar STRIPE_SECRET_KEY
   - Verificar rate limits de Stripe

---

## Próximos Pasos

### Semana 1
- [ ] Monitorear logs diariamente
- [ ] Revisar alertas en Admin
- [ ] Resolver discrepancias encontradas

### Semana 2
- [ ] Analizar métricas de reconciliación
- [ ] Ajustar horario de ejecución si necesario
- [ ] Configurar notificaciones email (opcional)

### Mes 1
- [ ] Evaluar tasa de discrepancias
- [ ] Optimizar queries si reconciliación >60s
- [ ] Documentar casos edge encontrados

---

## Contacto

- **Documentación Completa:** `docs/FINANCIAL_RECONCILIATION.md`
- **Soporte Técnico:** devops@yourdomain.com
- **Alertas Financieras:** finance@yourdomain.com
