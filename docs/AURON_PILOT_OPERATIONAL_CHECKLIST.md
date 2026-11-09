# AURON_PILOT_OPERATIONAL_CHECKLIST.md — AURON Beauty

## 1. Estado de los repositorios

### Backend (`api_peluqueria`, rama `master`)
- **HEAD:** `5ba3a1d` (sincronizado con `origin/master`).
- **Working tree:** 7 archivos modificados + 1 migración + 1 test + 12 documentos (sin commitear).
- **Migraciones:** 0001–0047. `makemigrations --check`: No changes detected.
- **Tests:** 505 passed, 1 skipped, 2 xfailed, 17 warnings.
- **Cambios pendientes:** appointments/views.py, earnings_models.py, test_liquidacion.py, reports/urls.py, reports/views.py, barbershop_serializers.py, barbershop_views.py.

### Frontend (`auron-tailadmin`, rama `main`)
- **HEAD:** `d9ca69b` (sincronizado con `origin/main`).
- **Working tree:** 7 archivos modificados (sin commitear).
- **Build:** ✅ `dist/ng-tailadmin` (0 errores).

### Archivos sin respaldo
- Los cambios locales (7+7 archivos) no están commiteados. Se recomienda commitear antes del piloto.
- Backup de base de datos: `/tmp/opencode/api_peluqueria_backup_20261106_135614.tar.gz` (155 MB, verificado).

## 2. Configuración operativa

| Comprobación | Estado | Evidencia |
|---|---|---|
| Variables de entorno (SECRET_KEY, FERNET_KEY) | ✅ Requeridas en producción | `backend/settings.py` línea 34, 731 |
| DEBUG=False por defecto | ✅ | `env('DEBUG', default=False)` |
| Conexión PostgreSQL | ✅ Configurable | `DATABASE_URL` en settings |
| Redis/Celery | ✅ Configurable | `CELERY_BROKER_URL` |
| Envío de correos | ✅ Configurable | `EMAIL_HOST`, `RESEND_API_KEY` |
| JWT/Cookies/CORS | ✅ Configurado | `SIMPLE_JWT`, `CORS_ALLOWED_ORIGINS` |
| Dominios | ✅ | Frontend: `beauty.auronsuite.com`, Backend: `api.auronsuite.com` |
| HTTPS | ✅ | Cloudflare (frontend), Let's Encrypt (backend) |
| Health check | ✅ | `GET /api/healthz/` y `/api/healthz/public/` |

## 3. Copias de seguridad y recuperación

| Comprobación | Estado | Evidencia |
|---|---|---|
| Backup automático | ⚠️ No verificado | No hay cron configurado en el código |
| Última copia | ✅ Disponible | `/tmp/opencode/api_peluqueria_backup_20261106_135614.tar.gz` (155 MB) |
| Procedimiento de restauración | ✅ Documentado | `pg_restore -d auron_db backup.dump` |
| Archivos de configuración | ✅ En Git | `.env.production.example` |

**Acción manual necesaria:** Configurar cron para backup diario de PostgreSQL.

## 4. Verificación del onboarding

| Paso | Estado | Evidencia |
|---|---|---|
| Registro de negocio | ✅ | `POST /api/subscriptions/register/` |
| Selección de plan | ✅ | basic/standard/premium/enterprise |
| Creación de tenant | ✅ | Transaccional, probado |
| Activación por correo | ✅ | Email con enlace de un solo uso |
| Creación de contraseña | ✅ | `POST /api/auth/set-password/` |
| Inicio de sesión | ✅ | `POST /api/auth/login/` |
| Configuración inicial | ✅ | Branch, Setting, categorías automáticas |
| Creación de empleados | ✅ | `EmployeeViewSet`, límites por plan |
| Servicios y horarios | ✅ | Service, WorkSchedule |

**Pasos que requieren intervención manual:**
- Configurar DNS (ya hecho para producción).
- Configurar variables de entorno en el servidor.
- Ejecutar `setup_saas` para crear planes y superadmin.

## 5. Preparación de soporte y monitoreo

| Comprobación | Estado | Evidencia |
|---|---|---|
| Health check | ✅ | `/api/healthz/` y `/api/healthz/public/` |
| Registro de errores | ✅ | `apps/utils/middleware.py`, ErrorContextMiddleware |
| Logs de backend | ✅ | StructuredLoggingMiddleware, logging config |
| Identificación de errores por tenant | ✅ | `trace_id`, `tenant_id` en logs |
| Procedimiento de incidencias | ✅ | support_api (tickets) |
| Canales de soporte | ✅ | soporte@auronsuite.com, https://auronsuite.com/soporte |

## 6. Verificación de experiencia del cliente

| Aspecto | Estado | Observación |
|---|---|---|
| Registro | ✅ | Formulario guiado en 3 pasos |
| Configuración del negocio | ✅ | Plan, sucursal, categorías automáticas |
| Registro de empleados | ✅ | Formulario con validación de límites |
| Creación de citas | ✅ | Calendario visual, slots de disponibilidad |
| Realizar venta y cobrar | ✅ | POS con carrito, pagos, NCF |
| Consultar reportes | ✅ | Dashboard, ventas, caja, inventario, fiscal |

**Obstáculos reales encontrados:**
- El registro requiere que el email no esté duplicado (case-insensitive, ya corregido).
- La configuración fiscal (ISR/TSS) requiere conocimiento técnico del usuario.
- El onboarding no tiene un tutorial guiado paso a paso (solo email).

## 7. Clasificación de riesgos

| Riesgo | Clasificación | Mitigación |
|---|---|---|
| Cumplimiento fiscal (RD) | Importante | Validación profesional pendiente |
| Obligaciones laborales | Importante | No implementadas (regalía, vacaciones, prestaciones) |
| Pagos parciales en nómina | Menor | No soportado, documentado |
| Propinas | Menor | No implementado |
| Karma frontend | Menor | No ejecutable sin Chrome |
| Código muerto en appointments | Menor | Limpieza pendiente |
| Backup automático | Importante | Configurar cron |

## 8. Recomendación para incorporar al primer cliente

**AURON Beauty está operativamente preparado para recibir su primer cliente piloto** con las siguientes condiciones:

1. **Plan recomendado:** Standard (Pro) — $59/mes, 14 días de trial.
2. **Configuración inicial:** Ejecutar `setup_saas` para crear planes y superadmin.
3. **Backup:** Configurar cron para backup diario de PostgreSQL antes de incorporar clientes.
4. **Monitoreo:** Supervisar la operación durante las primeras 2 semanas.
5. **Limitaciones a comunicar:**
   - Regalía pascual, vacaciones y prestaciones no implementadas.
   - Tasas de ISR/TSS configurables manualmente.
   - Propinas no soportadas.
   - Pagos parciales en nómina no soportados.

**No se realizaron commits, push ni despliegues. No se modificó producción ni DNS. Ramas `master`/`main` preservadas. Cambios locales de sprints anteriores intactos.**

**Esperando autorización para continuar.**