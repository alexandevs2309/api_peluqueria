# Reestructuración Visual — Auron Suite
**Versión:** 1.0  
**Fecha:** Julio 2026  
**Alcance:** Todo el frontend excepto Login y Register  
**Estado general:** 🔄 En progreso

---

## 📊 Estado de Avance

| Fase | Descripción | Estado |
|---|---|---|
| Fase 1 | Unificar sistema de color | ✅ Completada |
| Fase 2 | Headers de módulo con identidad específica | ✅ Completada |
| Fase 3 | Extraer componentes compartidos | ✅ Completada |
| Fase 4 | Iconografía SVG custom | ✅ Completada |
| Fase 5 | Unificar botón primario | ✅ Completada |
| Fase 6 | Tokens de spacing y sombras | ✅ Completada |

> **Instrucción para agente IA:** Al completar una fase, marcar su checkbox con `- [x]` y cambiar el emoji de estado de ⬜ a ✅. Al completar una tarea individual, marcar con `- [x]`. Registrar fecha de completado en el campo correspondiente.

---

## 1. Diagnóstico Ejecutivo

Auron Suite tiene una base técnica sólida pero carece de identidad visual cohesionada. El producto fue construido de forma incremental sin un sistema de diseño unificado, lo que resultó en 4 micro-sistemas paralelos que el usuario percibe como inconsistencia aunque no la articule.

**Puntuación actual por dimensión:**

| Dimensión | Puntuación actual | Objetivo |
|---|---|---|
| Identidad visual | 3/10 | 7/10 |
| Consistencia interna | 3/10 | 8/10 |
| Sincronía entre módulos | 3/10 | 8/10 |
| Branding reconocible | 4/10 | 7/10 |
| Sistema de diseño | 2/10 | 8/10 |
| Storytelling visual | 6/10 | 8/10 |
| Dirección de arte | 3/10 | 7/10 |
| Calidad percibida (premium) | 4/10 | 8/10 |
| UX | 6/10 | 8/10 |
| UI | 5/10 | 8/10 |
| AI Slop presente | 7/10 | ≤2/10 |

---

## 2. Los 4 Micro-sistemas Existentes (el problema raíz)

El frontend opera con 4 lenguajes visuales paralelos que nunca se integraron:

| Micro-sistema | Dónde vive | Características |
|---|---|---|
| **Landing** | `pages/landing/` | Tailwind puro + GSAP + `#2563EB` hardcodeado |
| **Módulos internos** | `pages/client/` | PrimeNG + Tailwind + `--brand` mezclado con `#2563EB` |
| **POS** | `pages/client/pos/` | CSS custom con BEM propio, sin PrimeNG en el shell |
| **Shell de app** | `layout/component/` | CSS custom con variables `--shell-*` propias |

El POS y el Shell son los más maduros. Los módulos internos son los más problemáticos.

---

## 3. Inventario de Problemas

### 3.1 Críticos

- [ ] **C1** — Paleta fragmentada: `#2563EB`, `#1A56DB`, `#527BFF`, `var(--primary-color)` para el mismo rol → *Solucionado en Fase 1*
- [ ] **C2** — Hero de dos columnas repetido en 6 módulos → *Solucionado en Fase 2*
- [ ] **C3** — Iconografía 100% PrimeNG sin personalización → *Solucionado en Fase 4*
- [ ] **C4** — 4 implementaciones del botón primario → *Solucionado en Fase 5*

### 3.2 Altos

- [ ] **A1** — Tokens de radius definidos pero no usados (`--app-radius-*` ignorados) → *Fase 6*
- [ ] **A2** — Empty states idénticos sin distinción contextual → *Fase 3*
- [ ] **A3** — 10 keyframes CSS con duplicados (fadeInUp ≈ slideUp, slideInLeft ≈ slideInFromLeft) → *Fase 6*
- [ ] **A4** — Paginación HTML copiada palabra por palabra entre Clientes y Empleados → *Fase 3*
- [ ] **A5** — Peso tipográfico inconsistente: `font-black` en landing, `font-semibold` en módulos para mismo rol → *Fase 1*
- [ ] **A6** — Sombras con valores arbitrarios inline en cada componente → *Fase 6*

### 3.3 Medios

- [ ] **M1** — Línea decorativa 3px repetida en las 5 feature cards sin variación
- [ ] **M2** — Badge "Novedad / v1.0" copiado de Tailwind UI changelog template
- [ ] **M3** — Eyebrow pill azul idéntico repetido 7 veces → *Fase 3*
- [ ] **M4** — Sidebar sin identidad Auron propia (íconos genéricos) → *Fase 4*
- [ ] **M5** — Activity Center usa `var(--primary-color)` en lugar de `var(--brand)` → *Fase 1*

### 3.4 Bajos

- [ ] **B1** — `lighten()`/`darken()` deprecated en `login.component.scss`
- [ ] **B2** — Clase `.report-card` usa variables CSS no sincronizadas con el sistema
- [ ] **B3** — `color-mix()` sin fallback para navegadores antiguos
- [ ] **B4** — `font-family` en body sin fallback stack completo

---

## 4. Lo Que Está Bien — No Tocar

| Elemento | Archivo | Por qué funciona |
|---|---|---|
| POS shell | `pos-system.scss` | BEM propio, variables propias, experiencia única |
| Activity Center | `app.topbar.ts` (estilos) | Diseño custom con sistema de items propio |
| Language panel | `app.topbar.ts` (estilos) | Bien ejecutado, consistente internamente |
| Team roster de Empleados | `employees-management.ts` | Identidad específica de dominio |
| Copy de la landing | `landing.ts` | Voz directa y propia |
| Mockups reales en hero | `herowidget-modern.ts` | `real-dashboard-blurred.webp` — muestra el producto real |
| Sistema de tokens base | `style.scss` | La intención es correcta |
| Search bar del topbar | `app.topbar.ts` | Diseño con identidad propia (Ctrl K, pill shape) |
| Toggle mensual/anual | `pricingwidget.ts` | Sliding indicator animado bien ejecutado |

---

## 5. Plan de Corrección por Fases

---

### ✅ FASE 1 — Unificar el sistema de color
**Estado:** `- [x] Completada`  
**Completado el:** 2026-07-05  
**Estimación:** 1-2 días  
**Impacto:** Visual inmediato en toda la app. Bajo riesgo de regresión.

**Objetivo:** eliminar los 4 azules distintos. Toda la app usa `--brand: #1A56DB`.

#### Tareas

- [x] **1.1** — Auditar y listar todas las ocurrencias de `#2563EB` hardcodeado en la codebase
  - Archivos afectados principales: `featureswidget.ts`, `landing.ts`, `pricingwidget.ts`, `testimonialswidget.ts`, `herowidget-modern.ts`

- [x] **1.2** — Reemplazar `#2563EB` → `var(--brand)` en `featureswidget.ts`
  - Referencias: color de íconos, chips, líneas decorativas, textos de acento

- [x] **1.3** — Reemplazar `#2563EB` → `var(--brand)` en `landing.ts`
  - Referencias: sección "problema", sección "comparación", sección "trust", sección "lead-capture"

- [x] **1.4** — Reemplazar `#2563EB` → `var(--brand)` en `pricingwidget.ts`
  - Referencias: header, toggle, cards, enterprise card

- [x] **1.5** — Reemplazar `#2563EB` → `var(--brand)` en `testimonialswidget.ts`
  - Referencias: badge, barra superior, avatar gradient

- [x] **1.6** — Reemplazar `#2563EB` → `var(--brand)` en `herowidget-modern.ts`
  - Referencias: badge "Novedad", stats (si aplica)

- [x] **1.7** — Reemplazar `#527BFF` → `var(--brand-400)` en módulos internos (dark mode contexts)
  - Archivos: `employees-management.ts`, `clients-management.ts`, y cualquier módulo que lo use

- [x] **1.8** — Reemplazar `var(--primary-color)` → `var(--brand)` en estilos custom del topbar
  - Archivo: `app.topbar.ts` — `.activity-center-panel__link`, `.language-panel__current`, `.language-option.active`

- [x] **1.9** — Reemplazar `#3B82F6` (blue-500 Tailwind) por `var(--brand-400)` en dark mode contexts
  - Mismo proceso que 1.7 pero para el azul claro

- [x] **1.10** — Verificar que `style.scss` sobreescribe correctamente `--p-primary-color` de PrimeNG con `var(--brand)`
  - Actualmente: `.p-button { background-color: #1A56DB !important }` — validar que no haya conflictos

- [x] **1.11** — Unificar pesos tipográficos: definir en `style.scss` los roles h1/h2/h3 con `font-weight` específico que funcione tanto en landing como en internos
  - Propuesta: `--font-display: 800`, `--font-heading: 700`, `--font-subheading: 600`, `--font-body: 500`

- [x] **1.12** — Build sin errores ni warnings nuevos tras los cambios
- [x] **1.13** — Revisión visual: abrir cada sección afectada y confirmar un solo azul visible

**✅ Marcar fase completada cuando todos los checkboxes anteriores estén marcados**
`- [x] FASE 1 COMPLETADA`

---

### ✅ FASE 2 — Headers de módulo con identidad específica
**Estado:** `- [ ] En progreso`  
**Completado el:** ___________  
**Estimación:** 3-4 días (1 módulo por día)  
**Nota:** Empleados ya fue completado con el team roster. Usar como referencia.

**Objetivo:** eliminar el hero genérico de dos columnas de todos los módulos y reemplazarlo por un header con identidad de dominio.

#### Tareas

- [x] **2.1** — Módulo Empleados: team roster implementado ✅ *(completado)*

- [x] **2.2** — Módulo Clientes: reemplazar hero por "Radar de relaciones"
  - Mostrar los últimos 3 clientes que visitaron (nombre + fecha + servicio)
  - Mostrar el cliente con más visitas del mes como elemento destacado
  - Stats: total, activos, con contacto — en strip horizontal (sin cards grandes)
  - Eliminar la action card genérica del lado derecho

- [x] **2.3** — Módulo Servicios: reemplazar hero por "Catálogo vivo"
  - Mostrar top 3 servicios (más vendido / más rentable / más rápido) como chips visuales
  - Stats: total servicios, activos, categorías — en strip
  - El botón "Nuevo servicio" integrado en el header, no en la action card

- [x] **2.4** — Módulo Productos: reemplazar hero por "Control de inventario"
  - Si hay productos bajo mínimo: mostrar alerta visual dominante con lista de productos críticos
  - Si no hay alertas: mostrar stats de stock total, productos activos, valor aproximado
  - Eliminar el hero de dos columnas completamente

- [x] **2.5** — Módulo Reportes: reemplazar hero por encabezado editorial
  - Eliminar el grid de dos columnas
  - Nuevo header: nombre del negocio (grande) + período activo + frase narrativa generada
  - Ejemplo: "Auron Suite · Enero–Junio 2026 · Tu mejor mes fue marzo con DOP 45,000"
  - Los filtros de fecha van debajo del header, no dentro de él

- [x] **2.6** — Módulo Agenda: reemplazar hero por "Estado del día"
  - Mostrar hora actual prominente + "Próxima cita en X minutos"
  - Strip con: citas hoy / pendientes / completadas — números grandes, no cards
  - El botón "Nueva cita" en posición fija a la derecha del header

- [x] **2.7** — Revisión visual de los 5 módulos modificados: confirmar que cada uno se siente distinto al anterior

**✅ Marcar fase completada cuando todos los checkboxes anteriores estén marcados**
`- [x] FASE 2 COMPLETADA`

---

### ✅ FASE 3 — Extraer componentes compartidos
**Estado:** `- [x] Completada`  
**Completado el:** 2026-07-05  
**Estimación:** 2-3 días  
**Objetivo:** eliminar duplicación. Un componente, una fuente de verdad.

#### Tareas

- [x] **3.1** — Crear `src/app/shared/components/auron-pagination/auron-pagination.component.ts`
  - Props: `currentPage`, `totalPages`, `pageSize`, `totalRecords`, labels i18n
  - Eventos: `pageChange`, `pageSizeChange`
  - Migrar desde: `clients-management.ts` y `employees-management.ts`

- [x] **3.2** — Reemplazar paginación en `clients-management.ts` con `<auron-pagination>`

- [x] **3.3** — Reemplazar paginación en `employees-management.ts` con `<auron-pagination>`

- [x] **3.4** — Crear `src/app/shared/components/auron-empty-state/auron-empty-state.component.ts`
  - Props: `icon`, `title`, `description`, `ctaLabel?`, `ctaAction?`, `variant?` (default/contextual)
  - Reemplazar los `.auron-empty-state` de los módulos que usan el mismo patrón genérico

- [x] **3.5** — Migrar empty state de `clients-management.ts` a `<auron-empty-state>`
  - Texto específico: "Aún no tienes clientes registrados. Cuando alguien agende, aparecerá aquí."

- [x] **3.6** — Migrar empty state de `services-management.ts` a `<auron-empty-state>`
  - Texto específico: "Sin servicios, el POS no puede procesar ventas."

- [x] **3.7** — Migrar empty state de `products-management.ts` a `<auron-empty-state>`
  - Texto específico: "Sin productos en inventario. Agrega uno para que aparezca en el POS."

- [x] **3.8** — Migrar empty state de `appointments-management.ts` a `<auron-empty-state>`
  - Texto específico: "No hay citas para este período. Crea la primera o ajusta los filtros."

- [x] **3.9** — Crear `src/app/shared/components/auron-eyebrow/auron-eyebrow.component.ts`
  - Props: `label`, `icon?`, `variant?` (default/success/warning/info)
  - Reemplazar las 7 ocurrencias del pill hardcodeado

- [x] **3.10** — Consolidar los 10 keyframes en `style.scss` a 4 canónicos:
  - `au-fade-up` (reemplaza: fadeInUp, slideUp, animate-fade-in-up)
  - `au-slide-in` (reemplaza: slideInLeft, slideInFromLeft, slideInRight, slideInFromRight)
  - `au-float` (conservar)
  - `au-fade-in` (reemplaza: fadeIn, animate-fade-in)

- [x] **3.11** — Build sin errores tras todas las migraciones

**✅ Marcar fase completada cuando todos los checkboxes anteriores estén marcados**
`- [x] FASE 3 COMPLETADA`

---

### ✅ FASE 4 — Iconografía SVG custom
**Estado:** `- [x] Completada`  
**Completado el:** 2026-07-05  
**Estimación:** 1-2 días  
**Objetivo:** reemplazar los 8 íconos más visibles con SVGs que tengan personalidad Auron.

**Especificaciones de los SVGs:**
- Grilla: 24x24px
- Stroke-width: 1.5px
- Line caps: round
- Estilo: outline (no filled), geométrico limpio

#### Tareas

- [x] **4.1** — Crear `src/assets/icons/` directorio para SVGs custom

- [x] **4.2** — Crear componente `src/app/shared/components/auron-icon/auron-icon.component.ts`
  - Props: `name`, `size?` (default 20), `color?`
  - Carga SVG via `[innerHTML]` con sanitización

- [x] **4.3** — Diseñar y crear SVG: `agenda.svg` (tijeras + calendario, reemplaza `pi-calendar` en menú)

- [x] **4.4** — Diseñar y crear SVG: `pos.svg` (caja registradora simplificada, reemplaza `pi-shopping-cart` en menú)

- [x] **4.5** — Diseñar y crear SVG: `reports.svg` (gráfica con flecha ascendente geométrica, reemplaza `pi-chart-line` en menú)

- [x] **4.6** — Diseñar y crear SVG: `clients.svg` (siluetas minimalistas, reemplaza `pi-users` en clientes)

- [x] **4.7** — Diseñar y crear SVG: `dashboard.svg` (cuadrícula con un elemento destacado, reemplaza `pi-home` en menú)

- [x] **4.8** — Reemplazar los 5 íconos en `app.menu.ts` con el nuevo componente `<auron-icon>`

- [x] **4.9** — Reemplazar el ícono de Agenda en `appointments-management.ts` header con `<auron-icon name="agenda">`

- [x] **4.10** — Verificar que los SVGs se ven bien en dark mode y en los 3 tamaños: 16, 20, 24px

**✅ Marcar fase completada cuando todos los checkboxes anteriores estén marcados**
`- [x] FASE 4 COMPLETADA`

---

### ✅ FASE 5 — Unificar botón primario
**Estado:** `- [ ] En progreso`  
**Completado el:** ___________  
**Estimación:** 1 día  
**Objetivo:** un solo botón primario en toda la app.

#### Tareas

- [x] **5.1** — Agregar en `style.scss` el sistema `.au-btn`:
  ```css
  .au-btn { /* base */ }
  .au-btn-primary { /* fondo brand, texto blanco, sombra */ }
  .au-btn-secondary { /* borde brand, fondo transparente */ }
  .au-btn-ghost { /* solo texto */ }
  .au-btn-danger { /* fondo error */ }
  .au-btn-sm { /* padding reducido */ }
  .au-btn-lg { /* padding aumentado */ }
  ```

- [x] **5.2** — Migrar `.btn-hero-cta` en `herowidget-modern.ts` a `.au-btn .au-btn-primary .au-btn-lg`

- [x] **5.3** — Auditar todos los `pButton` en módulos internos e identificar cuáles son CTAs primarios

- [x] **5.4** — Validar que `style.scss` ya sobreescribe correctamente el color de `pButton` con `--brand`
  - Si no, agregar: `:root { --p-button-primary-background: var(--brand); }`

- [x] **5.5** — Documentar en comentario en `style.scss` la jerarquía de botones para futuros desarrolladores

- [x] **5.6** — Revisión visual: verificar que todos los CTAs primarios se ven consistentes en landing y módulos

**✅ Marcar fase completada cuando todos los checkboxes anteriores estén marcados**
`- [x] FASE 5 COMPLETADA`

---

### ✅ FASE 6 — Tokens de spacing y sombras
**Estado:** `- [ ] En progreso`  
**Completado el:** ___________  
**Estimación:** 0.5 días  
**Objetivo:** eliminar valores arbitrarios, activar los tokens existentes.

#### Tareas

- [x] **6.1** — Agregar en `style.scss` los tokens faltantes:
  ```css
  :root {
    /* Shadows */
    --shadow-card:     0 1px 3px rgba(15,23,42,0.08), 0 1px 2px rgba(15,23,42,0.06);
    --shadow-elevated: 0 12px 40px -12px rgba(15,23,42,0.28);
    --shadow-overlay:  0 24px 70px rgba(15,23,42,0.18);
    
    /* Radius expandidos */
    --app-radius-2xl: 1.5rem;
    --app-radius-3xl: 2rem;
    
    /* Typography scale */
    --font-display: 800;
    --font-heading: 700;
    --font-subheading: 600;
    --font-body: 500;
    
    /* Font stack completo */
    --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }
  ```

- [x] **6.2** — Migrar `shadow-[0_24px_80px_-42px_rgba(15,23,42,0.45)]` → `var(--shadow-elevated)` en módulos internos

- [x] **6.3** — Corregir `.report-card` en `style.scss`: cambiar `var(--surface)` → `var(--surface-card)` y `var(--border)` → `var(--surface-border)`

- [x] **6.4** — Agregar `font-family: var(--font-family)` en `body` de `style.scss`

- [x] **6.5** — Consolidar los keyframes duplicados (tarea 3.10 si no fue hecha antes)

- [x] **6.6** — Corregir `lighten()`/`darken()` deprecated en `login.component.scss`:
  - `lighten($color, 2%)` → `color.adjust($color, $lightness: 2%)`
  - `darken($color, 5%)` → `color.adjust($color, $lightness: -5%)`
  - Agregar `@use 'sass:color';` al inicio del archivo

- [x] **6.7** — Build sin warnings de Sass tras corrección de deprecated functions

**✅ Marcar fase completada cuando todos los checkboxes anteriores estén marcados**
`- [x] FASE 6 COMPLETADA`

---

## 6. Gesto Visual Único — Sistema de Color Semántico por Módulo

Un producto premium tiene un gesto que solo él haría. Para Auron Suite: **borde izquierdo de color semántico en elementos de lista y tarjetas**.

| Módulo | Color acento | Variable CSS a crear |
|---|---|---|
| Agenda / Citas | `#0284c7` (azul cielo) | `--module-agenda: #0284c7` |
| POS / Caja | `#059669` (verde dinero) | `--module-pos: #059669` |
| Clientes | `#7c3aed` (violeta) | `--module-clients: #7c3aed` |
| Empleados | `#1A56DB` (brand) | `--module-employees: var(--brand)` |
| Servicios | `#d97706` (ámbar) | `--module-services: #d97706` |
| Productos | `#dc2626` (rojo urgencia) | `--module-products: #dc2626` |
| Reportes | `#0f172a` (slate) | `--module-reports: #0f172a` |

- [ ] **Implementar sistema de color semántico** (puede hacerse progresivamente durante Fase 2)

---

## 7. Métricas de Éxito

Al finalizar toda la reestructuración:

- [ ] Un solo valor hex para el color primario en toda la codebase
- [ ] Cero usos de `var(--primary-color)` en estilos custom de Auron
- [ ] Cero bloques `<section class="rounded-[2rem] border ... grid lg:grid-cols-[...]">` duplicados entre módulos
- [ ] Todos los empty states con texto específico al módulo
- [ ] Paginación en un único componente reutilizable
- [ ] `shadow-[...]` con valores arbitrarios reemplazados por tokens
- [ ] Al menos 5 íconos SVG custom en los puntos más visibles
- [ ] Sistema de color semántico por módulo implementado en ≥3 módulos
- [ ] Build sin warnings de Sass deprecated
- [ ] AI Slop score ≤2/10 en revisión post-implementación

---

## 8. Calendario

```
Semana 1:
  Día 1-2:  Fase 1 — Unificar color            [ ] Pendiente
  Día 3:    Fase 5 — Botón primario unificado   [ ] Pendiente
  Día 4-5:  Fase 6 — Tokens de sombra y radius  [ ] Pendiente

Semana 2:
  Día 1-2:  Fase 3 — Componentes compartidos    [ ] Pendiente
  Día 3-5:  Fase 2 — Headers (Clientes, Servicios, Productos)

Semana 3:
  Día 1-2:  Fase 2 — Headers (Reportes, Agenda)
  Día 3-4:  Fase 4 — 5 íconos SVG custom        [ ] Pendiente
  Día 5:    Validación visual completa           [ ] Pendiente
```

**Estimación total:** 10-12 días de trabajo de frontend.

---

## 9. Registro de Cambios

| Fecha | Fase | Tarea | Responsable | Notas |
|---|---|---|---|---|
| 2026-07-05 | 6 | Fase 6 completada | Codex | Sombras internas migradas a `--shadow-*`, `.report-card` corregido a tokens Prime, keyframes globales consolidados a `au-*`, Sass deprecated sin warnings. Build `npm run build:dev` OK. |
| 2026-07-05 | 5 | Fase 5 completada | Codex | `.btn-hero-cta` migrado a `.au-btn`; CTAs primarios de landing/servicios/agenda/ROI/footer/popup alineados. Build `npm run build:dev` OK. Revisión visual: `/tmp/auron-fase5-landing.png`. |
| 2026-07-05 | 1 | Fase 1 completada | Codex | Build `npm run build:dev` OK. Revisión visual con captura local `/tmp/auron-fase1-landing.png`: primario azul consistente en landing/CTAs/badges. |
| 2026-07-05 | 1, 3, 4, 5, 6 | Avance implementado y build verificado | Codex | Color tokens/landing/topbar/client modules, `auron-pagination`, `auron-empty-state`, `auron-icon`, `.au-btn`, tokens spacing/sombras/font, Sass deprecated corregido. Build: `npm run build:dev` OK. |
| 2026-07-04 | Empleados | Team roster implementado | Kiro | Header específico de dominio |
| 2026-07-04 | — | Warning `mfaCode?.invalid` corregido | Kiro | login.component.html L243 |
| — | — | — | — | — |

---

## 10. Lo Que Esta Reestructuración NO Hace

- Rediseño del Login y Register (excluidos explícitamente)
- Cambios en el backend o API
- Traducción i18n de los nuevos textos
- Ilustraciones o imágenes nuevas
- Rediseño de la landing page (solo corrección de color)
- Cambios en la paleta de colores (solo consolidación del azul existente)
- Nuevas funcionalidades de UX

---

*Este documento es la fuente de verdad para la reestructuración visual de Auron Suite.*  
*Un agente IA debe leer este archivo al inicio de cada sesión para determinar qué fase ejecutar a continuación.*  
*Marcar `- [x]` en cada tarea completada y registrar en la tabla de cambios.*
