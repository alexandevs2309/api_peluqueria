# AURON Design System 2.0

> Inspirado en: Stripe, Linear, Vercel, Raycast, Supabase
> No copia: transformación de principios en sistema propio

---

## 1. Design DNA

```
AURON es cálido pero profesional.
  → Terracota, no azul corporativo.
  → Neutros cálidos, no grises fríos.
  → Bordes generosos, no ángulos rectos.

AURON es premium pero accesible.
  → Display typography para jerarquía.
  → Motion con propósito, no decorativo.
  → Whitespace como feature, no como bug.

AURON es potente pero simple.
  → Cada pantalla tiene UNA acción principal.
  → Datos visibles, configuración oculta.
  → El onboarding guía, no abruma.
```

---

## 2. Color System (simplificado)

### Token architecture (ELIMINAR duplicación)

```
:root {
  --brand-50  → --brand-950     // Escala completa de marca
  --neutral-50 → --neutral-950  // Neutros cálidos (antes --gray-*)
  --success, --warning, --danger, --info  // Semánticos
  --surface-ground, --surface-card, --surface-border, --surface-hover
  --text-primary, --text-secondary, --text-tertiary, --text-disabled
}
```

### Paleta (ajustes sobre la actual)

| Token | Valor actual | Nuevo valor | Razón |
|-------|-------------|-------------|-------|
| `--brand` | `#1A56DB` | `#1A56DB` | Se mantiene — buen contraste |
| `--accent` | `#D97706` | `#C8674A` | Terracota es nuestra identidad |
| `--coral` | `#E0586A` | `#E0586A` | Se mantiene |
| `--success` | `#4A8C5C` | `#4A8C5C` | Se mantiene |
| `--warning` | `#D4A84B` | `#D4A84B` | Se mantiene |
| `--danger` | `#B84A4A` | `#B84A4A` | Se mantiene |
| `--info` | `#C8674A` | `#2563EB` | Info debe ser neutral, no terracota |

### Superficies

```css
:root {
  --surface-ground:     #F7F8FA;  // Fondo general
  --surface-card:       #FFFFFF;  // Tarjetas
  --surface-elevated:   #FFFFFF;  // Modales, dropdowns
  --surface-border:     #E4E7EC;  // Bordes
  --surface-hover:      #F0F1F3;  // Hover en tablas/listas

  --text-primary:       #101828;  // Títulos
  --text-secondary:     #475467;  // Body
  --text-tertiary:      #98A2B3;  // Metadatos, placeholders
  --text-disabled:      #D0D5DD;  // Deshabilitado
}

.app-dark {
  --surface-ground:     #0C0E12;
  --surface-card:       #13161D;
  --surface-elevated:   #1A1F2B;
  --surface-border:     #1F2330;
  --surface-hover:      #1A1F2B;

  --text-primary:       #F0F2F5;
  --text-secondary:     #8C93A4;
  --text-tertiary:      #5A6276;
  --text-disabled:      #343A4A;
}
```

---

## 3. Typography Scale

### Font families (se mantienen)

```css
--font-ui:    'Inter', -apple-system, system-ui, sans-serif;
--font-display: 'EB Garamond', 'Georgia', serif;
--font-mono:  'JetBrains Mono', 'Fira Code', monospace;  // NUEVO
```

### Type scale (ajustada)

```css
--text-xs:     0.6875rem;  // 11px — etiquetas
--text-sm:     0.8125rem;  // 13px — metadatos
--text-base:   0.9375rem;  // 15px — body (cambio de 14px a 15px)
--text-lg:     1.0625rem;  // 17px — body grande
--text-xl:     1.25rem;    // 20px — subtítulos
--text-2xl:    1.5rem;     // 24px — títulos de sección
--text-3xl:    2rem;       // 32px — títulos de página
--text-4xl:    2.75rem;    // 44px — display chico
--text-5xl:    3.75rem;    // 60px — display medio
--text-6xl:    5rem;       // 80px — display grande
```

### Line height scale

```css
--leading-none:    1;
--leading-tight:   1.1;
--leading-snug:    1.2;
--leading-normal:  1.5;
--leading-relaxed: 1.6;
--leading-loose:   1.8;
```

### Font weight tokens

```css
--font-normal:    400;
--font-medium:    500;
--font-semibold:  600;
--font-bold:      700;
--font-black:     900;
```

---

## 4. Spacing Scale (unificada)

```css
--space-0:     0px;
--space-0\.5:  0.125rem;  // 2px
--space-1:     0.25rem;   // 4px
--space-1\.5:  0.375rem;  // 6px
--space-2:     0.5rem;    // 8px
--space-2\.5:  0.625rem;  // 10px
--space-3:     0.75rem;   // 12px
--space-3\.5:  0.875rem;  // 14px
--space-4:     1rem;      // 16px
--space-5:     1.25rem;   // 20px
--space-6:     1.5rem;    // 24px
--space-7:     1.75rem;   // 28px
--space-8:     2rem;      // 32px
--space-9:     2.25rem;   // 36px
--space-10:    2.5rem;    // 40px
--space-12:    3rem;      // 48px
--space-14:    3.5rem;    // 56px
--space-16:    4rem;      // 64px
--space-20:    5rem;      // 80px
--space-24:    6rem;      // 96px
```

---

## 5. Radius Scale (más generosa)

```css
--radius-none:  0px;
--radius-xs:    0.375rem;  // 6px  — badges, tags pequeños
--radius-sm:    0.5rem;    // 8px  — inputs, botones
--radius-md:    0.75rem;   // 12px — cards, tablas
--radius-lg:    1rem;      // 16px — diálogos, modales
--radius-xl:    1.25rem;   // 20px — cards principales, sidebar
--radius-2xl:   1.5rem;    // 24px — contenedores hero, dashboard
--radius-3xl:   2rem;      // 32px — elementos especiales
--radius-pill:  9999px;    // pills, badges, avatares
```

---

## 6. Elevation & Shadows

```css
--shadow-xs:    0 1px 2px rgba(30, 27, 24, 0.05);
--shadow-sm:    0 1px 3px rgba(30, 27, 24, 0.08), 0 1px 2px rgba(30, 27, 24, 0.04);
--shadow-md:    0 4px 8px rgba(30, 27, 24, 0.08), 0 2px 4px rgba(30, 27, 24, 0.04);
--shadow-lg:    0 8px 24px rgba(30, 27, 24, 0.10), 0 2px 8px rgba(30, 27, 24, 0.04);
--shadow-xl:    0 12px 40px rgba(30, 27, 24, 0.12), 0 4px 12px rgba(30, 27, 24, 0.06);
--shadow-2xl:   0 24px 80px rgba(30, 27, 24, 0.15);
```

Todas las sombras usan RGB cálido `(30, 27, 24)` — como ya está implementado.

---

## 7. Animation Tokens

```css
--duration-instant:  0ms;
--duration-fast:    100ms;
--duration-normal:  200ms;
--duration-slow:    300ms;
--duration-slower:  500ms;

--ease-linear:      linear;
--ease-in:          cubic-bezier(0.4, 0, 1, 1);
--ease-out:         cubic-bezier(0, 0, 0.2, 1);
--ease-in-out:      cubic-bezier(0.4, 0, 0.2, 1);
--ease-spring:      cubic-bezier(0.16, 1, 0.3, 1);
--ease-bounce:      cubic-bezier(0.34, 1.56, 0.64, 1);
```

---

## 8. Layout Constants

```css
--sidebar-width:      260px;     // Reducido de 300px
--sidebar-collapsed:  0px;
--topbar-height:      4rem;      // Reducido de 4.75rem
--topbar-inset:       0.75rem;   // Reducido de 1rem
--main-padding-x:     2rem;      // Aumentado de 1.5rem
--main-padding-top:   calc(var(--topbar-height) + var(--topbar-inset) * 2 + 0.5rem);
--content-max-width:  1440px;    // Reducido de 1504px
```

Razón: más espacio útil para el contenido principal. Sidebar más delgado, topbar más compacto.

---

## 9. Component Architecture

### Capas de componentes

```
┌─────────────────────────────────────────────────────┐
│  Layer 4: Feature Components (POS, Appointments...)  │
│  ┌─────────────────────────────────────────────────┐ │
│  │  Layer 3: Composed Components (DataTable,       │ │
│  │             KPI Card, Timeline, Stepper...)      │ │
│  │  ┌─────────────────────────────────────────────┐ │ │
│  │  │  Layer 2: Primitives (Button, Input, Badge, │ │ │
│  │  │             Dialog, Toast, Avatar...)        │ │ │
│  │  │  ┌─────────────────────────────────────────┐ │ │ │
│  │  │  │  Layer 1: Atoms (Icon, Text, Spacer,    │ │ │ │
│  │  │  │            Divider, Skeleton)            │ │ │ │
│  │  │  └─────────────────────────────────────────┘ │ │ │
│  │  └─────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Estrategia de reemplazo de PrimeNG

**Mantener (aporta valor real):**
- `p-calendar` — date picking complejo
- `p-fileupload` — upload con progreso
- `p-editor` — editor rich text
- `p-chart` — chart.js wrapper
- `p-table` — solo si necesitamos virtual scroll pesado

**Reemplazar en Sprint 1:**
- `p-button` → `<button class="au-btn">`
- `p-card` → `<au-card>`
- `p-dialog` → `<au-dialog>`
- `p-toast` → `<au-toast>`
- `p-badge` → `<au-badge>`
- `p-tag` → `<au-tag>`
- `p-inputtext` → `<au-input>`
- `p-select` → `<au-select>`
- `p-skeleton` → `<au-skeleton>`
- `p-avatar` → `<au-avatar>`

**Reemplazar en Sprint 2:**
- `p-datatable` → `<au-table>`
- `p-dropdown` → `<au-dropdown>`
- `p-paginator` → `<au-pagination>`
- `p-tabs` → `<au-tabs>`
- `p-accordion` → `<au-accordion>`
- `p-menu` → `<au-menu>`
- `p-panelmenu` → `<au-panel-menu>`

**Reemplazar en Sprint 3+:**
- `p-calendar` → `<au-datepicker>`
- `p-chart` → `<au-chart>`
- `p-fileupload` → `<au-upload>`
- `p-editor` → `<au-editor>`
