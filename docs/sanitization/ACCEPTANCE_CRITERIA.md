# ACCEPTANCE_CRITERIA.md — AURON Beauty

## Criterios de aceptación por módulo

### POS

- [ ] Crear venta con múltiples artículos (servicios y productos).
- [ ] Asignar profesional por línea de venta.
- [ ] Aplicar descuentos individuales y globales.
- [ ] Aplicar promociones y cupones válidos.
- [ ] Registrar pagos en efectivo, tarjeta y mixtos.
- [ ] Abrir y cerrar caja con arqueo.
- [ ] Actualizar inventario atómicamente.
- [ ] Generar NCF cuando corresponda.
- [ ] Prevenir ventas duplicadas (idempotency).
- [ ] Cancelar y reembolsar ventas.
- [ ] Revertir comisiones por reembolso.

### Comisiones

- [ ] Comisión por servicio con porcentaje correcto.
- [ ] Diferentes porcentajes por empleado y servicio.
- [ ] Servicios realizados por varios profesionales.
- [ ] Productos no generan comisión.
- [ ] Servicios gratuitos no generan comisión.
- [ ] Prevención de doble conteo (fuente única).
- [ ] Snapshots históricos inmutables.
- [ ] Reversión de comisión por reembolso.
- [ ] Cambios de porcentaje no afectan ventas históricas.

### Nómina

- [ ] Salario fijo calculado correctamente (monthly/biweekly/weekly).
- [ ] Comisión calculada desde snapshots.
- [ ] Esquema mixto (base + comisión).
- [ ] Deducciones de asistencia (tardanza/ausencia).
- [ ] Deducciones de préstamos (cuotas automáticas).
- [ ] Deducciones de config (ISR/SFS/AFP).
- [ ] Ajustes manuales (bonos/penalizaciones).
- [ ] Aprobación de período (solo pending_approval).
- [ ] Rechazo de período con motivo.
- [ ] Registro de pago (solo approved).
- [ ] Protección de períodos aprobados/pagados.
- [ ] Generación de comprobante (solo si paid).
- [ ] Historial de períodos.
- [ ] Detalle financiero por empleado.
- [ ] My Earnings (solo datos propios).
- [ ] Snapshots inmutables.

### Empleados

- [ ] Alta, modificación y desactivación.
- [ ] Tipos de remuneración (fixed/commission/mixed).
- [ ] Configuración de comisiones.
- [ ] Sucursales y asignaciones.
- [ ] Activos/inactivos.
- [ ] Usuario↔empleado.
- [ ] Permisos y acceso salarial.
- [ ] Cambios de condiciones laborales.
- [ ] Historial de cambios (inmutable).

### Servicios

- [ ] CRUD y categorías.
- [ ] Comisión por servicio/empleado.

### Productos e inventario

- [ ] CRUD de productos.
- [ ] Movimientos de stock.
- [ ] Actualización atómica.

### Pagos y caja

- [ ] Caja (apertura/cierre/arqueo).
- [ ] Conciliación.
- [ ] Pagos en efectivo/tarjeta/mixtos.

### Citas

- [ ] CRUD y estados.
- [ ] Horarios y asistencia.

### Clientes

- [ ] CRUD y loyalty.

### Configuración fiscal

- [ ] NCF (generación, secuencias).
- [ ] Branding y settings.

### Sucursales y multi-tenancy

- [ ] Aislamiento por tenant (list, update, delete).
- [ ] RBAC deny-by-default.
- [ ] Superadmin vs tenant admin.

### Roles y permisos

- [ ] Permisos por módulo y acción.
- [ ] Guards en frontend.
- [ ] Validación en backend.

### Reportes

- [ ] Ventas, empleados, dashboard.

### Comprobantes

- [ ] Recibos de nómina.
- [ ] Recibos de venta.

### Frontend POS

- [ ] Carrito, descuentos, cupones, NCF.
- [ ] Acciones reales conectadas a endpoints.

### Frontend Nómina

- [ ] Resumen financiero.
- [ ] Selector de período.
- [ ] Tabla de empleados.
- [ ] Modal de detalle.
- [ ] Acciones de aprobación/pago.
- [ ] Historial.
- [ ] Estados claramente diferenciados.

### Frontend My Earnings

- [ ] Ganancias, comisiones, deducciones.
- [ ] Períodos y pagos.
- [ ] Comprobantes.
- [ ] Solo datos propios.

## Condiciones para declarar cada fase terminada

### Fase 1 — Validación fiscal
- ISR calculado según tabla DGII vigente.
- TSS/SFS validados contra valores oficiales.
- Regalía pascual calculada y pagada en diciembre.
- Vacaciones y prestaciones calculadas y registradas.

### Fase 2 — Comisiones y descuentos
- Comisión calculada sobre la base acordada.
- Redenciones no inflan comisión.
- Pagos parciales generan comisión proporcional (si se implementa).

### Fase 3 — Nómina avanzada
- Pago parcial registrado correctamente.
- Reverso de pago funciona.
- Auditoría de deducciones completa.
- Compensación mid-período prorrateada.

### Fase 4 — Funcionalidades adicionales
- Propina registrada y distribuida.
- Alquiler de silla funcional.
- Nomenclatura unificada.

### Fase 5 — Validación y calidad
- Karma ejecutándose en CI.
- Cobertura de pruebas ≥ 80% en módulos críticos.
- Validación fiscal contra fuentes oficiales documentada.

## Pruebas obligatorias por fase

### Pruebas unitarias
- Cálculo de ISR progresivo.
- Regalía, vacaciones, prestaciones.
- Comisión con descuentos, redenciones, pagos parciales.
- Pago parcial, reverso, auditoría.
- Propinas, alquiler de silla.

### Pruebas de integración
- Flujo completo de nómina con deducciones legales.
- Venta con descuento → comisión correcta.
- Venta con propina → nómina.

### Pruebas E2E
- Implementar si se decide (actualmente no disponibles).

## Notas

- Los datos actuales son de prueba y pueden perderse si es necesario, previa planificación y autorización.
- No asumir que es necesario borrar la base de datos.
- La primera fase de implementación debe ser la validación fiscal (Fase 1), ya que afecta los cálculos de nómina.
- Las decisiones de negocio (comisión sobre descuentos, pagos parciales, etc.) deben aprobarse antes de programar.
