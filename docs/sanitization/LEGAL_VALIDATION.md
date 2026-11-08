# LEGAL_VALIDATION.md — Validación normativa (República Dominicana)

## 1. ISR (Impuesto Sobre la Renta)

### Regla oficial
- **Fuente:** DGII — Guía de Retenciones del ISR.
- **Enlace:** https://dgii.gov.do/publicacionesOficiales/bibliotecaVirtual/contribuyentes/retencionesRetribucionesComplementarias/Documents/2-Guia-11-Retenciones%20del%20Impuesto%20Sobre%20la%20Renta.pdf
- **Escala anual 2026:**
  - Hasta RD$416,220.00 → Exento
  - RD$416,220.01 a RD$624,329.00 → 15% del excedente de RD$416,220.01
  - RD$624,329.01 a RD$867,123.00 → RD$31,216.00 + 20% del excedente de RD$624,329.01
  - Desde RD$867,123.01 → RD$79,776.00 + 25% del excedente de RD$867,123.01
- **Exención contributiva mensual:** RD$34,685.00 (duodécima parte de RD$416,220).
- **Base gravable:** El ISR se calcula sobre la renta neta, es decir, **después de deducir las cotizaciones de Seguridad Social (SFS + AFP del empleado)**. No se calcula directamente sobre el salario bruto.
- **Metodología:** salario neto mensual × 12 = salario neto anual; comparar con la escala; calcular retención mensual = retención anual / 12.

### Diseño de especificación para tablas fiscales versionadas (Ley 30-26)

A partir de 2027, la Ley 30-26 modifica la escala ISR:
- Mínimo exento: RD$480,000.00 (desde 2027).
- Nuevo tramo: 27% para rentas superiores.

**Especificación técnica propuesta:**

```
FiscalTable {
  fiscal_year: int          # Año fiscal (2026, 2027, ...)
  effective_date: date      # Fecha de vigencia
  exemption_annual: decimal # Mínimo exento anual
  exemption_monthly: decimal# Mínimo exento mensual (exemption_annual / 12)
  brackets: [
    { from: decimal, to: decimal, rate: decimal, base_amount: decimal },
    ...
  ]
  source: str              # Fuente oficial (DGII)
  version: int             # Versión de la tabla
}
```

**Comportamiento:**
- Al calcular ISR para un período, seleccionar la `FiscalTable` vigente según la fecha del período.
- Si no existe tabla para el año, usar la más reciente anterior.
- Las tablas deben ser inmutables una vez publicadas.
- Registrar qué tabla se usó en el cálculo (trazabilidad).

**Cambio 2027 (Ley 30-26):**
- Exención anual: RD$480,000.00 (vs RD$416,220.00 en 2026).
- Nuevo tramo: 27% para rentas superiores al tramo actual de 25%.
- La tabla 2026 no cambia; la 2027 se agrega como nueva versión.

### Implementación actual
- **Archivos:** `apps/employees_api/earnings_models.py` (PayrollConfiguration: `tax_rate`), `apps/employees_api/earnings_views.py` (config endpoint), `apps/employees_api/earnings_models.py` (`calculate_amounts`).
- **Función:** `calculate_amounts()` aplica `tax_amount = (gross * tax_rate / 100).quantize(0.01)`.

### Diferencias encontradas
- El sistema usa una **tasa plana configurable** (`tax_rate`), no la tabla progresiva por tramos de DGII.
- El ISR se calcula sobre `gross_amount` (salario base + comisiones + christmas_bonus), **sin deducir primero las cotizaciones de Seguridad Social**. La base gravable debe ser: salario bruto − SFS − AFP.
- No se valida la tasa contra valores oficiales.
- No hay versionado de tablas fiscales.

### Cambios técnicos necesarios
- Implementar la tabla progresiva de ISR en `calculate_amounts()` o en `PayrollCalculationService`.
- Calcular la base gravable como: `gross_amount - social_security_amount - health_insurance_amount`.
- Agregar modelo `FiscalTable` con versionado por año.
- Agregar método `calculate_isr(taxable_base, fiscal_year)` que aplique la escala DGII.

### Casos de prueba propuestos
- Salario mensual RD$34,685 → ISR = 0.
- Salario mensual RD$50,000 → base gravable = 50,000 − SFS − AFP; ISR = (base×12; tramo 15%).

### Estado: ❌ NO IMPLEMENTADO (tasa plana, no tabla progresiva; base gravable incorrecta; sin versionado)

---

## 2. TSS y SFS (Tesorería de la Seguridad Social)

### Regla oficial
- **Fuente:** TSS — Resolución 01-2025, vigente desde 01/02/2026.
- **Enlace:** https://tss.gob.do/preguntas-frecuentes
- **Tasas (empleado):**
  - SFS (Seguro Familiar de Salud): 3.04%
  - AFP (Seguro de Vejez, Discapacidad y Sobrevivencia): 2.87%
  - Total descuento empleado: 5.91%
- **Tasas (empleador):**
  - SFS: 7.09%
  - AFP: 7.10% (que **incluye** el Fondo de Solidaridad del 0.4%)
  - SRL (Riesgos Laborales): 1% cuota fija + 0.10-0.30% variable (según factor de riesgo)
  - INFOTEP: 1% sobre nómina
- **Topes de cotización (2026, vigentes desde 01/02/2026):**
  - SRL: RD$92,892.00 (4 SMN)
  - SFS: RD$232,230.00 (10 SMN)
  - AFP: RD$464,460.00 (20 SMN)
- **Salario mínimo nacional para topes:** RD$23,223.00
- **Nota sobre Fondo de Solidaridad:** El 0.4% del Fondo de Solidaridad está **incluido** dentro del aporte patronal AFP del 7.10%. No debe duplicarse.

### Implementación actual
- **Archivos:** `apps/employees_api/earnings_models.py` (PayrollConfiguration: `social_security_rate`, `health_insurance_rate`), `apps/employees_api/earnings_models.py` (`calculate_amounts`).
- **Función:** `calculate_amounts()` aplica `ss_amount = (gross * social_security_rate / 100)` y `hi_amount = (gross * health_insurance_rate / 100)`.

### Diferencias encontradas
- Las tasas son **configurables manualmente**, no validadas contra los valores oficiales (3.04% SFS, 2.87% AFP).
- No se aplican **topes de cotización** (SFS RD$232,230; AFP RD$464,460).
- No se distingue entre aportes del empleado (deducciones) y aportes del empleador (costo laboral).
- No se incluye SRL, INFOTEP ni fondo de solidaridad (aportes del empleador).
- **Ejemplo aritmético corregido:** Salario RD$50,000 → SFS empleado = 3.04% × 50,000 = RD$1,520.00; AFP empleado = 2.87% × 50,000 = RD$1,435.00. Total retenido empleado = RD$2,955.00. Neto después de aportes = RD$47,045.00.

### Cambios técnicos necesarios
- Agregar validación de tasas contra valores oficiales.
- Implementar topes de cotización en el cálculo.
- Separar deducciones del empleado (SFS 3.04%, AFP 2.87%) de aportes del empleador (SFS 7.09%, AFP 7.10% que incluye fondo de solidaridad 0.4%, SRL, INFOTEP).
- Agregar campos para aportes del empleador.

### Casos de prueba propuestos
- Salario RD$50,000 → SFS empleado = RD$1,520.00; AFP empleado = RD$1,435.00.
- Salario RD$300,000 → SFS = 3.04% × 232,230 = RD$7,060.00 (tope); AFP = 2.87% × 300,000 = RD$8,610.00.

### Estado: ⚠️ PARCIAL (tasas manuales, sin topes, sin separación empleado/empleador)

---

## 3. Regalía pascual

### Regla oficial
- **Fuente:** Código de Trabajo (Ley 16-92), Art. 219 y 220.
- **Enlace:** https://mt.gob.do/wp-content/uploads/2024/07/codigo_de_trabajo.pdf
- **Fórmula:** Duodécima parte del salario ordinario devengado en el año calendario.
- **Base:** Salario ordinario (salario base + comisiones regulares). Excluye horas extras, propinas, bonificaciones.
- **Pago:** A más tardar el 20 de diciembre de cada año.
- **Proporcionalidad (Art. 220):** El trabajador que no haya prestado servicios durante todo el año tiene derecho al salario de Navidad en proporción al tiempo trabajado durante el año. No existe un requisito general de 3 meses; la proporcionalidad se aplica según el tiempo trabajado.
- **Tope:** En ningún caso mayor a 5 salarios mínimos (en la práctica, la mayoría paga un mes completo).
- **Exención ISR (Art. 222):** El salario de Navidad no es susceptible de gravamen, embargo, cesión o venta, ni está sujeto al impuesto sobre la renta. Esta exención aplica aunque el monto exceda los 5 salarios mínimos.
- **Diferencia con criterio DGII:** La DGII ha publicado criterio interpretativo que limita la exención a la duodécima parte de los salarios anuales. El Art. 222 del Código de Trabajo establece la exención sin límite. **Esta diferencia está pendiente de interpretación profesional. No se resuelve por inferencia.**
- **No computable:** No se computa para preaviso, cesantía ni asistencia económica.

### Implementación actual
- **Archivos:** `apps/employees_api/earnings_models.py` (campo `christmas_bonus` en `PayrollPeriod`), `apps/employees_api/earnings_views.py` (expuesto en API), `apps/employees_api/payroll_services.py` (`apply_calculation_to_period` incluye en gross).
- **Función:** Campo `DecimalField` manual, incluido en `gross_amount`. Sin fórmula de cálculo.

### Diferencias encontradas
- El campo `christmas_bonus` existe pero es **manual** (se ingresa a mano).
- No hay fórmula de cálculo (duodécima parte del salario ordinario anual).
- No se genera automáticamente en diciembre.
- No se excluye del ISR (debería estar exenta según Art. 222, aunque DGII tiene criterio diferente).
- No se consideran fracciones de año (proporcional según Art. 220).

### Cambios técnicos necesarios
- Implementar cálculo automático: `regalia = (salario_ordinario_anual) / 12`.
- Generar automáticamente en diciembre para todos los empleados activos.
- Marcar como exenta de ISR (pendiente de interpretación profesional sobre el límite).
- Considerar proporcionalidad por tiempo trabajado (Art. 220).

### Casos de prueba propuestos
- Empleado con salario fijo RD$50,000/mes durante 12 meses → regalía = RD$50,000.
- Empleado que ingresó en abril (9 meses) → regalía = salario_ordinario_anual × 9/12.
- Empleado que ingresó en noviembre (2 meses) → regalía proporcional (fracción > 0).

### Estado: ❌ NO IMPLEMENTADO (campo manual, sin fórmula ni generación automática)

---

## 4. Vacaciones

### Regla oficial
- **Fuente:** Código de Trabajo (Ley 16-92), Art. 177, 179 y 180.
- **Enlace:** https://mt.gob.do/wp-content/uploads/2024/07/codigo_de_trabajo.pdf
- **Derecho:** 14 días laborables de vacaciones con disfrute de salario después de 1 año de servicio ininterrumpido. 18 días después de 5 años.
- **Fraccionamiento (Art. 177):** Las vacaciones pueden fraccionarse por acuerdo entre trabajador y empleador, respetando un período mínimo de una semana.
- **Proporcionalidad (Art. 179):** Trabajadores que sin culpa alguna no puedan tener oportunidad de prestar servicios ininterrumpidos durante un año tienen derecho a un período de vacaciones proporcional al tiempo trabajado, si éste es mayor de cinco meses.
- **Escala de proporcionalidad (Art. 180):**
  - Trabajadores con más de 5 meses de servicios → 6 días.
  - Trabajadores con más de 6 meses de servicios → 7 días.
- **Cálculo:** Si el salario es por labor rendida, se usa el promedio diario de los últimos 12 meses (o período menor que haya trabajado).
- **Compensación pecuniaria:** Si el trabajador deja la empresa sin haber disfrutado las vacaciones, recibe una compensación equivalente a los salarios del período vacacional.
- **No fraccionables:** Las vacaciones no pueden fraccionarse en períodos menores de una semana ni sustituirse por pagos adicionales.
- **Factor 23.83:** Salario diario = salario mensual / 23.83 (usado en prestaciones).

### Implementación actual
- **Archivos:** No existe en el código. No hay modelo, endpoint ni componente para vacaciones.

### Diferencias encontradas
- **Completamente ausente.** No hay modelo `Vacation`, ni endpoint, ni cálculo.

### Cambios técnicos necesarios
- Crear modelo `Vacation` con campos: employee, year, days, start_date, end_date, status, paid_amount.
- Crear endpoint para calcular y registrar vacaciones.
- Implementar cálculo: 14 días (o 18 después de 5 años) × salario diario.
- Implementar fraccionamiento por acuerdo (mínimo 1 semana).
- Implementar proporcionalidad (Art. 179-180).
- Agregar a la nómina como concepto independiente.

### Casos de prueba propuestos
- Empleado con 1 año de servicio → 14 días de vacaciones.
- Empleado con 6 años de servicio → 18 días de vacaciones.
- Empleado con salario por comisión → promedio diario de últimos 12 meses.
- Empleado con 7 meses de servicio → 7 días (proporcional, Art. 180).

### Estado: ❌ NO IMPLEMENTADO

---

## 5. Prestaciones laborales (preaviso y cesantía)

### Regla oficial
- **Fuente:** Código de Trabajo (Ley 16-92), Art. 76, 79, 80, 81, 82, 85.
- **Enlace:** https://mt.gob.do/wp-content/uploads/2024/07/codigo_de_trabajo.pdf
- **Preaviso (Art. 76):** El empleador que omite el preaviso debe pagar una indemnización equivalente al salario durante el período de preaviso:
  - 7 días de salario si tiene entre 3 y 6 meses de servicio.
  - 14 días si tiene entre 6 y 12 meses.
  - 28 días si tiene 1 año o más.
- **Cesantía (Art. 80):** El empleador que ejerza el desahucio debe pagar al trabajador un auxilio de cesantía:
  - **6 días** de salario ordinario si tiene entre 3 y 6 meses de trabajo continuo.
  - **13 días** de salario ordinario si tiene entre 6 y 12 meses.
  - **21 días por año** si tiene entre 1 y 5 años.
  - **23 días por año** si tiene **5 años o más** (desde los cinco años cumplidos).
  - Las fracciones de año se calculan proporcionalmente según el Art. 80 (fracción superior a 3 meses).
- **Base de cálculo (Art. 85):** El importe del auxilio de cesantía y del preaviso se calculará tomando como base el **promedio de los salarios devengados por el trabajador durante el último año o fracción de un año** que tenga de vigencia el contrato. Solo se tendrán en cuenta los salarios correspondientes a horas ordinarias.
- **Distinción de causas de terminación:**
  - **Desahucio (Art. 75):** Terminación sin causa justificada → preaviso + cesantía + vacaciones + regalía proporcional.
  - **Despido con causa:** Sin preaviso ni cesantía (faltas graves).
  - **Dimisión con causa justificada:** Derecho a todas las prestaciones como si fuera despido sin causa.
  - **Dimisión sin causa:** Solo vacaciones no disfrutadas + regalía proporcional.
  - **Mutuo acuerdo:** Lo pactado entre las partes.
- **Asistencia económica (Art. 82):** En caso de despido sin causa, el trabajador tiene derecho a una asistencia económica equivalente a los salarios que habría recibido desde la demanda hasta la sentencia definitiva, con un máximo de 6 meses. Esta es distinta de la cesantía.
- **Prestaciones por despido sin causa:** preaviso + cesantía + vacaciones no disfrutadas + regalía proporcional + participación en beneficios.
- **Plazo de pago:** 10 días después de la terminación del contrato. Retraso genera 1 día de salario adicional por día (Art. 86, sin tope).
- **Factor 23.83:** Salario diario = salario mensual / 23.83.
- **Exención ISR:** Preaviso y cesantía están exentos del ISR (Ley 30-26 de 2026 extendió esta exención a la asistencia económica del Art. 82).

### Implementación actual
- **Archivos:** No existe en el código. No hay modelo, endpoint ni cálculo para preaviso o cesantía.

### Diferencias encontradas
- **Completamente ausente.** No hay modelo `Prestacion`, ni endpoint, ni cálculo.

### Cambios técnicos necesarios
- Crear modelo `Prestacion` con campos: employee, termination_date, termination_type, preaviso_days, cesantia_days, vacation_days, regalia_proporcional, total.
- Crear endpoint para calcular y registrar prestaciones.
- Implementar fórmula de preaviso y cesantía según años de servicio y causa de terminación.
- Usar Art. 85 para la base de cálculo (promedio de salarios del último año).
- Integrar con nómina (pago final).

### Casos de prueba propuestos
- Empleado con 2 años de servicio, despido sin causa → preaviso 28 días + cesantía 21×2 = 42 días.
- Empleado con 6 meses, renuncia sin causa → solo vacaciones no disfrutadas + regalía proporcional.
- Empleado con 10 años, despido sin causa → preaviso 28 días + cesantía 23×10 = 230 días.
- Empleado con 4 meses, despido sin causa → preaviso 7 días + cesantía 6 días.
- Empleado con 5 años exactos → cesantía 23×5 = 115 días (desde los cinco años cumplidos).

### Estado: ❌ NO IMPLEMENTADO

---

## 6. INFOTEP

### Regla oficial
- **Fuente:** INFOTEP (Instituto Nacional de Formación Técnico Profesional).
- **Enlace:** https://www.infotep.gov.do
- **Composición:**
  - **Empleador:** 1% sobre la nómina total (salarios).
  - **Trabajador:** 0.5% deducible de las utilidades/bonificaciones anuales que reciben los trabajadores (participación en beneficios).
- **Distinción:** El 1% patronal se calcula sobre salarios; el 0.5% del trabajador se aplica solo sobre bonificaciones/utilidades, no sobre el salario ordinario.

### Implementación actual
- **Archivos:** No existe en el código. No hay campo, cálculo ni deducción para INFOTEP.

### Diferencias encontradas
- **Completamente ausente.** No hay modelo, endpoint ni cálculo para INFOTEP.

### Cambios técnicos necesarios
- Agregar campo `infotep_rate` a `PayrollConfiguration` (1% patronal).
- Agregar deducción automática de INFOTEP (1% sobre salario) como aporte del empleador.
- Agregar deducción del 0.5% sobre bonificaciones (participación en utilidades) del trabajador.
- Separar claramente: 1% patronal (salarios) vs 0.5% trabajador (bonificaciones).

### Casos de prueba propuestos
- Salario RD$50,000 → INFOTEP patronal = 1% × 50,000 = RD$500.
- Bonificación de RD$10,000 → INFOTEP trabajador = 0.5% × 10,000 = RD$50.

### Estado: ❌ NO IMPLEMENTADO

---

## 7. Participación en los beneficios (bonificación)

### Regla oficial
- **Fuente:** Código de Trabajo (Ley 16-92), Art. 223.
- **Fórmula:** 10% de las utilidades o beneficios netos de la empresa, distribuidos proporcionalmente entre los trabajadores.
- **Tope:** 45 días de salario ordinario para empleados con **menos de 3 años** de servicio; **60 días** para empleados con **3 años o más**.
- **Exenciones:** Empresas industriales, forestales y mineras durante sus primeros 3 años de operación; empresas de zonas francas; empresas agrícolas con capital inferior a RD$1,000,000.
- **Pago:** Entre 90 y 120 días después del cierre del ejercicio económico.

### Implementación actual
- **Archivos:** No existe en el código. No hay modelo, endpoint ni cálculo.

### Diferencias encontradas
- **Completamente ausente.**

### Cambios técnicos necesarios
- Crear modelo `ParticipacionBeneficios` con campos: tenant, fiscal_year, total_utilities, percentage, employee, amount, days_cap.
- Implementar cálculo: 10% de utilidades × proporción del salario del empleado / total salarios.
- Aplicar tope de 45/60 días según antigüedad.
- Integrar con nómina (bonificación).

### Casos de prueba propuestos
- Empresa con utilidades de RD$1,000,000 → 10% = RD$100,000 distribuidos proporcionalmente.
- Empleado con 2 años de servicio → tope de 45 días de salario.
- Empleado con 3 años de servicio → tope de 60 días de salario.

### Estado: ❌ NO IMPLEMENTADO

---

## 8. Resumen comparativo actualizado

| Concepto | Regla oficial | Implementado | Estado |
|---|---|---|---|
| ISR (tabla progresiva) | DGII escala 0/15/20/25% sobre base gravable | Tasa plana sobre gross (sin deducir SS) | ❌ Parcial |
| TSS/SFS (tasas y topes) | 3.04%/2.87%, topes RD$232,230/RD$464,460 | Tasas manuales, sin topes | ⚠️ Parcial |
| Regalía pascual | Duodécima parte salario ordinario anual (Art. 219-220) | Campo manual, sin fórmula | ❌ Ausente |
| Vacaciones | 14/18 días laborables (Art. 177, 179-180) | No existe | ❌ Ausente |
| Prestaciones (preaviso/cesantía) | 7/14/28 días preaviso; 6/13/21/23 días cesantía (Art. 76/80) | No existe | ❌ Ausente |
| INFOTEP | 1% patronal (salarios) + 0.5% trabajador (bonificaciones) | No existe | ❌ Ausente |
| Participación en beneficios | 10% de utilidades, tope 45/60 días (Art. 223) | No existe | ❌ Ausente |
| ITBIS | 18% sobre bienes/servicios | ✅ Implementado | ✅ Correcto |
| NCF | Comprobantes fiscales RD | ✅ Implementado | ✅ Correcto |
| Regalía exención ISR | Art. 222 — exenta del ISR (diferencia con criterio DGII) | No implementado | ⚠️ Pendiente de interpretación |

## Fuentes oficiales

1. **DGII — Impuesto Sobre la Renta:** https://dgii.gov.do/cicloContribuyente/obligacionesTributarias/principalesImpuestos/Paginas/impuestoSobreRenta.aspx
2. **DGII — Retenciones del ISR:** https://dgii.gov.do/publicacionesOficiales/bibliotecaVirtual/contribuyentes/retencionesRetribucionesComplementarias/Documents/2-Guia-11-Retenciones%20del%20Impuesto%20Sobre%20la%20Renta.pdf
3. **DGII — Tabla de Retenciones:** https://dgii.gov.do/publicacionesOficiales/tablaRetenciones/Paginas/default.aspx
4. **DGII — Salario de Navidad y exención fiscal:** http://dgii.gov.do/legislacion/editorialJuridico/Paginas/salario-navidad-y-exencion-fiscal.aspx
5. **TSS — Preguntas frecuentes (topes y tasas):** https://tss.gob.do/preguntas-frecuentes
6. **Presidencia RD — Nuevos topes TSS 2026:** https://presidencia.gob.do/noticias/tesoreria-de-la-seguridad-social-informa-nuevos-topes-de-cotizacion-para-el-regimen
7. **Código de Trabajo (Ley 16-92):** https://mt.gob.do/wp-content/uploads/2024/07/codigo_de_trabajo.pdf
8. **Arthur & Castillo — Derecho Laboral RD:** https://aclaw.com/es/guia-legal-republica-dominicana/derecho-laboral
9. **impucalculo.com — Prestaciones laborales:** https://impucalculo.com/blog/prestaciones-laborales-guia.html
10. **Alegra — Bonificaciones laborales RD:** https://blog.alegra.com/republica-dominicana/que-son-las-bonificaciones-laborales
11. **INFOTEP:** https://www.infotep.gov.do
12. **El Caribe — Regalía pascual:** https://www.instagram.com/p/DQ7CRm6juWg

## Distinción: normativa verificada vs. pendiente de validación profesional

| Concepto | Normativa verificada | Pendiente de validación profesional |
|---|---|---|
| ISR tabla progresiva | ✅ Verificado en DGII | Implementación técnica pendiente |
| TSS/SFS tasas y topes | ✅ Verificado en TSS | Implementación técnica pendiente |
| Regalía pascual fórmula | ✅ Verificado en Código de Trabajo (art. 219-220) | Implementación técnica pendiente |
| Regalía exención ISR (Art. 222 vs criterio DGII) | ✅ Verificado en ambas fuentes | **Pendiente de interpretación profesional** |
| Vacaciones | ✅ Verificado en Código de Trabajo (art. 177, 179-180) | Implementación técnica pendiente |
| Prestaciones (preaviso/cesantía) | ✅ Verificado en Código de Trabajo (art. 76-82, 85) | Implementación técnica pendiente |
| INFOTEP | ✅ Verificado en fuentes oficiales | Implementación técnica pendiente |
| Participación en beneficios | ✅ Verificado en Código de Trabajo (art. 223) | Implementación técnica pendiente |
| ITBIS | ✅ Implementado y verificado | — |
| NCF | ✅ Implementado y verificado | — |

**Conclusión:** La normativa está verificada en fuentes oficiales. La implementación técnica de ISR progresivo, TSS/SFS con topes, regalía pascual, vacaciones, prestaciones, INFOTEP y participación en beneficios está ausente o parcial. Se requiere validación profesional (contador/abogado laboral) para confirmar la aplicación correcta de las fórmulas en el contexto del negocio. La diferencia entre el Art. 222 del Código de Trabajo y el criterio de la DGII sobre la exención del ISR de la regalía pascual está pendiente de interpretación profesional.
