# DR Quarterly Audit Checklist

**Trimestre:** Q___ 20___  
**Fecha de auditoría:** ___________  
**Auditor:** ___________  
**Revisado por CTO:** ___________

---

## 1. AUDITORÍA DE BACKUPS

### 1.1 Existencia y Completitud

- [ ] Verificar backups daily (últimos 30 días)
  ```bash
  aws s3 ls s3://saas-backups-prod/daily/ | wc -l
  ```
  **Cantidad esperada:** 30  
  **Cantidad encontrada:** ___________  
  **Status:** ☐ OK ☐ Issue

- [ ] Verificar backups weekly (últimos 90 días)
  ```bash
  aws s3 ls s3://saas-backups-prod/weekly/ | wc -l
  ```
  **Cantidad esperada:** 13  
  **Cantidad encontrada:** ___________  
  **Status:** ☐ OK ☐ Issue

- [ ] Verificar backups monthly (último año)
  ```bash
  aws s3 ls s3://saas-backups-prod/monthly/ | wc -l
  ```
  **Cantidad esperada:** 12  
  **Cantidad encontrada:** ___________  
  **Status:** ☐ OK ☐ Issue

- [ ] Verificar WAL archives (últimos 7 días)
  ```bash
  aws s3 ls s3://saas-backups-prod/wal/ --recursive | wc -l
  ```
  **Cantidad encontrada:** ___________  
  **Status:** ☐ OK ☐ Issue

### 1.2 Integridad de Backups

- [ ] Validar checksums de últimos 5 backups
  ```bash
  for backup in $(aws s3 ls s3://saas-backups-prod/daily/ | tail -5 | awk '{print $2}'); do
    aws s3api head-object --bucket saas-backups-prod --key daily/${backup}/base.tar.gz
  done
  ```
  **Backups con checksum válido:** ___ / 5  
  **Status:** ☐ OK ☐ Issue

- [ ] Verificar tamaño de backups (tendencia)
  ```bash
  aws s3 ls s3://saas-backups-prod/daily/ --recursive --summarize | grep "Total Size"
  ```
  **Tamaño promedio:** ___________ GB  
  **Tendencia:** ☐ Estable ☐ Creciendo ☐ Decreciendo  
  **Status:** ☐ OK ☐ Issue

### 1.3 Seguridad de Backups

- [ ] Verificar encriptación habilitada (AES-256)
  ```bash
  aws s3api get-bucket-encryption --bucket saas-backups-prod
  ```
  **Encriptación:** ☐ Habilitada ☐ Deshabilitada  
  **Status:** ☐ OK ☐ Issue

- [ ] Verificar versioning habilitado
  ```bash
  aws s3api get-bucket-versioning --bucket saas-backups-prod
  ```
  **Versioning:** ☐ Enabled ☐ Suspended  
  **Status:** ☐ OK ☐ Issue

- [ ] Verificar MFA Delete habilitado
  ```bash
  aws s3api get-bucket-versioning --bucket saas-backups-prod | grep MFADelete
  ```
  **MFA Delete:** ☐ Enabled ☐ Disabled  
  **Status:** ☐ OK ☐ Issue

- [ ] Revisar access logs de S3 (accesos sospechosos)
  ```bash
  aws s3 ls s3://saas-logs/s3-access/ | tail -10
  ```
  **Accesos no autorizados:** ___________  
  **Status:** ☐ OK ☐ Issue

### 1.4 Costos de Storage

- [ ] Calcular costo mensual de backups
  ```bash
  aws ce get-cost-and-usage --time-period Start=2024-01-01,End=2024-01-31 \
    --granularity MONTHLY --metrics BlendedCost \
    --filter file://s3-backup-filter.json
  ```
  **Costo mensual:** $___________  
  **Tendencia vs trimestre anterior:** ☐ +___ % ☐ -___ %  
  **Status:** ☐ OK ☐ Revisar

- [ ] Verificar lifecycle policies aplicadas
  ```bash
  aws s3api get-bucket-lifecycle-configuration --bucket saas-backups-prod
  ```
  **Policies activas:** ___________  
  **Status:** ☐ OK ☐ Issue

---

## 2. AUDITORÍA DE PROCEDIMIENTOS

### 2.1 Documentación

- [ ] Revisar disaster_recovery.md actualizado
  **Última actualización:** ___________  
  **Antigüedad <3 meses:** ☐ Sí ☐ No  
  **Status:** ☐ OK ☐ Actualizar

- [ ] Verificar runbooks actualizados
  - [ ] runbook_db_restore.md
  - [ ] runbook_failover.md
  - [ ] runbook_security_incident.md
  - [ ] runbook_data_corruption.md
  
  **Runbooks desactualizados:** ___________  
  **Status:** ☐ OK ☐ Actualizar

- [ ] Validar scripts de automatización funcionando
  ```bash
  ls -lh /opt/scripts/disaster-recovery/
  ```
  **Scripts encontrados:** ___________  
  **Scripts con errores:** ___________  
  **Status:** ☐ OK ☐ Issue

### 2.2 Tests Ejecutados

- [ ] Verificar tests mensuales ejecutados (últimos 3 meses)
  **Mes 1:** ☐ Ejecutado ☐ No ejecutado  
  **Mes 2:** ☐ Ejecutado ☐ No ejecutado  
  **Mes 3:** ☐ Ejecutado ☐ No ejecutado  
  **Status:** ☐ OK ☐ Issue

- [ ] Revisar resultados de tests
  ```bash
  cat /var/log/dr_tests/*.log | grep -i "fail\|error"
  ```
  **Tests fallidos:** ___________  
  **Status:** ☐ OK ☐ Issue

- [ ] Validar tiempos de restore vs RTO
  | Test | RTO Objetivo | Tiempo Real | Status |
  |------|--------------|-------------|--------|
  | Restore completo | 4h | ___ min | ☐ OK ☐ Fail |
  | PITR | 4h | ___ min | ☐ OK ☐ Fail |
  | Tabla individual | 30min | ___ min | ☐ OK ☐ Fail |
  | Failover | 30min | ___ min | ☐ OK ☐ Fail |

### 2.3 Equipo y Accesos

- [ ] Verificar contactos de emergencia actualizados
  **Contactos desactualizados:** ___________  
  **Status:** ☐ OK ☐ Actualizar

- [ ] Validar accesos del equipo on-call
  - [ ] Acceso SSH a servidores DB
  - [ ] Acceso AWS Console (admin)
  - [ ] Acceso S3 backups (read/write)
  - [ ] Acceso PagerDuty
  - [ ] Acceso Datadog/Monitoring
  
  **Accesos faltantes:** ___________  
  **Status:** ☐ OK ☐ Issue

- [ ] Verificar rotación on-call actualizada
  **Última actualización:** ___________  
  **Status:** ☐ OK ☐ Actualizar

---

## 3. AUDITORÍA DE COMPLIANCE

### 3.1 Métricas de Disponibilidad

- [ ] Calcular uptime del trimestre
  ```sql
  SELECT 
    COUNT(*) FILTER (WHERE status='up') * 100.0 / COUNT(*) as uptime_percent
  FROM health_checks
  WHERE timestamp >= NOW() - INTERVAL '3 months';
  ```
  **Uptime:** ___________  %  
  **SLA objetivo:** 99.9%  
  **Status:** ☐ OK ☐ Issue

- [ ] Revisar incidentes del trimestre
  ```sql
  SELECT 
    COUNT(*) as total_incidents,
    AVG(resolution_time_minutes) as avg_resolution,
    MAX(resolution_time_minutes) as max_resolution
  FROM incident_log
  WHERE incident_date >= NOW() - INTERVAL '3 months';
  ```
  **Total incidentes:** ___________  
  **Tiempo promedio resolución:** ___________ min  
  **Tiempo máximo resolución:** ___________ min  
  **Status:** ☐ OK ☐ Issue

- [ ] Validar cumplimiento RTO/RPO
  ```sql
  SELECT 
    SUM(CASE WHEN met_rto = true THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as rto_compliance,
    SUM(CASE WHEN met_rpo = true THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as rpo_compliance
  FROM incident_log
  WHERE incident_date >= NOW() - INTERVAL '3 months';
  ```
  **RTO compliance:** ___________ %  
  **RPO compliance:** ___________ %  
  **Status:** ☐ OK ☐ Issue

### 3.2 Audit Logs

- [ ] Verificar audit logs de acceso a backups
  ```bash
  aws s3api get-bucket-logging --bucket saas-backups-prod
  ```
  **Logging habilitado:** ☐ Sí ☐ No  
  **Status:** ☐ OK ☐ Issue

- [ ] Revisar accesos sospechosos a backups
  ```bash
  aws s3api list-objects --bucket saas-logs --prefix s3-access/ | \
    grep -i "saas-backups-prod" | grep -v "known-user"
  ```
  **Accesos sospechosos:** ___________  
  **Status:** ☐ OK ☐ Investigar

- [ ] Verificar audit log de cambios en DB
  ```sql
  SELECT COUNT(*) FROM financial_audit_log
  WHERE created_at >= NOW() - INTERVAL '3 months';
  ```
  **Registros de auditoría:** ___________  
  **Status:** ☐ OK ☐ Issue

### 3.3 Seguridad

- [ ] Verificar rotación de credenciales
  ```bash
  aws secretsmanager describe-secret --secret-id prod/db/password | grep LastRotatedDate
  aws secretsmanager describe-secret --secret-id prod/stripe/api-key | grep LastRotatedDate
  ```
  **DB password rotado:** ☐ <90 días ☐ >90 días  
  **Stripe key rotado:** ☐ <180 días ☐ >180 días  
  **Status:** ☐ OK ☐ Rotar

- [ ] Revisar vulnerabilidades en dependencias
  ```bash
  safety check --json
  ```
  **Vulnerabilidades críticas:** ___________  
  **Status:** ☐ OK ☐ Patchear

- [ ] Verificar encriptación en tránsito
  ```bash
  psql -h primary-db -c "SHOW ssl;"
  ```
  **SSL habilitado:** ☐ Sí ☐ No  
  **Status:** ☐ OK ☐ Issue

### 3.4 Retención de Datos

- [ ] Verificar compliance con política de retención
  **Backups >1 año:** ___________  
  **Política:** Mover a DEEP_ARCHIVE  
  **Status:** ☐ OK ☐ Migrar

- [ ] Verificar eliminación de datos antiguos
  ```sql
  SELECT COUNT(*) FROM audit_log WHERE created_at < NOW() - INTERVAL '7 years';
  ```
  **Registros >7 años:** ___________  
  **Status:** ☐ OK ☐ Archivar

---

## 4. AUDITORÍA DE INFRAESTRUCTURA

### 4.1 Replicación

- [ ] Verificar estado de replication
  ```bash
  psql -h primary-db -c "SELECT * FROM pg_stat_replication;"
  ```
  **Standbys activos:** ___________  
  **Lag promedio:** ___________ segundos  
  **Status:** ☐ OK ☐ Issue

- [ ] Validar configuración de replication
  ```bash
  psql -h primary-db -c "SHOW wal_level;"
  psql -h primary-db -c "SHOW max_wal_senders;"
  ```
  **wal_level:** ___________  
  **max_wal_senders:** ___________  
  **Status:** ☐ OK ☐ Issue

### 4.2 Monitoreo

- [ ] Verificar alertas configuradas
  ```bash
  curl -H "Authorization: Bearer $DD_API_KEY" \
    https://api.datadoghq.com/api/v1/monitor | jq '.[] | select(.name | contains("backup"))'
  ```
  **Alertas activas:** ___________  
  **Status:** ☐ OK ☐ Issue

- [ ] Revisar falsos positivos (últimos 3 meses)
  **Alertas totales:** ___________  
  **Falsos positivos:** ___________  
  **Ratio:** ___________ %  
  **Status:** ☐ OK ☐ Ajustar

- [ ] Validar dashboard de DR actualizado
  **URL:** ___________  
  **Última actualización:** ___________  
  **Status:** ☐ OK ☐ Actualizar

### 4.3 Capacidad

- [ ] Proyectar crecimiento de backups (próximos 6 meses)
  **Tamaño actual:** ___________ GB  
  **Crecimiento mensual:** ___________ GB  
  **Proyección 6 meses:** ___________ GB  
  **Capacidad suficiente:** ☐ Sí ☐ No

- [ ] Verificar espacio en disco (servidores DB)
  ```bash
  df -h /var/lib/postgresql
  ```
  **Uso actual:** ___________ %  
  **Status:** ☐ OK ☐ Expandir

---

## 5. AUDITORÍA DE INCIDENTES

### 5.1 Revisión de Incidentes

- [ ] Listar incidentes del trimestre
  ```sql
  SELECT 
    incident_id,
    incident_type,
    severity,
    resolution_time_minutes,
    met_rto
  FROM incident_log
  WHERE incident_date >= NOW() - INTERVAL '3 months'
  ORDER BY severity DESC, resolution_time_minutes DESC;
  ```

| ID | Tipo | Severidad | Tiempo | RTO Met |
|----|------|-----------|--------|---------|
| ___ | ___ | ___ | ___ min | ☐ Sí ☐ No |
| ___ | ___ | ___ | ___ min | ☐ Sí ☐ No |
| ___ | ___ | ___ | ___ min | ☐ Sí ☐ No |

### 5.2 Post-Mortems

- [ ] Verificar post-mortems completados
  **Incidentes críticos:** ___________  
  **Post-mortems completados:** ___________  
  **Status:** ☐ OK ☐ Pendientes

- [ ] Revisar acciones correctivas implementadas
  **Acciones totales:** ___________  
  **Acciones completadas:** ___________  
  **Acciones pendientes:** ___________  
  **Status:** ☐ OK ☐ Seguimiento

### 5.3 Lecciones Aprendidas

**Principales hallazgos del trimestre:**

1. ___________
2. ___________
3. ___________

**Mejoras implementadas:**

1. ___________
2. ___________
3. ___________

---

## 6. REPORTE EJECUTIVO

### 6.1 Resumen de Compliance

| Área | Status | Comentarios |
|------|--------|-------------|
| Backups | ☐ OK ☐ Issue | ___________ |
| Procedimientos | ☐ OK ☐ Issue | ___________ |
| Compliance | ☐ OK ☐ Issue | ___________ |
| Infraestructura | ☐ OK ☐ Issue | ___________ |
| Incidentes | ☐ OK ☐ Issue | ___________ |

**Status general:** ☐ Aprobado ☐ Aprobado con observaciones ☐ Requiere acción

### 6.2 Métricas Clave

| Métrica | Q Anterior | Q Actual | Tendencia |
|---------|------------|----------|-----------|
| Uptime (%) | ___ | ___ | ☐ ↑ ☐ → ☐ ↓ |
| RTO Compliance (%) | ___ | ___ | ☐ ↑ ☐ → ☐ ↓ |
| RPO Compliance (%) | ___ | ___ | ☐ ↑ ☐ → ☐ ↓ |
| Incidentes totales | ___ | ___ | ☐ ↑ ☐ → ☐ ↓ |
| MTTR (min) | ___ | ___ | ☐ ↑ ☐ → ☐ ↓ |
| Costo backups ($) | ___ | ___ | ☐ ↑ ☐ → ☐ ↓ |

### 6.3 Issues Críticos

**Issues encontrados (P0):**

1. ___________
2. ___________
3. ___________

**Plan de remediación:**

| Issue | Responsable | Fecha límite | Status |
|-------|-------------|--------------|--------|
| ___ | ___ | ___ | ☐ Abierto ☐ En progreso ☐ Cerrado |
| ___ | ___ | ___ | ☐ Abierto ☐ En progreso ☐ Cerrado |
| ___ | ___ | ___ | ☐ Abierto ☐ En progreso ☐ Cerrado |

### 6.4 Recomendaciones

**Mejoras propuestas:**

1. ___________
2. ___________
3. ___________

**Inversión requerida:**

- Tiempo: ___________ días-persona
- Costo: $___________ USD
- Prioridad: ☐ Alta ☐ Media ☐ Baja

---

## 7. APROBACIÓN

**Auditoría completada por:** ___________  
**Fecha:** ___________  
**Firma:** ___________

**Revisado por CTO:** ___________  
**Fecha:** ___________  
**Firma:** ___________

**Próxima auditoría:** Q___ 20___

---

## ANEXOS

### A. Logs Relevantes

- Backup logs: `/var/log/pg_backup.log`
- Restore test logs: `/var/log/dr_tests/`
- Incident logs: `incident_log` table
- Access logs: `s3://saas-logs/s3-access/`

### B. Documentos Relacionados

- Disaster Recovery Plan: `disaster_recovery.md`
- Monthly Test Checklist: `dr_monthly_test_checklist.md`
- Runbooks: `docs/runbooks/`
- Post-mortems: `docs/post-mortems/`

### C. Contactos

- CTO: ___________
- DevOps Lead: ___________
- Security Lead: ___________
- Compliance Officer: ___________
