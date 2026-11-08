# DEPENDENCY_MAP.md — AURON Beauty

## 1. Mapa de dependencias entre módulos

```
POS (Sale/SaleDetail/Payment/CashRegister/Promotion/Coupon/NCF)
  ├── Inventario (Product/StockMovement) — actualización atómica con lock
  ├── Servicios (Service/ServiceEmployee) — comisión por servicio
  ├── Clientes (Client) — loyalty points
  ├── Empleados (Employee) — asignación por línea
  ├── Citas (Appointment) — vinculación sale↔appointment
  ├── Caja (CashRegister) — arqueo
  └── Nómina (PayrollPeriod) — snapshots de comisión

Nómina (PayrollPeriod/PayrollDeduction/PayrollConfiguration)
  ├── Empleados (Employee, EmployeeCompensationHistory)
  ├── POS (Sale, SaleDetail, CommissionAdjustment)
  ├── Asistencia (AttendanceRecord) — deducciones por tardanza/ausencia
  ├── Préstamos (Loan) — cuotas automáticas
  ├── Configuración (PayrollConfiguration: ISR/SFS/AFP)
  └── Notificaciones (email al aprobar/pagar)

Comisiones (SaleCommissionService)
  ├── ServiceEmployee.commission_percentage
  ├── EmployeeCompensationHistory (vigente a la fecha de venta)
  └── Employee.commission_rate (global)

Multi-tenant
  ├── TenantMiddleware (JWT claim → tenant)
  ├── TenantValidationMiddleware
  ├── TenantScopedViewSet (auto-filter)
  ├── SubscriptionValidationMiddleware (trial/paywall)
  └── RBAC (UserRole → Role → Permission, deny-by-default)
```

## 2. Flujo financiero completo

```
Venta → Detalle de venta → Descuentos → Impuestos → Pago → Caja → Inventario → Comisión → Nómina → Pago al empleado → Recibo
```

### Dónde se genera cada importe

| Importe | Generado en | Almacenado en | Servicio |
|---|---|---|---|
| Total de venta | `SaleViewSet.perform_create` | `Sale.total` | POS |
| Descuento | `SaleViewSet.perform_create` | `Sale.discount` | POS |
| Impuestos (ITBIS) | `SaleViewSet.perform_create` | `Sale.tax` | POS |
| Comisión por línea | `SaleCommissionService.calculate_detail_commission` | `SaleDetail.commission_amount_snapshot` | POS |
| Comisión por venta | `SaleCommissionService.calculate_commission_snapshot` (legacy) | `Sale.commission_amount_snapshot` | POS |
| Salario base | `PayrollCalculationService.calculate_from_snapshots` | `PayrollPeriod.base_salary` | Nómina |
| Comisión ganada | `PayrollCalculationService.calculate_from_snapshots` | `PayrollPeriod.commission_earnings` | Nómina |
| Deducciones | `PayrollPeriod.calculate_amounts` | `PayrollDeduction` | Nómina |
| Bruto | `PayrollPeriod.calculate_amounts` | `PayrollPeriod.gross_amount` | Nómina |
| Neto | `PayrollPeriod.calculate_amounts` | `PayrollPeriod.net_amount` | Nómina |
| Pago al empleado | `PayrollPeriod.mark_as_paid` | `PayrollPeriod.net_amount`, `paid_at`, `paid_by` | Nómina |

### Dónde se almacena cada registro

| Registro | Modelo | Tabla |
|---|---|---|
| Venta | `Sale` | `pos_sale` |
| Detalle de venta | `SaleDetail` | `pos_saledetail` |
| Pago | `Payment` | `pos_payment` |
| Movimiento de caja | `CashRegister` | `pos_cashregister` |
| Movimiento de inventario | `StockMovement` | `inventory_stockmovement` |
| Comisión (snapshot) | `Sale.commission_amount_snapshot` | `pos_sale` |
| Comisión (snapshot línea) | `SaleDetail.commission_amount_snapshot` | `pos_saledetail` |
| Ajuste de comisión | `CommissionAdjustment` | `employees_commissionadjustment` |
| Período de nómina | `PayrollPeriod` | `employees_payrollperiod` |
| Deducción | `PayrollDeduction` | `employees_payrolldeduction` |
| Configuración de nómina | `PayrollConfiguration` | `employees_payrollconfiguration` |
| Historial de compensación | `EmployeeCompensationHistory` | `employees_employeecompensationhistory` |
| Préstamo | `Loan` | `employees_loan` |

### Modificaciones que se producen en cada operación

| Operación | Registros modificados |
|---|---|
| Crear venta | Sale (create), SaleDetail (create), StockMovement (create), Product.stock (update), CashRegister.sales_amount (update), Payment (create), Sale.commission snapshots (update), Appointment (update status), loyalty points (update) |
| Reembolso | Sale (amount_refunded, status), StockMovement (create, restore), CommissionAdjustment (create, negative), PayrollPeriod (recalc), Sale.commission_amount_snapshot (no se modifica, se crea ajuste) |
| Aprobar período | PayrollPeriod (status→approved, is_finalized=True, calculation_snapshot, can_pay=True) |
| Registrar pago | PayrollPeriod (status→paid, paid_at, paid_by, payment_method, payment_reference), Loan.remaining_balance (update), Loan.status (update si pagado) |
| Recalcular período | PayrollPeriod (base_salary, commission_earnings, gross_amount, net_amount), PayrollDeduction (delete auto + create auto) |

### Posibles inconsistencias identificadas

1. **Comisión sobre productos en ventas legacy**: si existen ventas históricas con `commission_amount_snapshot` a nivel de venta (calculado sobre total incluyendo productos), la nómina incluirá comisión sobre productos. Mitigación: las nuevas ventas usan fuente única (line-source para servicios, NULL para venta). Las históricas se respetan.
2. **Descuentos globales no afectan comisión**: la comisión se calcula sobre `line_total` (precio×cantidad), no sobre el total con descuento global. Si se aplica un descuento del 10% a la venta, la comisión sigue siendo sobre el precio bruto.
3. **Puntos de fidelidad no afectan comisión**: los puntos usados/obtenidos se registran pero no reducen la base de comisión.
4. **Pagos parciales en nómina no soportados**: un período solo puede pagarse completo. Si un empleado cobra parcialmente, no hay tracking.
5. **Reverso de pago completo**: no existe flujo de reverso de pago. Si se paga por error, no hay mecanismo para revertir (solo rechazo pre-pago).
6. **Compensación mid-período**: se usa la compensación vigente al inicio del período. Si cambia a mitad, no se prorratea.
