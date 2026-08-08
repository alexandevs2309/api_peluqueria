# 🧪 Guía de Ejecución: Suite de Pruebas E2E de Personas Reales (Full Persona Journey)

Esta suite automatizada simula el comportamiento de **5 Personas Reales** interactuando en secuencia con la plataforma Auron Suite a través de llamadas HTTP y autenticación por cookies/JWT en la API de Django REST Framework.

---

## 🎭 Personas y Flujos Evaluados

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                 PERSONAS REALES EVALUADAS                                │
├─────────────────────────┬──────────────────────────┬─────────────────────────────────────┤
│ Persona                 │ Rol                      │ Flujos y Endpoints                  │
├─────────────────────────┼──────────────────────────┼─────────────────────────────────────┤
│ 1. SuperAdmin           │ Plataforma Global        │ Health Check, Planes SaaS, Ingesta  │
│ 2. Dueño de Salón       │ Client-Admin / Owner     │ Registro, Catálogo, NCF, Personal   │
│ 3. Recepcionista        │ Cajera                   │ Caja, Clientes, Citas, POS y Cobro  │
│ 4. Barbero / Estilista  │ Empleado                 │ Asistencia, Comisiones, Ataque RBAC │
│ 5. Auditor de Planes    │ Auditor Financiero       │ TSS/ISR, Nómina, Paywall de Planes  │
└─────────────────────────┴──────────────────────────┴─────────────────────────────────────┘
```

---

## 🚀 Cómo Ejecutar la Suite

### Opción 1: Contra el Servidor en Ejecución (Local o Docker)
```bash
cd /home/auron/Descargas/proyect
python scripts/test_persona_real_e2e.py --base-url http://localhost:8001/api
```

### Opción 2: Dentro del Contenedor Docker
```bash
docker compose exec web python scripts/test_persona_real_e2e.py --base-url http://localhost:8000/api
```

### Opción 3: Modo Nativo Django (APIClient sin servidor HTTP activo)
```bash
cd /home/auron/Descargas/proyect
python scripts/test_persona_real_e2e.py --django-client
```

---

## 📊 Matriz de Cobertura de la Suite

1. **Autenticación y Seguridad:**
   * `/api/auth/register/` (Onboarding con creación atómica de Tenant)
   * `/api/auth/cookie-login/` y `/api/auth/login/` (Emisión de JWT/Session)
   * `/api/auth/users/` (Consulta de perfiles)

2. **Suscripciones y Monetización:**
   * `/api/subscriptions/plans/` (Consulta de catálogo de planes)
   * `/api/subscriptions/me/entitlements/` (Verificación de features activas)

3. **Punto de Venta y Facturación DGII:**
   * `/api/pos/ncf-sequences/` (Secuencia fiscal B02)
   * `/api/pos/cashregisters/` (Apertura y cierre de caja)
   * `/api/pos/sales/` (Venta multilínea con cálculo de comisiones e ITBIS)

4. **Operación de Citas y Servicios:**
   * `/api/clients/clients/` (Creación de clientes)
   * `/api/services/services/` (Catálogo de servicios y precios)
   * `/api/appointments/appointments/` (Agendamiento y confirmación de turnos)

5. **Nómina y Asistencia:**
   * `/api/employees/attendance/check_in/` y `/check_out/`
   * `/api/employees/payroll/config/` (Deducciones TSS y parámetros fiscales)
   * `/api/employees/payroll/client/payroll/my-earnings/` (Comisiones en vivo del estilista)
   * `/api/employees/payroll/client/payroll/{id}/recalculate/` (Recálculo determinístico)
   * `/api/employees/payroll/client/payroll/register_payment/` (Liquidación de nómina)

6. **Defensa y Seguridad RBAC:**
   * Intento de acceso no autorizado de estilista a `/api/reports/dashboard/` -> **Verificación de 403 Forbidden**.
   * Intento de modificación no autorizada a `/api/system-settings/` -> **Verificación de 403 Forbidden**.
