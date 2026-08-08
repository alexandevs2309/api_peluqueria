# DISASTER RECOVERY PLAN

## Objetivos

**RPO (Recovery Point Objective)**: 24 horas  
**RTO (Recovery Time Objective)**: 15 minutos  
**Retención**: 30 días

---

## BACKUP AUTOMÁTICO

### Frecuencia

- **Diario**: 2:00 AM (automático vía cron)
- **Ubicación**: `/backups/` en servidor
- **Formato**: `backup_YYYYMMDD_HHMMSS.sql.gz`

### Configuración Cron

```bash
# Ejecutar setup-cron.sh para configurar
./scripts/setup-cron.sh

# Cron job creado:
0 2 * * * /path/to/scripts/backup-production.sh
```

### Verificación Manual

```bash
# Listar backups
ls -lh /backups/

# Verificar último backup
ls -lt /backups/ | head -n 2
```

---

## PROCEDIMIENTO DE RESTORE

### 1. Restore Completo (Disaster Recovery)

```bash
# 1. Detener servicios
docker compose down

# 2. Restaurar base de datos
./scripts/restore.sh /backups/backup_20240226_020000.sql.gz

# 3. Levantar servicios
docker compose up -d

# 4. Verificar
docker compose exec web python manage.py check
curl http://localhost/api/healthz/
```

**Tiempo estimado**: 10-15 minutos

### 2. Restore Parcial (Tabla específica)

```bash
# Restaurar solo una tabla
pg_restore -U postgres -d barbershop_db -t pos_api_sale backup.sql.gz
```

### 3. Point-in-Time Recovery (PITR)

```bash
# Restaurar hasta timestamp específico
./ops/restore/pg_restore_pitr.sh "2024-02-26 14:30:00"
```

---

## VALIDACIÓN POST-RESTORE

### Checklist Obligatorio

```bash
# 1. Verificar Django
docker compose exec web python manage.py check --deploy

# 2. Verificar datos críticos
docker compose exec web python manage.py shell
>>> from apps.pos_api.models import Sale
>>> Sale.objects.count()  # Debe coincidir con pre-disaster

# 3. Verificar integridad financiera
docker compose exec web python manage.py shell
>>> from apps.billing_api.tasks import daily_financial_reconciliation
>>> daily_financial_reconciliation.delay()

# 4. Health check
curl http://localhost/api/healthz/
```

---

## TEST MENSUAL DE RESTORE

### Procedimiento

```bash
# 1. Crear backup de prueba
./scripts/backup-production.sh

# 2. Crear entorno de test
docker compose -f docker-compose.test.yml up -d

# 3. Restaurar en test
./scripts/restore.sh /backups/latest.sql.gz --target=test

# 4. Validar
docker compose -f docker-compose.test.yml exec web python manage.py check

# 5. Documentar resultado
echo "$(date): Test restore OK" >> /var/log/dr-tests.log
```

**Ejecutar**: Primer lunes de cada mes

---

## ESCENARIOS DE DISASTER

### Escenario 1: Pérdida de Base de Datos

**Impacto**: CRÍTICO  
**RTO**: 15 minutos  
**RPO**: 24 horas

**Pasos**:
1. Identificar último backup válido
2. Ejecutar restore completo
3. Validar integridad
4. Notificar a usuarios

### Escenario 2: Corrupción de Datos

**Impacto**: ALTO  
**RTO**: 30 minutos  
**RPO**: 24 horas

**Pasos**:
1. Identificar alcance de corrupción
2. Restore parcial de tablas afectadas
3. Reconciliación financiera
4. Validar con usuarios

### Escenario 3: Pérdida de Servidor Completo

**Impacto**: CRÍTICO  
**RTO**: 2 horas  
**RPO**: 24 horas

**Pasos**:
1. Provisionar nuevo servidor
2. Instalar Docker + dependencias
3. Clonar repositorio
4. Restore completo
5. Configurar DNS
6. Validar

---

## CONTACTOS DE EMERGENCIA

**DevOps Lead**: [email]  
**DBA**: [email]  
**CTO**: [email]

---

## LOGS Y AUDITORÍA

Todos los restores se registran en:
- `/var/log/restore.log`
- Sentry (eventos críticos)
- Slack #ops-alerts

---

## ÚLTIMA ACTUALIZACIÓN

**Fecha**: 2024-02-26  
**Próximo Test**: 2024-03-04  
**Último Test Exitoso**: Pendiente
