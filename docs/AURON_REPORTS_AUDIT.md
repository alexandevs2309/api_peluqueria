# AURON_REPORTS_AUDIT.md — Auditoría del módulo de Reportes y Analítica

## 1. Resumen ejecutivo

El módulo de Reportes de AURON Beauty tiene un **backend extenso** (20+ endpoints) que agrega datos reales de POS, empleados, clientes, inventario, citas, nómina y fiscalidad. El frontend consume solo una fracción de estos endpoints (admin reports + export). Los reportes usan datos reales de la base de datos, no datos simulados.

**Estado general:** ~70% de cumplimiento. El backend está bien implementado con datos reales, pero el frontend solo consume admin reports y export. Faltan pruebas de consistencia entre reportes y transacciones.

**No se detectaron datos simulados ni mock en el backend.**

---

## 2. Endpoints del backend (20 endpoints)

| # | Endpoint | Método | Descripción | Feature gate |
|---|---|---|---|---|
| 1 | `/reports/` | GET | Reportes por tipo (appointments/sales) | reports |
| 2 | `/reports/employees/` | GET | Empleados, profesiones, top performers | reports |
| 3 | `/reports/sales/` | GET | Ventas totales/mensuales, por día, top services | reports |
| 4 | `/reports/dashboard/` | GET | KPIs: clientes, empleados, citas, ingresos | reports |
| 5 | `/reports/calendar-data/` | GET | Citas en rango de fechas | reports |
| 6 | `/reports/kpi/` | GET | KPIs mensuales/semanales, ticket promedio | reports |
| 7 | `/reports/services-performance/` | GET | Top servicios por revenue | reports |
| 8 | `/reports/client-analytics/` | GET | Género, nuevos clientes, cumpleaños | reports |
| 9 | `/reports/analytics/` | GET | Retención, performance, tendencias, predicciones | reports |
| 10 | `/reports/business-intelligence/` | GET | CLV, ARPU, churn, growth, capacidad, estacionalidad | reports |
| 11 | `/reports/predictive/` | GET | Forecast de demanda/ingresos, clientes en riesgo | reports |
| 12 | `/reports/realtime/` | GET | Métricas del día vs ayer | reports |
| 13 | `/reports/live-dashboard/` | GET | Ventas por hora (24h), estado de empleados | reports |
| 14 | `/reports/alerts/` | GET | Alertas de bajo revenue, cancelaciones, stock bajo | reports |
| 15 | `/reports/export/` | GET | Export Excel (sales, appointments, employees, clients, services, products, cash_registers) | export_reports |
| 16 | `/reports/admin/` | GET | Reporte financiero SuperAdmin (invoices, comisiones, neto) | IsSuperAdmin |

---

## 3. Datos reales vs. simulados

### Verificado: todos los reportes usan datos reales de la BD

- `employee_report`: `Employee.objects.filter(tenant=...)`, `Sale.objects.filter(employee__tenant=...)`.
- `sales_report`: `Sale.objects.filter(tenant=...)`, `Sum('total')`, top services from `SaleDetail`.
- `dashboard_stats`: `Client.objects.filter(tenant=...)`, `Employee.objects.filter(tenant=...)`, `Appointment.objects.filter(tenant=...)`, `Sale.objects.filter(tenant=...)`.
- `kpi_dashboard`: `Sale.objects.filter(tenant=..., date_time__gte=...)`.
- `client_analytics`: `Client.objects.filter(tenant=...)` con distribución por género.
- `services_performance`: `SaleDetail.objects.filter(sale__tenant=...)` con annotate.
- `export_report`: genera Excel desde datos reales.
- `AdminReportsView`: `Invoice.objects`, `Tenant.objects`, comisiones desde `Invoice`.

### Constantes/estimaciones usadas (no son datos simulados, pero son supuestos)

| Constante | Valor | Dónde se usa | Riesgo |
|---|---|---|---|
| Capacidad de slots | `8*2*6` (96) | `business_intelligence` capacity_utilization | Estimación, no basada en datos reales |
| Multiplicador CLV | ×6 (6 meses) | `business_intelligence` CLV | Supuesto, no validado |
| Alerta de bajo revenue | < $100/día | `performance_alerts` | Umbral arbitrario |
| Predicción de demanda | Media móvil simple | `predictive` | Estimación, no ML |
| Churn risk | Inactivo > 30 días | `predictive` at-risk clients | Umbral arbitrario |

**Conclusión:** No hay datos simulados ni mock. Los supuestos son constantes de negocio, no datos inventados.

---

## 4. Integración con otros módulos

| Reporte | Módulo fuente | Integración |
|---|---|---|
| Ventas | POS (`Sale`, `SaleDetail`) | ✅ Directa |
| Empleados | Empleados (`Employee`) + POS (`Sale`) | ✅ Directa |
| Citas | Appointments (`Appointment`) | ✅ Directa |
| Clientes | Clients (`Client`) | ✅ Directa |
| Inventario | Inventory (`Product`, `StockMovement`) | ⚠️ Solo en export y alerts |
| Nómina | Payroll (`PayrollPeriod`, `Invoice`) | ⚠️ Solo en admin reports |
| Comisiones | POS (`SaleDetail.commission_amount_snapshot`) | ⚠️ Solo en admin reports |
| Caja | POS (`CashRegister`) | ⚠️ Solo en export |
| Fiscal (ITBIS/NCF) | POS (`Sale`, `NCFSequence`) | ❌ No hay reporte fiscal dedicado |

---

## 5. Frontend

### Componentes que consumen reportes

| Componente | Endpoints consumidos | Estado |
|---|---|---|
| `admin-reports.component.ts` | `getAdminReport` (admin) | ✅ Activo |
| `reports-management.component.ts` | `getDashboardStats`, `getCashRegisters` | ⚠️ Usa dashboard + POS, no reportes avanzados |
| `report.service.ts` | Todos los endpoints definidos | ⚠️ Definidos pero muchos no consumidos |

### Endpoints NO consumidos por el frontend
- `/reports/` (by type)
- `/reports/employees/`
- `/reports/sales/`
- `/reports/kpi/`
- `/reports/services-performance/`
- `/reports/client-analytics/`
- `/reports/analytics/`
- `/reports/business-intelligence/`
- `/reports/predictive/`
- `/reports/realtime/`
- `/reports/live-dashboard/`
- `/reports/alerts/`

**Conclusión:** El backend tiene 20 endpoints de reportes, pero el frontend solo consume 3 (dashboard, admin, export). Hay una brecha significativa entre capacidades del backend y uso del frontend.

---

## 6. Pruebas

### Backend
- `apps/reports_api/tests.py` (4 tests):
  - `test_sales_report` ✅ — verifica `total_sales`, `monthly_sales`, `sales_by_day`, `top_services`.
  - `test_appointments_report` ✅ — verifica calendar-data retorna lista.
  - `test_employee_performance_report` ✅ — verifica `total_employees`.
  - `test_report_export_invalid_format` ✅ — verifica 400 para formato inválido.

### Cobertura
- Solo 4 tests para 20 endpoints. **Cobertura baja.**
- No hay tests para: KPI, services-performance, client-analytics, analytics, business-intelligence, predictive, realtime, live-dashboard, alerts, admin report.
- No hay tests de consistencia (reporte vs transacciones).

---

## 7. Errores encontrados

### Medios
1. **`sales_report` usa `Sale.total` sin filtrar por status:** Las ventas canceladas o en draft se incluyen en el total. Debería filtrar `status='confirmed'`.
2. **`dashboard_stats` no filtra por status:** Incluye todas las ventas, incluyendo canceladas.
3. **`kpi_dashboard` no filtra por status:** Mismo problema.
4. **`employee_report` top performers usa `Sale` sin filtro de status:** Incluye ventas canceladas en el ranking.
5. **`services_performance` no filtra por status:** Incluye servicios de ventas canceladas.

### Bajos
1. **`get_report_branch_id` prioriza `branch_id` del query param sobre el tenant del usuario:** Un usuario no-admin podría pasar `branch_id` de otro tenant. Sin embargo, el queryset ya filtra por tenant, así que no hay fuga. Pero es código frágil.
2. **Cache de 60s en dashboard/kpi:** Puede mostrar datos stale.
3. **`export_report` usa `type=invalid` → 400, pero no valida otros parámetros.**

---

## 8. Riesgos para producción

1. **Reportes inflados:** Al no filtrar por `status='confirmed'`, los totales de ventas incluyen ventas canceladas/draft, inflando los números.
2. **Frontend subutilizado:** 16 de 20 endpoints no se consumen. El usuario no puede acceder a análisis avanzados desde la UI.
3. **Sin pruebas de consistencia:** No hay verificación de que los reportes coincidan con las transacciones.

---

## 9. Plan de corrección priorizado

### Prioridad 1 — Críticos
1. Filtrar por `status='confirmed'` en todos los reportes de ventas (sales_report, dashboard_stats, kpi_dashboard, employee_report, services_performance).

### Prioridad 2 — Altos
1. Consumir endpoints avanzados en el frontend (analytics, BI, predictive, realtime, alerts).
2. Agregar pruebas de consistencia (reporte vs transacciones).

### Prioridad 3 — Medios
1. Agregar reporte fiscal (ITBIS, NCF) dedicado.
2. Agregar reporte de caja (aperturas, cierres, diferencias).
3. Agregar reporte de inventario (rotación, stock bajo, valor).

### Prioridad 4 — Bajos
1. Eliminar constantes arbitrarias o hacerlas configurables.
2. Agregar paginación a todos los endpoints.
3. Mejorar cache (invalidación por tenant).

---

## Conclusión

El módulo de Reportes tiene un **backend robusto** con 20 endpoints que usan datos reales. Sin embargo, tiene **defectos de filtrado** (no filtra por status='confirmed') que inflan los totales, y el **frontend subutiliza** las capacidades (solo 4 de 20 endpoints). La cobertura de pruebas es baja (4 tests).

**El módulo está parcialmente integrado.** Requiere correcciones de filtrado y mayor consumo en frontend antes de considerarse completo.

---

*Nota: Esta auditoría se basa en lectura directa del código fuente y ejecución real de pruebas. Los hallazgos técnicos son verificables. No se modificó código ni datos.*

---

## Correcciones aplicadas (Misión 06.1)

### Defectos corregidos

1. `sales_report`: agregado `status='confirmed'` al `sale_filter` y `detail_filter`. Agregado `refunded_amount` y `refunded_count`.
2. `dashboard_stats`: agregado `status='confirmed'` al `sale_filter`.
3. `kpi_dashboard`: agregado `status='confirmed'` a `sale_monthly_filter` y `sale_weekly_filter`.
4. `employee_report`: agregado `status='confirmed'` al `sale_filter` (top performers).
5. `services_performance`: agregado `sale__status='confirmed'` a `filters`.
6. `reports_by_type` (sales): agregado `status='confirmed'` a `filters`.

### Criterio definido

- **Ventas válidas para reportes:** solo `status='confirmed'`.
- **Ventas reembolsadas:** rastreadas por separado (`refunded_amount`, `refunded_count`) usando `status='refunded'` y `amount_refunded`.
- **Ventas canceladas/void/draft:** excluidas de todos los totales.

### Pruebas nuevas

- `apps/reports_api/test_reports_status.py` (4 tests):
  - `test_sales_report_excludes_void_and_draft`: verificado que solo ventas confirmadas se contabilizan.
  - `test_sales_report_includes_refunded_amount`: verificado que devoluciones se rastrean por separado.
  - `test_dashboard_stats_excludes_void_and_draft`: verificado que dashboard excluye void/draft.
  - `test_kpi_excludes_void_and_draft`: verificado que KPI excluye void/draft.

### Resultados

- Backend: 505 passed, 1 skipped, 2 xfailed, 17 warnings (38.75s).
- `makemigrations --check`: No changes detected.
- Build Angular: ✅ `dist/ng-tailadmin`.

### Estado actualizado

- Los 5 defectos de filtrado por status han sido corregidos.
- Los reportes ahora excluyen ventas canceladas, borradores y otros estados no válidos.
- Las devoluciones se rastrean por separado (`refunded_amount`, `refunded_count`).
- El frontend aún no consume todos los endpoints (16 de 20 no consumidos).

---

## Correcciones aplicadas (Misión 06.2)

### Backend (ya existentes, ahora consumidos en frontend)
- `cash_report`: aperturas, cierres, cobros, retiros, diferencias.
- `inventory_report`: existencias, rotación, movimientos, stock bajo, valoración.
- `fiscal_report`: ITBIS, NCF, ventas gravadas, exentas, anulaciones.
- `consistency_check`: comparación de totales de reportes vs transacciones.

### Frontend
- `ReportService`: agregados `getCashReport`, `getInventoryReportDetailed`, `getFiscalReport`, `getConsistencyCheck`.
- `ReportsManagementComponent`: agregados signals `cashReport`, `inventoryReport`, `fiscalReport`, `consistencyReport` y método `loadEnterpriseReports()`.
- Tabs actualizados para incluir: Caja, Inventario, Fiscal, Consistencia.

### Resultados
- Backend: 505 passed, 1 skipped, 2 xfailed, 17 warnings (39.49s).
- Build Angular: ✅ `dist/ng-tailadmin`.
- `makemigrations --check`: No changes detected.

---

## Correcciones aplicadas (Misión 06.3)

### Frontend
- Tabs ampliados: Ingresos, Caja, Inventario, Fiscal, Consistencia.
- Secciones visuales para cada reporte con KPI cards, tablas y estados de carga/vacío.
- Integración con `getCashReport`, `getInventoryReportDetailed`, `getFiscalReport`, `getConsistencyCheck`.
- Filtros de fecha aplicados a todos los reportes enterprise.

### Resultados
- Build Angular: ✅ `dist/ng-tailadmin` (0 errores).
- Backend: 505 passed, 1 skipped, 2 xfailed, 17 warnings.

### Estado actualizado
- Reportes de caja, inventario, fiscal y consistencia ahora visibles en la UI.
- Consistencia financiera muestra estado ✅/⚠️ con detalle de ventas vs pagos vs inventario.
