# DR Monthly Test Checklist

**Fecha de ejecución:** ___________  
**Ejecutado por:** ___________  
**Duración total:** ___________

---

## PRE-TEST

- [ ] Ventana de mantenimiento programada (si aplica)
- [ ] Equipo notificado (DevOps + Backend)
- [ ] Ambiente staging disponible
- [ ] Acceso a AWS verificado
- [ ] Scripts actualizados en `/opt/scripts/`

---

## TEST 1: RESTORE COMPLETO DE BASE DE DATOS

**Objetivo:** Validar capacidad de restore desde backup daily  
**Tiempo esperado:** <4 horas  
**Ambiente:** Staging

### Ejecución

- [ ] Identificar último backup disponible
  ```bash
  aws s3 ls s3://saas-backups-prod/daily/ | tail -5
  ```
  **Backup seleccionado:** ___________

- [ ] Descargar backup a servidor staging
  ```bash
  time aws s3 sync s3://saas-backups-prod/daily/[TIMESTAMP] /tmp/restore/
  ```
  **Tiempo descarga:** ___________ min

- [ ] Ejecutar restore
  ```bash
  time /opt/scripts/pg_restore_staging.sh
  ```
  **Tiempo restore:** ___________ min

- [ ] Validar integridad de datos
  ```bash
  psql staging -c "SELECT COUNT(*) FROM tenants;"
  psql staging -c "SELECT COUNT(*) FROM users;"
  psql staging -c "SELECT COUNT(*) FROM subscriptions WHERE status='active';"
  psql staging -c "SELECT MAX(created_at) FROM payments;"
  ```
  **Resultados:**
  - Tenants: ___________
  - Users: ___________
  - Active subscriptions: ___________
  - Último pago: ___________

- [ ] Verificar consistencia referencial
  ```bash
  psql staging -f /opt/scripts/validate_referential_integrity.sql
  ```
  **Errores encontrados:** ___________

- [ ] Conectar aplicación a staging DB
  ```bash
  kubectl set env deployment/django-api-staging DATABASE_HOST=staging-db
  ```
  **Health check OK:** [ ] Sí [ ] No

### Resultados

**Tiempo total:** ___________ min  
**RTO cumplido (<240 min):** [ ] Sí [ ] No  
**Integridad validada:** [ ] Sí [ ] No  
**Problemas encontrados:** ___________

---

## TEST 2: POINT-IN-TIME RECOVERY (PITR)

**Objetivo:** Validar recuperación a punto específico en el tiempo  
**Tiempo esperado:** <4 horas  
**Ambiente:** Staging

### Ejecución

- [ ] Seleccionar punto de recuperación (15 min atrás)
  **Target time:** ___________

- [ ] Configurar recovery target
  ```bash
  echo "recovery_target_time = '[TIMESTAMP]'" >> /var/lib/postgresql/14/staging/postgresql.auto.conf
  ```

- [ ] Ejecutar PITR
  ```bash
  time /opt/scripts/pg_pitr_staging.sh
  ```
  **Tiempo PITR:** ___________ min

- [ ] Validar punto de recuperación
  ```bash
  psql staging -c "SELECT MAX(created_at) FROM payments;"
  ```
  **Último registro:** ___________  
  **Coincide con target:** [ ] Sí [ ] No

### Resultados

**PITR exitoso:** [ ] Sí [ ] No  
**RPO cumplido (<15 min):** [ ] Sí [ ] No  
**Problemas encontrados:** ___________

---

## TEST 3: RESTORE DE TABLA INDIVIDUAL

**Objetivo:** Validar recuperación granular  
**Tiempo esperado:** <30 min  
**Ambiente:** Staging

### Ejecución

- [ ] Seleccionar tabla de prueba (no crítica)
  **Tabla:** ___________

- [ ] Contar registros originales
  ```bash
  psql staging -c "SELECT COUNT(*) FROM [TABLA];"
  ```
  **Count original:** ___________

- [ ] Simular pérdida de datos
  ```bash
  psql staging -c "DELETE FROM [TABLA] WHERE created_at > NOW() - INTERVAL '1 hour';"
  ```
  **Registros eliminados:** ___________

- [ ] Restaurar tabla desde backup
  ```bash
  time /opt/scripts/restore_single_table.sh [TABLA]
  ```
  **Tiempo restore:** ___________ min

- [ ] Validar recuperación
  ```bash
  psql staging -c "SELECT COUNT(*) FROM [TABLA];"
  ```
  **Count post-restore:** ___________  
  **Coincide con original:** [ ] Sí [ ] No

### Resultados

**Restore exitoso:** [ ] Sí [ ] No  
**Tiempo <30 min:** [ ] Sí [ ] No  
**Problemas encontrados:** ___________

---

## TEST 4: VALIDACIÓN DE WAL ARCHIVES

**Objetivo:** Verificar continuidad de WAL para PITR  
**Tiempo esperado:** <10 min

### Ejecución

- [ ] Listar últimos WAL archives
  ```bash
  aws s3 ls s3://saas-backups-prod/wal/ | tail -20
  ```

- [ ] Verificar continuidad (sin gaps)
  ```bash
  /opt/scripts/validate_wal_continuity.sh
  ```
  **Gaps encontrados:** ___________

- [ ] Verificar antigüedad del último WAL
  ```bash
  LAST_WAL=$(aws s3 ls s3://saas-backups-prod/wal/ | tail -1 | awk '{print $1" "$2}')
  echo "Último WAL: ${LAST_WAL}"
  ```
  **Último WAL:** ___________  
  **Antigüedad <10 min:** [ ] Sí [ ] No

- [ ] Verificar tamaño promedio WAL
  ```bash
  aws s3 ls s3://saas-backups-prod/wal/ | tail -100 | awk '{sum+=$3; count++} END {print sum/count}'
  ```
  **Tamaño promedio:** ___________ bytes

### Resultados

**WAL continuos:** [ ] Sí [ ] No  
**Archiving funcionando:** [ ] Sí [ ] No  
**Problemas encontrados:** ___________

---

## TEST 5: VALIDACIÓN DE BACKUPS AUTOMÁTICOS

**Objetivo:** Verificar ejecución correcta de backups programados  
**Tiempo esperado:** <10 min

### Ejecución

- [ ] Verificar backup de hoy existe
  ```bash
  TODAY=$(date +%Y%m%d)
  aws s3 ls s3://saas-backups-prod/daily/ | grep ${TODAY}
  ```
  **Backup encontrado:** [ ] Sí [ ] No

- [ ] Verificar tamaño del backup
  ```bash
  aws s3 ls s3://saas-backups-prod/daily/[TIMESTAMP]/ --recursive --summarize
  ```
  **Tamaño total:** ___________ GB

- [ ] Revisar logs de backup
  ```bash
  tail -50 /var/log/pg_backup.log
  ```
  **Errores en log:** [ ] Sí [ ] No

- [ ] Verificar retención (30 daily, 13 weekly, 12 monthly)
  ```bash
  aws s3 ls s3://saas-backups-prod/daily/ | wc -l
  aws s3 ls s3://saas-backups-prod/weekly/ | wc -l
  aws s3 ls s3://saas-backups-prod/monthly/ | wc -l
  ```
  **Daily backups:** ___________  
  **Weekly backups:** ___________  
  **Monthly backups:** ___________

### Resultados

**Backups automáticos OK:** [ ] Sí [ ] No  
**Retención correcta:** [ ] Sí [ ] No  
**Problemas encontrados:** ___________

---

## TEST 6: FAILOVER SIMULADO (OPCIONAL - REQUIERE VENTANA)

**Objetivo:** Validar promoción automática de standby  
**Tiempo esperado:** <30 min  
**⚠️ REQUIERE VENTANA DE MANTENIMIENTO**

### Ejecución

- [ ] Verificar replication lag antes de test
  ```bash
  psql -h primary-db -c "SELECT client_addr, state, sync_state, replay_lag FROM pg_stat_replication;"
  ```
  **Lag actual:** ___________ segundos

- [ ] Detener primary DB
  ```bash
  ssh postgres@primary-db "sudo systemctl stop postgresql"
  ```
  **Hora de detención:** ___________

- [ ] Monitorear promoción automática de standby
  ```bash
  watch -n 1 'pg_isready -h standby-db'
  ```
  **Standby promovido:** [ ] Sí [ ] No  
  **Tiempo hasta promoción:** ___________ segundos

- [ ] Verificar aplicación conecta a nuevo primary
  ```bash
  kubectl logs deployment/django-api | grep "database connection"
  ```
  **Reconexión exitosa:** [ ] Sí [ ] No

- [ ] Validar escrituras en nuevo primary
  ```bash
  psql -h standby-db -c "INSERT INTO health_check (timestamp) VALUES (NOW());"
  ```
  **Escritura exitosa:** [ ] Sí [ ] No

- [ ] Revertir: Levantar primary original como nuevo standby
  ```bash
  ssh postgres@primary-db "sudo systemctl start postgresql"
  ```

### Resultados

**Failover exitoso:** [ ] Sí [ ] No  
**RTO cumplido (<30 min):** [ ] Sí [ ] No  
**Downtime total:** ___________ min  
**Problemas encontrados:** ___________

---

## POST-TEST

- [ ] Cleanup de archivos temporales
  ```bash
  rm -rf /tmp/restore/*
  ```

- [ ] Documentar resultados en wiki
- [ ] Actualizar métricas de DR
- [ ] Reportar problemas encontrados (Jira/GitHub)
- [ ] Programar próximo test (primer lunes del mes siguiente)

---

## RESUMEN EJECUTIVO

### Métricas Alcanzadas

| Métrica | Objetivo | Alcanzado | Status |
|---------|----------|-----------|--------|
| RTO (Restore completo) | <4h | ___ min | ☐ Pass ☐ Fail |
| RPO (PITR) | <15min | ___ min | ☐ Pass ☐ Fail |
| Restore tabla individual | <30min | ___ min | ☐ Pass ☐ Fail |
| Failover time | <30min | ___ min | ☐ Pass ☐ Fail |

### Issues Encontrados

1. ___________
2. ___________
3. ___________

### Acciones Correctivas

1. ___________
2. ___________
3. ___________

### Próximos Pasos

- [ ] ___________
- [ ] ___________
- [ ] ___________

---

**Firma del ejecutor:** ___________  
**Fecha:** ___________  
**Aprobado por CTO:** ___________
