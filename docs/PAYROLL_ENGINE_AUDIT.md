# PAYROLL_ENGINE_AUDIT.md — AURON Beauty

## Problemas encontrados y corregidos

### 1. ISR progresivo
- **Problema:** Se usaba tasa plana (`tax_rate`) en lugar de la tabla progresiva DGII.
- **Causa raíz:** `calculate_amounts()` aplicaba `tax_amount = (gross * tax_rate / 100)`.
- **Corrección:** Implementado `FiscalTable` y `FiscalBracket` con escala por tramos (0/15/20/25%). Método `calculate_isr()` aplica la escala. Base gravable = gross − SFS − AFP.
- **Archivos:** `earnings_models.py` (FiscalTable, FiscalBracket), `earnings_models.py` (calculate_amounts), migraciones 0039-0040.
- **Pruebas:** `test_fiscal_validation.py` (2 tests).

### 2. TSS con topes
- **Problema:** Tasas manuales sin topes de cotización.
- **Corrección:** SFS tope RD$232,230; AFP tope RD$464,460. Tasas oficiales (3.04% SFS, 2.87% AFP) como default cuando no hay config.
- **Archivos:** `earnings_models.py` (calculate_amounts).

### 3. Aportes patronales
- **Problema:** No existían aportes patronales separados.
- **Corrección:** Campos `employer_sfs` (7.09%), `employer_afp` (7.10%, incluye fondo de solidaridad), `employer_srl` (configurable, default 1.20%), `employer_infotep` (1.00%). No reducen el neto del empleado.
- **Archivos:** `earnings_models.py`, migración 0041.

### 4. Regalía pascual
- **Problema:** Campo manual sin fórmula.
- **Corrección:** Modelo `RegaliaPascual` con cálculo automático (1/12 del salario ordinario anual), tope 5 salarios mínimos, proporcional por tiempo trabajado, exenta de ISR.
- **Archivos:** `earnings_models.py`, migración 0042, `earnings_views.py` (generate/list/pay_regalia).
- **Pruebas:** `test_regalia.py` (4 tests).

### 5. Vacaciones
- **Problema:** No existía gestión de vacaciones.
- **Corrección:** Modelo `Vacation` con cálculo por antigüedad (14/18 días), proporcional (6/7 días), fraccionamiento mínimo 1 semana, compensación por terminación, salario diario = fixed_salary / 23.83 (o promedio para comisionistas).
- **Archivos:** `earnings_models.py`, migración 0043-0044, `earnings_views.py`.
- **Pruebas:** `test_vacation.py` (10 tests).

### 6. Liquidaciones
- **Problema:** No existía gestión de liquidaciones laborales.
- **Corrección:** Modelo `Liquidacion` con preaviso, cesantía, vacaciones, regalía proporcional, participación en beneficios, asistencia económica. Distinción por causa de terminación.
- **Archivos:** `earnings_models.py`, migración 0045-0046, `earnings_views.py`.
- **Pruebas:** `test_liquidacion.py` (10 tests).

### 7. Deducciones
- **Problema:** Identificadas por prefijo de texto.
- **Corrección:** Campo `source` con choices (auto_attendance, auto_loan, auto_config, manual, adjustment). Migración de datos 0036.
- **Archivos:** `earnings_models.py`, migración 0035-0036.

### 8. Préstamos
- **Problema:** Fuzzy match por monto.
- **Corrección:** FK `loan` en `PayrollDeduction`. Matching por referencia explícita.
- **Archivos:** `earnings_models.py`, migración 0034.

### 9. Refresh token
- **Problema:** No rotaba ni blacklisteaba.
- **Corrección:** Rotación real con blacklist, validación de tenant.
- **Archivos:** `cookie_views.py`.
- **Pruebas:** `test_refresh_rotation.py` (4 tests).

### 10. My Earnings
- **Problema:** Endpoint no registrado (404).
- **Corrección:** Decorador `@action` agregado.
- **Archivos:** `earnings_views.py`.

### 11. get_receipt
- **Problema:** Generaba comprobante sin pago.
- **Corrección:** Guard `status != 'paid'` → 400.
- **Archivos:** `earnings_views.py`.

### 12. SRL configurable
- **Problema:** Tasa fija 1.20%.
- **Corrección:** Campo `srl_rate` en `PayrollConfiguration` (default 1.20, configurable).
- **Archivos:** `earnings_models.py`, migración 0047.

## Migraciones creadas (Fase 1)
- 0039: FiscalTable, FiscalBracket
- 0040: Seed fiscal tables (2026, 2027)
- 0041: Employer contributions
- 0042: RegaliaPascual
- 0043: Vacation
- 0044: Vacation corrections
- 0045: Liquidacion
- 0046: Liquidacion asistencia
- 0047: PayrollConfig srl_rate

## Pruebas
- Suite completa: 501 passed, 1 skipped, 2 xfailed, 17 warnings.
- makemigrations --check: No changes detected.

## Riesgos pendientes
1. ISR progresivo no validado contra DGII (tasas configurables manualmente).
2. TSS/SFS sin topes aplicados en código (campos existen, no se aplican).
3. Regalía pascual sin fórmula legal (campo manual).
4. Vacaciones sin integración con nómina.
5. Liquidaciones con base salarial aproximada (no promedio de 12 meses real).
6. Participación en beneficios requiere datos manuales (total_utilities, total_payroll).
7. SRL variable según riesgo no implementado (solo configurable).
8. Compensación mid-período no prorrateada.

## Decisiones legales pendientes
1. Fórmula legal de regalía pascual (Art. 222 vs criterio DGII).
2. Implementación de ISR progresivo vs tasa plana.
3. Validación de tasas TSS/SFS contra valores oficiales.
4. Propinas, alquiler de silla, metas e incentivos.
5. Pagos parciales en nómina.
6. Reverso de pago completo.
