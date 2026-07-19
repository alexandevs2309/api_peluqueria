# AURON Responsive Blueprint

> Principio: responsive no es "versión mobile". Es la misma app, adaptada al contexto de uso.

---

## 1. Breakpoints

```scss
$breakpoints: (
  'xs':  480px,   // Teléfonos pequeños
  'sm':  640px,   // Teléfonos grandes
  'md':  768px,   // Tablets vertical
  'lg':  1024px,  // Tablets horizontal / desktop pequeño
  'xl':  1280px,  // Desktop
  '2xl': 1536px,  // Desktop grande
);

// Mobile-first: escribir estilos base para mobile, mejorar hacia arriba
@mixin up($bp) { @media (min-width: map-get($breakpoints, $bp)) { @content; } }
@mixin down($bp) { @media (max-width: map-get($breakpoints, $bp) - 1px) { @content; } }
```

---

## 2. Layout por módulo

### Sidebar

| Breakpoint | Comportamiento |
|-----------|---------------|
| < lg | Overlay (slide desde izquierda) con backdrop |
| ≥ lg | Fijo, 260px, visible siempre |

### POS

| Breakpoint | Comportamiento |
|-----------|---------------|
| < md | Single column: catálogo arriba, carrito abajo. FAB para toggle vista |
| ≥ md | Two column: catálogo left, carrito right |

### Citas (FullCalendar)

| Breakpoint | Vista inicial |
|-----------|---------------|
| < lg | `listWeek` — events en lista vertical |
| ≥ lg | `timeGridDay` o `timeGridWeek` — cuadrícula horaria |

### Tablas

| Breakpoint | Comportamiento |
|-----------|---------------|
| < md | Vista tarjetas (cards apiladas) en vez de tabla |
| ≥ md | Tabla normal con `responsiveLayout="scroll"` |

### Diálogos

| Breakpoint | Ancho |
|-----------|-------|
| < md | `--width: calc(100vw - 32px)` (full casi) |
| ≥ md | `--width: 480px` (normal) |
| ≥ xl | `--width: 560px` (cómodo) |

---

## 3. Mobile-first table pattern

```html
@if (viewportWidth() < 640) {
  <!-- Card view for mobile -->
  <div class="mobile-card-list">
    @for (item of items; track item.id) {
      <div class="mobile-card" (click)="edit(item)">
        <div class="mobile-card__header">
          <au-avatar [label]="item.name" />
          <span class="mobile-card__name">{{ item.name }}</span>
          <au-tag [severity]="item.status === 'active' ? 'success' : 'warn'">
            {{ item.status }}
          </au-tag>
        </div>
        <div class="mobile-card__body">
          <div class="mobile-card__row">
            <span class="label">Teléfono</span>
            <span>{{ item.phone }}</span>
          </div>
          <div class="mobile-card__row">
            <span class="label">Email</span>
            <span>{{ item.email }}</span>
          </div>
        </div>
      </div>
    }
  </div>
} @else {
  <!-- Desktop table -->
  <au-table [columns]="columns" [data]="items" />
}
```

---

## 4. Touch Targets

```
Todos los elementos interactivos deben tener mínimo 44×44px de touch target.
```

| Elemento | Mobile | Desktop |
|----------|--------|---------|
| Botones | min 48px height | min 36px height |
| Links en listas | 44px row height | 36px row height |
| Dropdown items | 44px height | 32px height |
| Switch track | 28×20px | 24×16px |
| Radio/Checkbox | 24×24px | 20×20px |

---

## 5. Responsive Dialog Pattern

```typescript
const dialogWidth = computed(() => {
  const vw = viewportWidth();
  if (vw < 640) return 'calc(100vw - 32px)';
  if (vw < 1024) return 'min(480px, calc(100vw - 64px))';
  return '480px';
});
```

---

## 6. Testing responsive

Checklist por módulo:

```
□ ¿Funciona en 375px (iPhone SE)?
□ ¿Funciona en 768px (iPad portrait)?
□ ¿Funciona en 1024px (iPad landscape)?
□ ¿Funciona en 1440px (desktop)?
□ ¿Los touch targets miden ≥ 44px en móvil?
□ ¿No hay scroll horizontal en ningún breakpoint?
□ ¿Los diálogos son usables en móvil (no ocupan 100% con padding 0)?
□ ¿El sidebar se cierra automáticamente al navegar en móvil?
□ ¿Las tablas se degradan a cards sin perder información?
□ ¿Los skeletons matching el layout responsive?
```
