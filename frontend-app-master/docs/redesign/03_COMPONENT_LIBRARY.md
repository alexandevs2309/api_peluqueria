# AURON Component Library — Arquitectura

> Principio: componentes standalone, signals, sin NgModules. Reemplazo progresivo de PrimeNG.

---

## 1. Estructura de directorios

```
src/app/shared/componetes/
├── primitives/              # Layer 1: Átomos
│   ├── au-icon/
│   ├── au-text/
│   ├── au-skeleton/
│   ├── au-divider/
│   └── au-spacer/
├── ui/                      # Layer 2: Primitivos compuestos
│   ├── au-btn/
│   ├── au-input/
│   ├── au-select/
│   ├── au-badge/
│   ├── au-tag/
│   ├── au-avatar/
│   ├── au-dialog/
│   ├── au-toast/
│   ├── au-card/
│   └── au-modal/
├── composed/                # Layer 3: Compuestos
│   ├── au-table/
│   ├── au-pagination/
│   ├── au-tabs/
│   ├── au-accordion/
│   ├── au-stepper/
│   ├── au-timeline/
│   ├── au-kpi-card/
│   ├── au-empty-state/
│   └── au-menu/
└── index.ts                 # Barrel export
```

---

## 2. Estándar de componente

```typescript
// shared/componetes/ui/au-btn/au-btn.component.ts
@Component({
  selector: 'button[au-btn], a[au-btn]',  // Extiende nativos
  standalone: true,
  imports: [NgClass],
  host: {
    '[class.au-btn]': 'true',
    '[class.au-btn--primary]': 'variant === "primary"',
    '[class.au-btn--secondary]': 'variant === "secondary"',
    '[class.au-btn--ghost]': 'variant === "ghost"',
    '[class.au-btn--danger]': 'variant === "danger"',
    '[class.au-btn--sm]': 'size === "sm"',
    '[class.au-btn--lg]': 'size === "lg"',
    '[class.au-btn--icon]': 'iconOnly',
    '[class.au-btn--loading]': 'loading',
    '[disabled]': 'disabled || loading',
  },
  template: `
    @if (loading) {
      <span class="au-btn__spinner" aria-hidden="true"></span>
    }
    @if (icon && !loading) {
      <au-icon [name]="icon" class="au-btn__icon" />
    }
    <span class="au-btn__text"><ng-content /></span>
  `,
})
export class AuBtn {
  readonly variant = input<'primary' | 'secondary' | 'ghost' | 'danger'>('primary');
  readonly size = input<'sm' | 'md' | 'lg'>('md');
  readonly icon = input<string>();
  readonly iconOnly = input(false);
  readonly loading = input(false);
  readonly disabled = input(false);
}
```

---

## 3. Catálogo de componentes

### Layer 1: Primitives

| Componente | Selector | Props | Notas |
|-----------|----------|-------|-------|
| Icon | `<au-icon>` | `name`, `size`, `variant` | SVG inline con `currentColor` |
| Text | `<span au-text>` | `variant` (h1-h6, body, caption), `align` | Utility |
| Skeleton | `<au-skeleton>` | `type` (text, card, table, avatar), `width`, `height`, `lines` | Variantes específicas |
| Divider | `<au-divider>` | `orientation`, `label` | — |
| Spacer | `<au-spacer>` | `size`, `axis` | Flex gap utility |

### Layer 2: UI Components

| Componente | Selector | Props | Notas |
|-----------|----------|-------|-------|
| Button | `<button au-btn>` | `variant`, `size`, `icon`, `loading`, `disabled` | Extiende `<button>` |
| Input | `<au-input>` | `label`, `placeholder`, `error`, `hint`, `prefix`, `suffix` | Wrapper sobre input nativo |
| Select | `<au-select>` | `options`, `placeholder`, `searchable` | Combobox con search |
| Badge | `<au-badge>` | `value`, `variant` (dot, number, text), `severity` | Notificación |
| Tag | `<au-tag>` | `severity`, `closable` | Status tag |
| Avatar | `<au-avatar>` | `src`, `label`, `size`, `shape` | Con fallback iniciales |
| Dialog | `<au-dialog>` | `title`, `open`, `closable`, `size` | Modal + backdrop |
| Toast | `<au-toast>` | Signal-based service | Servicio injectable |
| Card | `<au-card>` | `title`, `subtitle`, `padding` | Glass/hover por variante |
| Dropdown | `<au-dropdown>` | `items`, `position` | Menú contextual |

### Layer 3: Composed Components

| Componente | Props | Notas |
|-----------|-------|-------|
| DataTable | `columns`, `data`, `sortable`, `filterable`, `paginated` | Virtual scroll + sticky header |
| Pagination | `page`, `total`, `perPage`, `onPageChange` | Botón numérico + prev/next |
| Tabs | `tabs[]`, `activeTab`, `onTabChange` | Line indicator animation |
| Stepper | `steps[]`, `currentStep` | Con barra de progreso + checkmarks |
| Timeline | `items[]`, `orientation` | Eventos cronológicos |
| KpiCard | `label`, `value`, `trend`, `icon` | Dashboard widget |
| EmptyState | `title`, `description`, `illustration`, `action` | Por módulo |
| Menu | `items[]`, `collapsed` | Sidebar + dropdown |

---

## 4. CSS Architecture

Cada componente tiene su propio `.scss` usando **BEM-like** + CSS custom properties:

```scss
// au-btn.component.scss
@use '../../../styles/tokens' as *;

.au-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-sm);
  font-family: var(--font-ui);
  font-weight: var(--font-medium);
  font-size: var(--text-sm);
  line-height: var(--leading-snug);
  cursor: pointer;
  border: 1px solid transparent;
  transition: all var(--duration-fast) var(--ease-out);
  user-select: none;

  /* Primary */
  &--primary {
    background: var(--brand);
    color: white;
    box-shadow: var(--shadow-xs);

    &:hover {
      background: var(--brand-600);
      transform: translateY(-1px);
      box-shadow: var(--shadow-sm);
    }

    &:active {
      transform: translateY(0);
      box-shadow: var(--shadow-xs);
    }
  }

  /* Secondary */
  &--secondary {
    background: var(--surface-card);
    color: var(--text-primary);
    border-color: var(--surface-border);

    &:hover {
      background: var(--surface-hover);
      border-color: var(--brand-200);
    }
  }

  /* Ghost */
  &--ghost {
    background: transparent;
    color: var(--text-primary);

    &:hover {
      background: var(--surface-hover);
    }
  }

  /* Danger */
  &--danger {
    background: var(--danger);
    color: white;

    &:hover {
      background: var(--danger-600); // darkened
    }
  }

  /* States */
  &--loading { pointer-events: none; opacity: 0.7; }
  &:disabled { opacity: 0.4; pointer-events: none; }

  /* Sizes */
  &--sm { padding: var(--space-1) var(--space-3); font-size: var(--text-xs); }
  &--lg { padding: var(--space-3) var(--space-6); font-size: var(--text-base); }

  /* Icon only */
  &--icon { padding: var(--space-2); aspect-ratio: 1; }

  &__spinner {
    width: 1em;
    height: 1em;
    border: 2px solid currentColor;
    border-top-color: transparent;
    border-radius: 50%;
    animation: auSpin 0.6s linear infinite;
  }
}

@keyframes auSpin {
  to { transform: rotate(360deg); }
}
```

---

## 5. Bundle Strategy

```
Cada componente standalone es tree-shakeable.
Solo se incluye en el bundle si se importa.
```

**Tamaño target por componente:** `< 3KB gzipped`

| Componente | Target size | Actual estimate |
|-----------|-------------|-----------------|
| au-btn | < 1KB | 0.8KB |
| au-input | < 2KB | 1.5KB |
| au-dialog | < 3KB | 2.5KB |
| au-table | < 5KB | 4KB |
| au-toast | < 2KB | 1.5KB |

---

## 6. PrimeNG Wrapper Strategy

Mientras no tengamos reemplazo nativo, usar wrappers que expongan API unificada:

```typescript
// shared/prime-wrappers/p-table-wrapper.component.ts
// Expone API de au-table pero usa p-table internamente
// Cuando esté listo au-table, se cambia el import sin tocar consumidores
```

Pero el objetivo es **eliminar wrappers** y reemplazar directamente en módulos.

---

## 7. Design Token Bridge

```scss
// _component-tokens.scss
// Puente entre tokens de diseño y variables internas de PrimeNG

// Eliminar progresivamente conforme reemplazamos componentes
.p-component {
  --p-button-primary-background: var(--brand);
  --p-button-primary-hover-background: var(--brand-600);
  --p-button-primary-active-background: var(--brand-700);
  --p-button-primary-border-color: var(--brand);

  --p-inputtext-background: var(--surface-card);
  --p-inputtext-border-color: var(--surface-border);
  --p-inputtext-hover-border-color: var(--brand-300);

  --p-datatable-header-background: transparent;
  --p-datatable-row-hover-background: var(--surface-hover);
  --p-datatable-row-striped-background: var(--surface-ground);
}
```
