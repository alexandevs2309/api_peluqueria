# Migration Plan — 10 Sprints

> Principio: un cambio visible por sprint. No mezclar fases.

---

## Sprint 1: Design tokens + Layout shell

**Duración:** 5-7 días
**Impacto:** Global (layout shell, colores, spacing)

### Tasks
- [x] Definir `tokens.css` con variables de color, spacing, typography, shadows
- [x] Integrar Tailwind 4 `@theme` con tokens
- [x] Limpiar `_platform.scss`: 442 lineas `!important` → tokens
- [x] Refactor layout shell: sidebar, topbar, content wrapper
- [x] Sistema de layout usando CSS grid (no flex layout de PrimeNG)
- [x] Sidebar con agrupación UX optimizada (4 secciones, no 8)
- [x] Topbar con ⌘K command palette placeholder
- [x] Remover colores hardcodeados inline en templates
- [x] Build limpio (tsc --noEmit + build:dev)

### Deliverables
- `tokens.css` con ~60 variables
- Layout shell sin PrimeNG Layout
- Sidebar reordenada
- Topbar simplificada

### Riesgos
- Layout de PrimeNG está muy acoplado a `app.layout.ts`
- Hay que probar cada ruta después del cambio

---

## Sprint 2: Botones + Cards + Icon system

**Duración:** 3-4 días
**Impacto:** Medio (componentes compartidos)

### Tasks
- [ ] Crear `au-btn` component (selector: `button[au-btn]`)
- [ ] Migrar todos los botones a `au-btn`
- [ ] Crear `au-card` component
- [ ] Migrar cards principales (dashboard, clientes, servicios)
- [ ] Sistema de iconos: SVG inline + `au-icon` component
- [ ] Reemplazar iconos de PrimeNG con SVG inline
- [ ] Crear `au-skeleton` con variantes (card, table, chart, avatar)
- [ ] Dashboard hero: saludo + KPI skeleton
- [ ] Build limpio

### Deliverables
- `au-btn`, `au-card`, `au-icon`, `au-skeleton`
- Dashboard hero con skeleton
- Menos dependencia de PrimeNG

---

## Sprint 3: Dialog + Toast + Empty State

**Duración:** 3-4 días
**Impacto:** Medio (componentes compartidos)

### Tasks
- [ ] Crear `au-dialog` (modal + backdrop + focus trap)
- [ ] Crear `au-toast` (servicio injectable + signal)
- [ ] Crear `au-empty-state` (con ilustración SVG inline)
- [ ] Migrar diálogos principales (POS payment, create/edit forms)
- [ ] Migrar toasts de `MessageService` a `uiStore.toasts`
- [ ] Reemplazar `p-confirmDialog` con `au-dialog` + confirm config
- [ ] Build limpio

### Deliverables
- `au-dialog`, `au-toast`, `au-empty-state`
- POS payment dialog migrado
- Sin PrimeNG MessageService

---

## Sprint 4: Table + Pagination + Badge + Tag

**Duración:** 5-7 días
**Impacto:** Alto (reemplazo de p-table)

### Tasks
- [ ] Crear `au-table` (virtual scroll, sticky header, sort, filter)
- [ ] Crear `au-pagination`
- [ ] Crear `au-badge` + `au-tag`
- [ ] Migrar tabla de clientes
- [ ] Migrar tabla de servicios
- [ ] Migrar tabla de productos
- [ ] Migrar tabla de empleados
- [ ] Migrar tabla de citas
- [ ] Migrar tabla de reportes
- [ ] Build limpio

### Deliverables
- `au-table`, `au-pagination`, `au-badge`, `au-tag`
- 6+ tablas migradas
- Peso de bundle reducido (sin p-table)

### Riesgos
- p-table tiene paginación, sorting, filtering, selection, row expand
- au-table debe cubrir al menos 80% de casos de uso
- Para el 20% restante: wrapper temporal

---

## Sprint 5: Input + Select + Form system

**Duración:** 4-5 días
**Impacto:** Alto (formularios)

### Tasks
- [ ] Crear `au-input` (wrapper de input nativo + label + error + hint)
- [ ] Crear `au-select` (combobox con search)
- [ ] Crear `au-textarea`
- [ ] Crear `au-checkbox` + `au-radio`
- [ ] Migrar formularios principales (create/edit de cada módulo)
- [ ] Form validation con mensajes de error consistentes
- [ ] Build limpio

### Deliverables
- `au-input`, `au-select`, `au-textarea`, `au-checkbox`, `au-radio`
- Formularios migrados (clientes, servicios, productos, empleados, citas)

---

## Sprint 6: Dashboard + Charts

**Duración:** 3-4 días
**Impacto:** Alto (página principal)

### Tasks
- [ ] Implementar dashboard hero con saludo + fecha + share link
- [ ] KPI row con count-up animation (ng2-charts)
- [ ] Best-selling widget con mini chart
- [ ] Recent sales widget con skeleton
- [ ] Revenue stream chart
- [ ] Onboarding progress bar (5/7 steps real)
- [ ] Dashboard responsive (2 columnas → 1 columna mobile)
- [ ] Build limpio

### Deliverables
- Dashboard 2.0 con hero, KPIs, widgets
- Skeleton loaders en todos los widgets
- Count-up animation en KPIs

---

## Sprint 7: POS redesign

**Duración:** 5-7 días
**Impacto:** Crítico (flujo core)

### Tasks
- [ ] POS layout: catálogo + cart dos columnas
- [ ] Mobile: FAB con contador + toggle vista
- [ ] Product card redesign con imagen y precio grande
- [ ] Cart panel con mejor visualización de items
- [ ] Coupon input integrado
- [ ] NCF selector mejorado
- [ ] Payment dialog con au-dialog
- [ ] Thermal ticket template mejorado
- [ ] Branch selector condicional por plan
- [ ] Build limpio

### Deliverables
- POS 2.0 con diseño mobile-first
- Mejor experiencia de cobro

---

## Sprint 8: Calendar + Appointments

**Duración:** 3-4 días
**Impacto:** Medio

### Tasks
- [ ] Calendar responsive (listWeek mobile, timeGridWeek desktop)
- [ ] Skeleton loader overlay en FullCalendar
- [ ] Appointment form con au-input / au-select
- [ ] Stylist filter + branch filter integrados
- [ ] Create appointment dialog con au-dialog
- [ ] Build limpio

### Deliverables
- Calendar responsive
- Skeleton overlay

---

## Sprint 9: Reports + Admin

**Duración:** 4-5 días
**Impacto:** Medio

### Tasks
- [ ] Report filters con au-select
- [ ] Report tables con au-table
- [ ] Export buttons (PDF, Excel) con au-btn
- [ ] Admin panel responsive
- [ ] Admin tables con au-table
- [ ] Admin filters con au-input / au-select
- [ ] Build limpio

### Deliverables
- Reports 2.0
- Admin 2.0

---

## Sprint 10: Performance + Accesibilidad + QA Final

**Duración:** 5-7 días
**Impacto:** Global

### Tasks
- [ ] `@defer` en POS, charts, admin, reports
- [ ] Lazy loading de imágenes
- [ ] Font-display swap + preconnect
- [ ] Lighthouse audit (target 95+)
- [ ] WCAG AA full audit
- [ ] Keyboard navigation audit
- [ ] Reduced-motion support
- [ ] Screen reader testing
- [ ] Build final + deploy

### Deliverables
- Lighthouse 95+
- WCAG AA compliant
- Bundle < 200KB inicial
