# Go-Live Checklist (30-45 min)

Objetivo: cerrar las brechas restantes de producción con evidencia.

## 1) Observabilidad Externa

- [ ] `Sentry` (o equivalente) configurado en backend y frontend.
- [ ] Alertas activas para:
  - [ ] Error rate alto (5xx)
  - [ ] Latencia p95 alta
  - [ ] Worker Celery caído
  - [ ] Redis/DB no disponibles
- [ ] Dashboard con métricas por tenant:
  - [ ] Requests/min
  - [ ] 4xx/5xx
  - [ ] Latencia p50/p95/p99

Evidencia:
- [ ] URL de dashboard y captura.
- [ ] Alerta de prueba disparada y recibida.

---

## 2) Backup + Restore (DR)

- [ ] Backup automático PostgreSQL habilitado (frecuencia definida).
- [ ] Retención definida (ejemplo: 7/14/30 días).
- [ ] Backup de media/archivos (si aplica).
- [ ] Restore de prueba ejecutado en entorno aislado.
- [ ] RTO medido (tiempo de recuperación real).
- [ ] RPO medido (pérdida de datos aceptable real).

Evidencia:
- [ ] Fecha/hora del último backup exitoso.
- [ ] Log de restore con duración.
- [ ] Documento con `RTO` y `RPO` finales.

---

## 3) Validación Final de Entorno Productivo

- [ ] `DEBUG=False` en runtime.
- [ ] `ALLOWED_HOSTS` correcto.
- [ ] TLS/HTTPS activo (`SECURE_SSL_REDIRECT=True`).
- [ ] Cookies seguras (`Secure`, `HttpOnly`, `SameSite`).
- [ ] No secretos hardcodeados.
- [ ] `docker-compose.prod.yml` validado y servicios `healthy`.
- [ ] Healthcheck API responde `200`.
- [ ] Migraciones aplicadas sin errores.
- [ ] Pruebas críticas RBAC/tenant pasan.

Comandos sugeridos:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail 120 web
docker compose -f docker-compose.prod.yml exec web python manage.py shell -c "from django.conf import settings; print('DEBUG=', settings.DEBUG)"
docker compose -f docker-compose.prod.yml exec web python manage.py migrate --plan
docker compose -f docker-compose.prod.yml exec web pytest apps/employees_api/tests.py -k "manager_can_create_schedule_for_team_employee or manager_can_update_schedule_for_team_employee or manager_cannot_delete_schedule_sensitive_action or manager_cannot_create_schedule_other_tenant or manager_can_check_in_and_check_out_attendance or manager_cannot_check_in_attendance_other_tenant" -q
```

Evidencia:
- [ ] Captura de `ps` con `healthy`.
- [ ] Resultado de `DEBUG=False`.
- [ ] Resultado de tests críticos en verde.

---

## 4) Criterio de Cierre (Release Gate)

Se considera “listo para producción” cuando:

- [ ] Las 3 secciones anteriores están completas.
- [ ] Existe evidencia guardada (capturas/logs/enlaces).
- [ ] No hay errores bloqueantes abiertos.

---

## 5) Registro Final (rellenar)

- Fecha:
- Responsable:
- Entorno:
- RTO:
- RPO:
- Estado final: `APROBADO` / `NO APROBADO`
- Observaciones:
