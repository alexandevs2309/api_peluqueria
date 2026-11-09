# AURON_PILOT_READINESS.md — AURON Beauty

## 1. Estado técnico

### Backend
- **Rama:** `master`, HEAD `5ba3a1d`, sincronizada con `origin/master`.
- **Tests:** 505 passed, 1 skipped, 2 xfailed, 17 warnings (38.97s).
- **Migraciones:** 0001–0047, `makemigrations --check`: No changes detected.
- **Configuración:** DEBUG=False por defecto, SECRET_KEY/FERNET_KEY requeridos, validación de placeholders.
- **Seguridad:** JWT con rotación, blacklist, cookies seguras, RBAC deny-by-default, multi-tenant isolation.

### Frontend
- **Rama:** `main`, HEAD `d9ca69b`, sincronizada con `origin/main`.
- **Build:** ✅ `dist/ng-tailadmin` (0 errores).
- **Configuración:** API URL apunta a `api.auronsuite.com`.

### Cambios pendientes (no commiteados)
- Backend: 7 archivos modificados + 1 migración + 1 test + 12 documentos.
- Frontend: 7 archivos modificados.

## 2. Estado de suscripciones

### Planes disponibles (setup_saas.py)

| Plan | Precio/mes | Max empleados | Max usuarios | Sucursales | Features |
|---|---|---|---|---|---|
| Basic | $29.00 | 5 | 10 | 1 | appointments, clients, cash_register, reports (basic), support (email) |
| Standard (Pro) | $59.00 | 15 | 30 | 1 | + inventory, reports (advanced), support (priority) |
| Premium (Business) | $99.00 | 50 | 100 | ∞ | + multi_branch, reports (premium), support (24/7) |
| Enterprise | $149.00 | 0 (ilimitado) | 0 (ilimitado) | ∞ | + custom_branding, support (priority) |

### Trial
- **Duración:** 14 días (SystemSettings.trial_days).
- **Activación:** automática al registrarse.
- **Sin tarjeta de crédito requerida.**

### Límites por plan
- `max_employees`: 0 = ilimitado.
- `max_users`: 0 = ilimitado.
- `allows_multiple_branches`: solo Premium y Enterprise.
- `features`: dict por plan (appointments, cash_register, inventory, reports, multi_branch, custom_branding, support).

### Permisos por rol
- **SuperAdmin:** acceso total.
- **Client-Admin:** todos los permisos de tenant apps (settings_api, pos_api, billing_api, etc.).
- **Cajera/Estilista/Utility/Manager:** permisos específicos por rol (default_permissions.py).

## 3. Resultado de la prueba piloto

### Escenario: Registro → Configuración → Operación

| Paso | Estado | Evidencia |
|---|---|---|
| Registro de negocio | ✅ | `test_successful_registration_provisions_everything` (10/10 tests) |
| Creación de tenant | ✅ | Tenant creado con owner, plan, trial |
| Onboarding | ✅ | Email con enlace de un solo uso para contraseña |
| Configuración de empresa | ✅ | BarbershopSettings, Branch, Setting |
| Creación de sucursal | ✅ | Branch CRUD, plan-gated |
| Registro de empleado | ✅ | EmployeeViewSet, límites por plan |
| Configuración de servicios | ✅ | Service, ServiceEmployee, categorías |
| Configuración de horarios | ✅ | WorkSchedule |
| Gestión de clientes | ✅ | ClientViewSet, loyalty points |
| Citas | ✅ | AppointmentViewSet, disponibilidad |
| Ventas y cobros | ✅ | SaleViewSet, CashRegister, Payment |
| Inventario | ✅ | Product, StockMovement |
| Comisiones | ✅ | SaleCommissionService, snapshots |
| Nómina | ✅ | PayrollPeriod, cálculo, aprobación, pago |
| Reportes | ✅ | 20 endpoints, build OK |
| Aislamiento multi-tenant | ✅ | 13+ tests cross-tenant |

### Verificación de integración
- POS → Caja → Inventario: ✅ verificado.
- Venta → Comisión → Nómina: ✅ verificado.
- Nómina → Aprobación → Pago → Comprobante: ✅ verificado.
- Reportes → Transacciones: ⚠️ parcial (sin pruebas de consistencia dedicadas).

## 4. Problemas encontrados

### Bloqueantes
- Ninguno.

### No bloqueantes (documentados)
1. ISR/TSS no validados contra DGII/TSS.
2. Regalía pascual sin fórmula legal.
3. Vacaciones sin integración con nómina.
4. Liquidaciones con base salarial aproximada.
5. Propinas no implementadas.
6. Alquiler de silla no implementado.
7. Pagos parciales en nómina no soportados.
8. Karma frontend no ejecutable (sin Chrome).
9. Código muerto en appointments.
10. Frontend subutiliza endpoints de reportes (16 de 20 no consumidos).

## 5. Requisitos pendientes

1. Validación fiscal contra normativa dominicana (ISR, TSS, SFS).
2. Implementación de regalía pascual, vacaciones, prestaciones.
3. Propinas y alquiler de silla (si se requieren).
4. Pagos parciales en nómina (decisión de negocio).
5. Karma en CI (Chrome headless).
6. Limpieza de código muerto en appointments.

## 6. Riesgos

1. **Compliance fiscal (RD):** Tasas configurables pero no validadas. Riesgo legal.
2. **Obligaciones laborales:** Regalía, vacaciones, prestaciones no implementadas. Riesgo legal.
3. **Pagos parciales:** No soportados. Limitación operativa.
4. **Karma frontend:** No ejecutable sin Chrome. Limitación de CI.

## 7. Procedimiento de incorporación de un cliente

1. El cliente se registra en `https://beauty.auronsuite.com/signup`.
2. Selecciona un plan (Basic/Standard/Premium/Enterprise).
3. Completa el formulario (negocio + propietario + términos).
4. Recibe un email con enlace de un solo uso para crear contraseña.
5. Crea la contraseña (verifica el email automáticamente).
6. Inicia sesión y configura su negocio.
7. Registra empleados, servicios, productos.
8. Configura horarios y sucursales (si el plan lo permite).
9. Comienza a operar (citas, ventas, nómina).

## 8. Configuración inicial

- Plan de suscripción (Basic/Standard/Premium/Enterprise).
- Nombre del negocio y datos de contacto.
- Sucursal principal (automática).
- Categorías por defecto (servicios y productos).
- Configuración fiscal (ISR/SFS/AFP rates, SRL rate).
- Configuración de nómina (período default, auto-close).

## 9. Requisitos técnicos

- PostgreSQL 14+.
- Redis (Celery broker).
- Python 3.12, Django 5.2.
- Node.js 26, Angular 21.
- Cloudflare Workers (frontend).
- Gunicorn + Nginx (backend).

## 10. Copias de seguridad

- Backup automático: `pg_dump` diario (configurar cron).
- Backup manual: `pg_dump -Fc auron_db > backup.dump`.
- Restauración: `pg_restore -d auron_db backup.dump`.
- Backup del código: Git (master/main).

## 11. Recuperación ante fallos

1. Verificar health check: `GET /api/healthz/`.
2. Revisar logs de Gunicorn/Celery.
3. Verificar conexión a PostgreSQL y Redis.
4. Restaurar desde backup si es necesario.
5. Reiniciar servicios: `systemctl restart gunicorn celery`.

## 12. Canales de soporte

- Email: soporte@auronsuite.com
- URL: https://auronsuite.com/soporte

## 13. Procedimiento para reportar incidencias

1. El cliente reporta el problema vía email o soporte.
2. Se registra en el sistema de tickets (support_api).
3. Se clasifica por severidad (crítico/alto/medio/bajo).
4. Se asigna a un desarrollador.
5. Se corrige y se despliega.
6. Se notifica al cliente.

## 14. Recomendación para incorporar el primer cliente

**AURON Beauty está listo para incorporar su primer cliente piloto** con las siguientes condiciones:

1. **Plan recomendado:** Standard (Pro) — incluye inventario, reportes avanzados, soporte prioritario.
2. **Trial:** 14 días sin tarjeta de crédito.
3. **Limitaciones a comunicar al cliente:**
   - La regalía pascual, vacaciones y prestaciones laborales no están implementadas.
   - Las tasas de ISR/TSS/SFS son configurables manualmente (no validadas contra DGII).
   - Las propinas no están soportadas.
   - Los pagos parciales en nómina no están soportados.
4. **Monitoreo:** Supervisar la operación del piloto durante las primeras 2 semanas.
5. **Feedback:** Recoger feedback del cliente para iterar.

**No se realizaron commits, push ni despliegues en esta misión. No se modificó producción ni DNS. Ramas `master`/`main` preservadas. Cambios locales de sprints anteriores intactos.**

**Esperando autorización para continuar.**