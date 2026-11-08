# BUSINESS_RULES.md — AURON Beauty

## 1. Reglas de negocio implementadas (verificadas en código)

### POS
- Una venta puede contener múltiples artículos (servicios y productos).
- Cada línea de venta puede tener un empleado asignado.
- Los productos no generan comisión (regla de negocio aprobada).
- Los servicios generan comisión según el tipo de compensación del empleado (commission/mixed).
- Los descuentos globales se aplican al total de la venta, no a las líneas individuales.
- Las promociones y cupones se validan contra fecha, uso máximo y mínimo de compra.
- El NCF se genera automáticamente solo si `enable_ncf=True` y el cliente tiene RNC.
- La caja debe estar abierta para registrar ventas.
- El inventario se actualiza atómicamente con `select_for_update`.

### Comisiones
- Fuente única: una venta con comisiones por línea (line-source) NUNCA aporta por sale-source.
- Orden de resolución de tasa: `ServiceEmployee.commission_percentage` → `EmployeeCompensationHistory` vigente → `employee.commission_rate`.
- Solo empleados con `payment_type` in (commission, mixed) generan comisión.
- La comisión se calcula sobre `line_total` (precio × cantidad), no sobre el total con descuentos globales.
- Los reembolsos revierten comisión proporcionalmente al monto reembolsado.
- Los snapshots son inmutables después de la creación.

### Nómina
- Salario fijo: monthly = fixed_salary, biweekly = fixed/2, weekly = prorrateo por días reales.
- Comisiones: sale-source + line-source (mutuamente excluyentes) + ajustes.
- Deducciones: asistencia (tardanza/ausencia), préstamos (cuotas), config (ISR/SFS/AFP).
- Aprobación: solo períodos `pending_approval` pueden aprobarse.
- Pago: solo períodos `approved` pueden pagarse.
- Períodos aprobados/pagados son inmutables (campos financieros bloqueados).
- Snapshots de compensación se capturan al crear el período.
- `EmployeeCompensationHistory` es inmutable (no se puede modificar ni eliminar).

### Multi-tenant
- Cada usuario pertenece a un tenant (excepto superadmins).
- Todos los querysets se filtran por tenant.
- RBAC es deny-by-default basado en BD.
- Superadmins tienen acceso total.

### Autenticación
- JWT con access (30 min) y refresh (7 días).
- Rotación de refresh tokens con blacklist.
- Cookies HttpOnly, Secure (prod), SameSite.
- MFA opcional.

## 2. Reglas pendientes de definición (requieren decisión del propietario)

1. **Comisión sobre descuentos globales**: ¿la comisión se calcula sobre el precio bruto de la línea o sobre el total con descuento global?
2. **Comisión sobre productos**: confirmado que productos no generan comisión. ¿Aplica a todos los casos?
3. **Propinas**: no implementadas. ¿Se deben implementar? ¿Cómo se distribuyen?
4. **Pagos parciales en nómina**: no soportados. ¿Se deben soportar?
5. **Salario semanal**: convención de prorrateo por días reales (implementada). ¿Es la política deseada?
6. **Compensación mid-período**: se usa la vigente al inicio. ¿Se debe prorratear?
7. **Regalía pascual**: no implementada. ¿Se debe implementar? ¿Fórmula?
8. **Vacaciones y prestaciones**: no implementadas. ¿Se deben implementar?
9. **ISR progresivo**: se usa tasa plana. ¿Se debe implementar tabla DGII?
10. **Tasas TSS/SFS**: manuales. ¿Se deben validar contra valores oficiales?
11. **Nomenclatura**: "Mis Ganancias" vs "Nómina". ¿Unificar?

## 3. Reglas que NO están implementadas

- Regalía pascual (art. 223 Código de Trabajo RD).
- Vacaciones (art. 183).
- Prestaciones laborales (art. 80).
- Tabla progresiva de ISR (DGII).
- Validación de tasas TSS/SFS contra valores oficiales.
- Propinas.
- Alquiler de silla / prestación independiente.
- Metas e incentivos.
- Pagos parciales en nómina.
- Reverso de pago completo.

## 4. Fuentes oficiales (pendientes de consulta)

- DGII: https://dgii.gov.do (tablas ISR, retenciones)
- TSS: https://tss.gov.do (tasas AFP/SFS)
- Ministerio de Trabajo: https://mt.gob.do (Código de Trabajo, regalía, vacaciones, prestaciones)
- DGII NCF: normativa de comprobantes fiscales
