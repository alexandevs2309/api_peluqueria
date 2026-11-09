# PAYROLL_ENGINE_API_CONTRACT.md — AURON Beauty

## Endpoints de nómina

### GET /api/employees/payroll/client/payroll/
- **Método:** GET
- **Permisos:** `employees_api.view_employee_payroll`
- **Parámetros:** `status` (opcional, filtro)
- **Respuesta:** `{ periods: [{id, employee_id, employee_name, period_display, status, base_salary, commission_earnings, gross_amount, net_amount, deductions_total, period_start, period_end, can_pay, pay_block_reason, employee_payment_type, employee_commission_rate, employee_profession, services_count, gross_sales, christmas_bonus, backendStatus}] }`
- **Estados posibles:** open, pending_approval, approved, paid, rejected

### GET /api/employees/payroll/client/payroll/{id}/detail/
- **Método:** GET
- **Permisos:** `employees_api.view_employee_payroll`
- **Respuesta:** `{period_id, employee, period, compensation, amounts, services[], adjustments[], deductions[], can_pay, pay_block_reason, employer_contributions}`
- **Errores:** 404 (no encontrado), 403 (sin permiso)

### POST /api/employees/payroll/client/payroll/ensure-period/
- **Método:** POST
- **Permisos:** `employees_api.change_employee_payroll`
- **Body:** `{employee_id: int}`
- **Respuesta:** `{id, employee_id, status, net_amount, gross_amount, created}`

### POST /api/employees/payroll/client/payroll/{id}/submit/
- **Método:** POST
- **Permisos:** `employees_api.change_employee_payroll`
- **Respuesta:** `{message, status}`
- **Errores:** 400 (solo se pueden enviar períodos abiertos), 404

### POST /api/employees/payroll/client/payroll/{id}/approve/
- **Método:** POST
- **Permisos:** `employees_api.approve_payroll`
- **Respuesta:** `{message, status}`
- **Errores:** 400 (solo pendientes, neto ≤ 0), 404

### POST /api/employees/payroll/client/payroll/{id}/reject/
- **Método:** POST
- **Permisos:** `employees_api.approve_payroll`
- **Body:** `{reason: string}`
- **Respuesta:** `{message, status, reason}`
- **Errores:** 400 (solo pendientes), 404

### POST /api/employees/payroll/client/payroll/{id}/recalculate/
- **Método:** POST
- **Permisos:** `employees_api.change_employee_payroll`
- **Respuesta:** `{message, gross_amount, net_amount}`
- **Errores:** 400 (no se puede recalcular aprobado/pagado), 404

### POST /api/employees/payroll/client/payroll/register_payment/
- **Método:** POST
- **Permisos:** `employees_api.approve_payroll`
- **Body:** `{period_id, payment_method, payment_reference?}`
- **Respuesta:** `{payment_id, message, amount_paid, paid_at}`
- **Errores:** 400 (no aprobado, ya pagado, can_pay false), 404

### GET /api/employees/payroll/client/payroll/history/
- **Método:** GET
- **Permisos:** `employees_api.view_employee_payroll`
- **Respuesta:** `{periods: [{id, employee_name, period_display, status, base_salary, commission_earnings, gross_amount, net_amount, deductions_total, period_start, period_end, can_pay, pay_block_reason, paid_at}]}`

### GET /api/employees/payroll/client/payroll/my-earnings/
- **Método:** GET
- **Permisos:** `employees_api.view_employee_payroll`
- **Respuesta:** `{periods: [{id, period_display, status, base_salary, commission_earnings, gross_amount, net_amount, deductions_total, period_start, period_end, can_pay, pay_block_reason, payment_method, paid_at, christmas_bonus}]}`

### GET /api/employees/payroll/client/payroll/my-summary/
- **Método:** GET
- **Permisos:** `employees_api.view_employee_payroll`
- **Respuesta:** `{total_gross, total_net, total_deductions, paid_periods, pending_periods, payment_type, commission_rate}`

### GET /api/employees/payroll/payments/{id}/receipt/
- **Método:** GET
- **Permisos:** `employees_api.view_employee_payroll`
- **Respuesta:** `{payment_id, company, employee, period, amounts, payment_info, employer_contributions}`
- **Errores:** 400 (no pagado), 404

### GET/PUT /api/employees/payroll/config/
- **Método:** GET/PUT
- **Permisos:** GET: `view_employee_payroll`, PUT: `manage_payroll_config`
- **Body (PUT):** `{default_period_type, social_security_rate, health_insurance_rate, auto_close_periods, tax_rate, srl_rate}`
- **Respuesta:** `{id, tenant, default_period_type, tax_rate, social_security_rate, health_insurance_rate, srl_rate, auto_close_periods}`

## Endpoints de regalía pascual

### POST /api/employees/payroll/client/payroll/generate-regalia/
- **Método:** POST
- **Permisos:** `employees_api.change_employee_payroll`
- **Body:** `{year: int}`
- **Respuesta:** `{message, year}`

### GET /api/employees/payroll/client/payroll/regalia/
- **Método:** GET
- **Permisos:** `employees_api.view_employee_payroll`
- **Parámetros:** `year` (opcional)
- **Respuesta:** `{regalias: [{id, employee_id, employee_name, year, ordinary_salary_annual, amount, is_tax_exempt, status, paid_at}]}`

### POST /api/employees/payroll/client/payroll/regalia/{id}/pay/
- **Método:** POST
- **Permisos:** `employees_api.approve_payroll`
- **Body:** `{reference: string}`
- **Respuesta:** `{message, amount}`
- **Errores:** 400 (ya pagada), 404

## Endpoints de vacaciones

### POST /api/employees/payroll/client/payroll/generate-vacations/
- **Método:** POST
- **Permisos:** `employees_api.change_employee_payroll`
- **Body:** `{year: int}`
- **Respuesta:** `{message, year}`

### GET /api/employees/payroll/client/payroll/vacations/
- **Método:** GET
- **Permisos:** `employees_api.view_employee_payroll`
- **Parámetros:** `year` (opcional)
- **Respuesta:** `{vacations: [{id, employee_id, employee_name, year, days_entitled, days_taken, days_remaining, paid_amount, status, start_date, end_date}]}`

### POST /api/employees/payroll/client/payroll/vacations/{id}/enjoy/
- **Método:** POST
- **Permisos:** `employees_api.change_employee_payroll`
- **Body:** `{start_date: date, end_date: date}`
- **Respuesta:** `{message, days_taken}`
- **Errores:** 400 (menos de 1 semana), 404

### POST /api/employees/payroll/client/payroll/vacations/{id}/compensate/
- **Método:** POST
- **Permisos:** `employees_api.approve_payroll`
- **Body:** `{termination_type: string, payroll_period_id?: int}`
- **Respuesta:** `{message, paid_amount}`
- **Errores:** 400 (ya compensada, causa no permitida), 404

## Endpoints de liquidaciones

### POST /api/employees/payroll/client/payroll/generate-liquidacion/
- **Método:** POST
- **Permisos:** `employees_api.change_employee_payroll`
- **Body:** `{employee_id, termination_date, termination_type, total_utilities?, total_payroll?, participacion_exempt?, asistencia_economica?}`
- **Respuesta:** `{id, total, preaviso, cesantia, vacaciones, regalia, participacion}`
- **Errores:** 400 (datos faltantes), 404

### GET /api/employees/payroll/client/payroll/liquidaciones/
- **Método:** GET
- **Permisos:** `employees_api.view_employee_payroll`
- **Respuesta:** `{liquidaciones: [{id, employee_id, employee_name, termination_date, termination_type, total, status, paid_at}]}`

### POST /api/employees/payroll/client/payroll/liquidaciones/{id}/pay/
- **Método:** POST
- **Permisos:** `employees_api.approve_payroll`
- **Body:** `{reference: string}`
- **Respuesta:** `{message, total}`
- **Errores:** 400 (ya pagada), 404

## Estados posibles

### PayrollPeriod
- `open` → `pending_approval` → `approved` → `paid`
- `open` → `pending_approval` → `rejected`

### RegaliaPascual
- `calculated` → `paid`

### Vacation
- `pending` → `enjoyed` / `compensated`

### Liquidacion
- `calculated` → `paid`

## Permisos

| Permiso | Descripción |
|---|---|
| `employees_api.view_employee_payroll` | Consultar nómina, recibos, historial, detalle |
| `employees_api.change_employee_payroll` | Recalcular, enviar a aprobación, generar regalía/vacaciones/liquidación |
| `employees_api.approve_payroll` | Aprobar, rechazar, registrar pago, pagar regalía/liquidación |
| `employees_api.manage_employee_loans` | Gestionar préstamos |
| `employees_api.manage_payroll_config` | Modificar configuración de nómina |

## Errores esperados

| Código | Descripción |
|---|---|
| 400 | Datos inválidos, estado no permitido, monto ≤ 0, ya pagado |
| 403 | Sin permiso, sin tenant, tenant mismatch |
| 404 | Recurso no encontrado |
| 429 | Rate limit excedido (throttle) |
