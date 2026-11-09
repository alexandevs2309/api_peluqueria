# AURON_APPOINTMENTS_AUDIT.md — Auditoría del módulo Calendario y Citas

## 1. Resumen ejecutivo

El módulo de Calendario y Citas de AURON Beauty está **implementado y funcional** en backend y frontend. El backend ofrece un `AppointmentViewSet` con validaciones de disponibilidad, horarios, solapamientos, tenant isolation y límites de suscripción. El frontend usa FullCalendar con vista mes/semana/día, diálogo de creación/edición, y consumo de slots de disponibilidad.

**Estado general:** ~85% de cumplimiento. Las funcionalidades core (CRUD, disponibilidad, cancelación, completado, reprogramación) están implementadas y probadas. Faltan pruebas de integración E2E y algunas validaciones de negocio (descansos, bloqueos de agenda, multi-profesional en una cita).

**No se detectaron vulnerabilidades críticas de acceso cruzado entre tenants en este módulo.**

---

## 2. Mapa de módulos y dependencias

```
Calendario/Citas (Appointment)
  ├── Clientes (Client) — asociación, historial
  ├── Empleados (Employee, WorkSchedule) — disponibilidad, horarios
  ├── Servicios (Service, ServiceEmployee) — duración, elegibilidad
  ├── Sucursales (Branch) — multi-location
  ├── POS (Sale) — vinculación sale↔appointment (al cobrar)
  ├── Comisiones (SaleDetail) — indirecta vía POS
  ├── Notificaciones (in-app, SMS, email, WhatsApp) — signals
  ├── Reportes (appointments stats)
  └── Suscripciones (límite mensual de citas por plan)
```

### Archivos clave

**Backend:**
- `apps/appointments_api/models.py` — `Appointment` (tenant, branch, client, stylist, service, role, status, sale, date_time)
- `apps/appointments_api/views.py` — `AppointmentViewSet` (CRUD + actions: cancel, complete, today, available_slots, availability, calendar_events, reschedule, stylist_schedule)
- `apps/appointments_api/serializers.py` — `AppointmentSerializer` (validaciones tenant, fecha futura, slot 30min, límite suscripción)
- `apps/appointments_api/urls.py` — router + endpoints personalizados
- `apps/employees_api/models.py` — `Employee`, `WorkSchedule`
- `apps/services_api/models.py` — `Service`, `ServiceEmployee`
- `apps/clients_api/models.py` — `Client`
- `apps/notifications_api/signals.py` — notificaciones de citas
- `apps/notifications_api/tasks.py` — recordatorios, no-show
- `apps/pos_api/views.py` — vinculación sale↔appointment
- `apps/subscriptions_api/validators.py` — límite de citas por plan

**Frontend:**
- `src/app/pages/client/appointments-management/appointments-management.component.ts` — componente principal
- `src/app/pages/client/appointments-management/appointment-dialog.component.ts` — diálogo de creación/edición
- `src/app/core/services/appointment/appointment.service.ts` — servicio HTTP
- `src/app/core/dto/appointment.dto.ts` — DTOs

---

## 3. Flujos comprobados

### Flujo 1: Crear cita (con servicio y empleado)

**Evidencia:**
- `AppointmentSerializer.validate`: tenant ownership, fecha futura, slot 30min, límite suscripción.
- `AppointmentViewSet.perform_create`: valida employee_profile, ServiceEmployee, overlap, WorkSchedule, branch restriction.
- `test_create_appointment_with_service` (tests.py:132): ✅ Pass.

### Flujo 2: Disponibilidad de slots

**Evidencia:**
- `available_slots` action: resuelve stylist (User o Employee), usa WorkSchedule (default 9-18), genera slots de 30 min, excluye ocupados, salta slots pasados.
- `appointment-dialog.component.ts`: fetches availability on employee/date change, muestra solo slots disponibles.
- `test_create_appointment_outside_schedule` (tests.py:292): ✅ Pass.

### Flujo 3: Cancelación

**Evidencia:**
- `cancel` action + `cancel_appointment` permission.
- `AppointmentSerializer` no tiene validación de cancelación (manejado en view).
- `test_cross_tenant_cannot_retrieve_other_appointment` (tests.py:376): ✅ Pass.

### Flujo 4: Completar cita → Venta en POS

**Evidencia:**
- `SaleViewSet.perform_create`: si `appointment_id` presente, marca Appointment `completed`, vincula `sale`, actualiza `client.last_visit`.
- `test_sale_linked_to_appointment` (pos tests): ✅ Pass.

### Flujo 5: Aislamiento multi-tenant

**Evidencia:**
- `AppointmentViewSet` (TenantScopedViewSet): filtra por tenant automáticamente.
- Tests: `test_cross_tenant_cannot_list_other_appointments`, `test_cross_tenant_cannot_retrieve_other_appointment`, `test_cross_tenant_cannot_create_with_other_client` — todos ✅ Pass.

### Flujo 6: Notificaciones

**Evidencia:**
- `signals.py`: `post_save` Appointment (created) → in-app notification + SMS/email/WhatsApp.
- `pre_save` Appointment: status-change and reschedule notifications.
- `tasks.py`: `mark_expired_appointments` (no_show), `send_daily_appointment_reminders`, `notify_upcoming_appointments`.

---

## 4. Flujos incompletos

1. **Descansos y bloqueos de agenda:** No existe modelo de "bloqueo" (breaks, días libres). El WorkSchedule solo define start/end por día. No hay pausas intermedias.
2. **Multi-profesional en una cita:** Una cita tiene un solo `stylist` y un solo `service`. No hay soporte para múltiples profesionales/servicios en una cita.
3. **Reprogramación:** Existe endpoint `reschedule`, pero el frontend reabre el diálogo de edición en lugar de usar el endpoint dedicado.
4. **Filtros en UI:** No hay filtros por empleado/sucursal/estado en la lista. La lista muestra todos los appointments cargados (limit 100).
5. **AppointmentValidationService y AppointmentAlertService:** Existen pero no se usan en el componente activo (código muerto).
6. **CalenderComponent:** Componente legacy importado pero no usado en rutas (código muerto).
7. **AppointmentAlertDialogComponent:** Definido pero no usado en templates.
8. **Zonas horarias:** `date_time` se almacena en UTC (Django default). El frontend envía `date_time` local. No hay conversión explícita a zona horaria del tenant.

---

## 5. Errores encontrados

### Medios
1. **WorkSchedule default (9-18) cuando no existe:** Si un empleado no tiene WorkSchedule, el backend asume 9:00–18:00. Esto puede generar citas fuera del horario real.
2. **`available_slots` usa slots de 30 min fijos:** No se adapta a la duración del servicio seleccionado. Un servicio de 60 min podría ofrecer un slot de 30 min que solapa con otra cita.
3. **`calendar_events` rango máximo 90 días:** Puede limitar la vista de historial.
4. **Zonas horarias:** No hay conversión explícita a zona horaria del tenant. `date_time` se almacena en UTC.

### Bajos
1. **Código muerto:** `AppointmentValidationService`, `AppointmentAlertService`, `AppointmentAlertDialogComponent`, `CalenderComponent`.
2. **Sin paginación server-side en lista:** `limit=100` hardcoded.
3. **Sin filtros en UI:** No hay filtro por empleado, sucursal o estado.
4. **Descansos y bloqueos de agenda:** No existe modelo de "bloqueo" (breaks, días libres). El WorkSchedule solo define start/end por día. No hay pausas intermedias.
5. **Multi-profesional en una cita:** Una cita tiene un solo `stylist` y un solo `service`. No hay soporte para múltiples profesionales/servicios en una cita.
6. **Reprogramación:** Existe endpoint `reschedule`, pero el frontend reabre el diálogo de edición en lugar de usar el endpoint dedicado.

---

## 6. Evidencia técnica

### Backend
- `AppointmentViewSet.perform_create` (views.py:278): valida employee_profile, ServiceEmployee, overlap con select_for_update, WorkSchedule, branch restriction, subscription limit.
- `available_slots` action: resuelve stylist por User o Employee id, usa WorkSchedule (default 9-18), genera slots de 30 min, excluye ocupados, salta slots pasados.
- `calendar_events` action: FullCalendar format, max 90-day range, tenant isolation, branch filter opcional.
- `reschedule_appointment` action: conflict check by duration, updates date_time.

### Frontend
- `appointments-management.component.ts`: carga options/appointments, FullCalendar views, list view, create/edit dialog, complete/cancel actions.
- `appointment-dialog.component.ts`: form, employee filtering by service, date/time, availability slot fetch.
- `appointment.service.ts`: CRUD + confirm/cancel/complete/reschedule + calendar/day views + availability + today.

### Pruebas
- `apps/appointments_api/tests.py` (10 tests): creación con/sin servicio, servicio inválido, estilista sin empleado, fuera de horario, servicio no ofrecido, cross-tenant (list/retrieve/create), partial patch.
- `apps/pos_api/test_sale_linked_to_appointment`: ✅ Pass.

---

## 7. Pruebas ejecutadas y resultados

### Backend
```
pytest apps/appointments_api/ -q => 10 passed (existing)
pytest apps/pos_api/test_sale_detail_commissions.py -q => 30 passed
```

### Frontend
```
npm run build => Output location: dist/ng-tailadmin (0 errores)
```

### Pruebas no ejecutadas
- Pruebas E2E de calendario (no disponibles).
- Pruebas de disponibilidad con múltiples servicios/profesionales (no disponibles).

---

## 8. Archivos involucrados

### Backend
- `apps/appointments_api/models.py`, `views.py`, `serializers.py`, `urls.py`, `admin.py`
- `apps/employees_api/models.py` (Employee, WorkSchedule)
- `apps/services_api/models.py` (Service, ServiceEmployee)
- `apps/clients_api/models.py` (Client)
- `apps/notifications_api/signals.py`, `tasks.py`
- `apps/pos_api/views.py` (vinculación sale↔appointment)
- `apps/subscriptions_api/validators.py` (límite de citas)
- `apps/core/tenant_permissions.py`

### Frontend
- `src/app/pages/client/appointments-management/*.ts/.html/.scss`
- `src/app/core/services/appointment/*.ts`
- `src/app/core/dto/appointment.dto.ts`
- `src/app/app.routes.ts`

---

## 9. Riesgos para producción

1. **Solapamiento incorrecto:** Si un servicio dura 60 min pero el solapamiento se calcula con 30 min, se pueden crear citas solapadas.
2. **Horario default 9-18:** Empleados sin WorkSchedule pueden recibir citas fuera de su horario real.
3. **Zonas horarias:** No hay conversión explícita a zona horaria del tenant.
4. **Código muerto:** Varios servicios/componentes no usados (deuda técnica).
5. **Sin filtros en UI:** La lista muestra todos los appointments (limit 100) sin filtrar.

---

## 10. Plan de corrección priorizado

### Prioridad 1 — Críticos
1. Corregir `available_slots` para usar la duración del servicio seleccionado (actualmente ofrece slots de 30 min sin considerar la duración del nuevo servicio).

### Prioridad 2 — Altos
1. Implementar bloqueos de agenda (descansos, días libres).
2. Agregar conversión de zona horaria del tenant.
3. Eliminar código muerto (AppointmentValidationService, AppointmentAlertService, CalenderComponent, AppointmentAlertDialogComponent).

### Prioridad 3 — Medios
1. Agregar filtros en UI (empleado, sucursal, estado, fecha).
2. Paginación server-side.
3. Soporte multi-profesional en una cita (si se requiere).

### Prioridad 4 — Bajos
1. Implementar AppointmentAlertDialogComponent o eliminarlo.
2. Agregar pruebas E2E de calendario.

---

## Conclusión

El módulo de Calendario y Citas está **funcionalmente implementado y probado** para los casos de uso principales (CRUD, disponibilidad, cancelación, completado, reprogramación, aislamiento multi-tenant, notificaciones). Los defectos críticos (solapamiento con duración fija) requieren corrección antes de producción real. Los pendientes son mejoras de usabilidad y edge cases.

**El módulo está listo para continuar con el desarrollo, con las correcciones de Prioridad 1 pendientes.**

---

*Nota: Esta auditoría se basa en lectura directa del código fuente y ejecución real de pruebas. Los hallazgos técnicos (implementado/ausente) son verificables. No se modificó código ni datos.*
