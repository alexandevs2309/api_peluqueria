# CORRECTION_ROADMAP.md — AURON Beauty

## Fase 1 — Validación fiscal dominicana (Prioridad: Alta)

**Objetivo:** Validar y corregir los cálculos fiscales y laborales contra la normativa dominicana.

**Problemas a resolver:**
- ISR calculado con tasa plana, no tabla progresiva DGII.
- Tasas TSS/SFS manuales, no validadas contra valores oficiales.
- Regalía pascual no implementada.
- Vacaciones y prestaciones no implementadas.

**Repositorios:** `api_peluqueria` (backend).

**Archivos involucrados:**
- `apps/employees_api/earnings_models.py` (PayrollConfiguration, PayrollPeriod)
- `apps/employees_api/earnings_views.py` (config endpoint)
- `apps/employees_api/payroll_services.py`

**Dependencias:** Ninguna (independiente).

**Cambios de backend:**
- Implementar tabla progresiva de ISR (DGII) o validar tasa contra valores oficiales.
- Validar tasas TSS/SFS contra valores publicados por TSS.
- Implementar regalía pascual (art. 223 Código de Trabajo).
- Implementar vacaciones (art. 183) y prestaciones (art. 80).

**Cambios de frontend:**
- Agregar campos para regalía, vacaciones, prestaciones en nómina.
- Mostrar desglose fiscal en recibos.

**Migraciones necesarias:** Sí (nuevos campos en PayrollPeriod/PayrollConfiguration).

**Riesgos:** Alto — cambios en cálculos financieros; requiere validación legal.

**Pruebas unitarias:** Cálculo de ISR progresivo, regalía, vacaciones, prestaciones.

**Pruebas de integración:** Flujo completo de nómina con deducciones legales.

**Pruebas E2E:** No disponibles.

**Criterios de aceptación:**
- ISR calculado según tabla DGII vigente.
- TSS/SFS validados contra valores oficiales.
- Regalía pascual calculada y pagada en diciembre.
- Vacaciones y prestaciones calculadas y registradas.

## Fase 2 — Comisiones y descuentos (Prioridad: Media)

**Objetivo:** Resolver las inconsistencias en el cálculo de comisiones.

**Problemas a resolver:**
- Comisión sobre descuentos globales (decisión de negocio).
- Redenciones de fidelidad impacto en comisión.
- Comisión sobre pagos parciales.

**Repositorios:** `api_peluqueria` (backend), `auron-tailadmin` (frontend).

**Archivos involucrados:**
- `apps/pos_api/services.py` (SaleCommissionService)
- `apps/pos_api/views.py` (SaleViewSet.perform_create, refund)
- `apps/pos_api/models.py` (Sale, SaleDetail)

**Dependencias:** Fase 1 (no depende directamente).

**Cambios de backend:**
- Decidir si comisión se calcula sobre precio bruto o neto de descuento global.
- Aplicar redenciones de fidelidad a la base de comisión.
- Soportar comisión sobre pagos parciales (si se decide).

**Cambios de frontend:**
- Mostrar base de comisión en el detalle de venta.

**Migraciones necesarias:** No.

**Riesgos:** Medio — cambios en cálculos de comisión.

**Pruebas unitarias:** Comisión con descuentos, redenciones, pagos parciales.

**Pruebas de integración:** Venta con descuento → comisión correcta.

**Pruebas E2E:** No disponibles.

**Criterios de aceptación:**
- Comisión calculada sobre la base acordada.
- Redenciones no inflan comisión.
- Pagos parciales generan comisión proporcional (si se implementa).

## Fase 3 — Nómina avanzada (Prioridad: Media)

**Objetivo:** Completar funcionalidades de nómina no implementadas.

**Problemas a resolver:**
- Pagos parciales en nómina.
- Reverso de pago completo.
- Auditoría de deducciones (modified_by/modified_at).
- Compensación mid-período (prorrateo).
- Christmas bonus fórmula legal.

**Repositorios:** `api_peluqueria` (backend), `auron-tailadmin` (frontend).

**Archivos involucrados:**
- `apps/employees_api/earnings_models.py` (PayrollPeriod, PayrollDeduction)
- `apps/employees_api/earnings_views.py` (register_payment, get_receipt)
- `apps/employees_api/payroll_services.py`

**Dependencias:** Fase 1 (regalía/vacaciones pueden integrarse aquí).

**Cambios de backend:**
- Soportar pagos parciales (nuevo campo `paid_amount` en PayrollPeriod).
- Implementar reverso de pago (nuevo endpoint `reverse_payment`).
- Agregar campos de auditoría a PayrollDeduction.
- Implementar prorrateo de compensación mid-período.

**Cambios de frontend:**
- Mostrar pagos parciales y saldos pendientes.
- Acción de reverso de pago.

**Migraciones necesarias:** Sí (nuevos campos).

**Riesgos:** Alto — cambios en flujo de pagos.

**Pruebas unitarias:** Pago parcial, reverso, auditoría.

**Pruebas de integración:** Flujo completo con pago parcial y reverso.

**Pruebas E2E:** No disponibles.

**Criterios de aceptación:**
- Pago parcial registrado correctamente.
- Reverso de pago funciona.
- Auditoría de deducciones completa.
- Compensación mid-período prorrateada.

## Fase 4 — Funcionalidades adicionales (Prioridad: Baja)

**Objetivo:** Implementar funcionalidades no existentes.

**Problemas a resolver:**
- Propinas.
- Alquiler de silla / prestación independiente.
- Metas e incentivos.
- Nomenclatura "Mis Ganancias" vs "Nómina".

**Repositorios:** `api_peluqueria` (backend), `auron-tailadmin` (frontend).

**Archivos involucrados:**
- `apps/pos_api/models.py` (Sale — agregar campo tip)
- `apps/pos_api/views.py` (perform_create)
- `apps/employees_api/earnings_models.py` (nuevos campos)
- `apps/employees_api/earnings_views.py`

**Dependencias:** Fase 2 (comisiones).

**Cambios de backend:**
- Agregar campo `tip` a Sale.
- Implementar distribución de propinas (por empleado o por servicio).
- Implementar alquiler de silla (nuevo tipo de compensación).

**Cambios de frontend:**
- Agregar campo de propina en POS.
- Mostrar propinas en nómina.
- Unificar nomenclatura.

**Migraciones necesarias:** Sí.

**Riesgos:** Medio — nuevas funcionalidades, no afectan existentes.

**Pruebas unitarias:** Propinas, alquiler de silla.

**Pruebas de integración:** Venta con propina → nómina.

**Pruebas E2E:** No disponibles.

**Criterios de aceptación:**
- Propina registrada y distribuida.
- Alquiler de silla funcional.
- Nomenclatura unificada.

## Fase 5 — Validación y calidad (Prioridad: Continua)

**Objetivo:** Mejorar la cobertura de pruebas y la calidad del código.

**Problemas a resolver:**
- Ejecutar Karma en CI (sin Chrome en entorno actual).
- Agregar pruebas E2E (si se decide implementar).
- Validar fiscalidad dominicana con fuentes oficiales.

**Repositorios:** `api_peluqueria` (backend), `auron-tailadmin` (frontend).

**Archivos involucrados:** Todos los módulos auditados.

**Dependencias:** Todas las fases anteriores.

**Cambios de backend:**
- Ninguno (solo pruebas).

**Cambios de frontend:**
- Ninguno (solo pruebas).

**Migraciones necesarias:** No.

**Riesgos:** Bajo.

**Pruebas unitarias:** Agregar pruebas para funcionalidades sin cobertura.

**Pruebas de integración:** Agregar pruebas de flujo completo.

**Pruebas E2E:** Implementar si se decide.

**Criterios de aceptación:**
- Karma ejecutándose en CI.
- Cobertura de pruebas ≥ 80% en módulos críticos.
- Validación fiscal contra fuentes oficiales documentada.
