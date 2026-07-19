# AURON Accessibility Blueprint

> Principio: accesibilidad no es checklist. Es parte del diseño desde el primer wireframe.

---

## 1. WCAG Targets

| Nivel | Objetivo | Estado actual |
|-------|----------|---------------|
| WCAG 2.1 AA | **Mandatory** | Parcial |
| WCAG 2.1 AAA | Progresivo | No implementado |
| Section 508 | Compatible | Desconocido |

---

## 2. Color & Contrast

```css
/* Ratio target: 4.5:1 minimum (AA normal text) */
:root {
  --brand:         #1A56DB;   /* 4.6:1 on white ✅ */
  --text-primary:  #101828;   /* 15.4:1 on white ✅ */
  --text-secondary:#475467;   /* 7.1:1 on white ✅ */
  --text-tertiary: #98A2B3;   /* 3.2:1 on white ❌ — solo para metadatos */
  --text-disabled: #D0D5DD;   /* 2.1:1 on white ❌ — solo deshabilitado */
}

.app-dark {
  --text-primary:  #F0F2F5;   /* 14.1:1 on dark surface ✅ */
  --text-secondary:#8C93A4;   /* 6.5:1 on dark surface ✅ */
  --text-tertiary: #5A6276;   /* 4.2:1 on dark surface ✅ just barely */
}
```

### Reglas de color:
- `--text-tertiary` nunca debe usarse para contenido principal
- Badges y tags: fondo + texto con ratio ≥ 3:1 mínimo
- Links: `--brand` + underline en hover, no solo color
- Errores: `--danger` + icono, no solo color

---

## 3. Focus Management

```
Cada componente debe tener un focus ring visible.
El outline por defecto del browser NO se debe eliminar sin reemplazo.
```

```css
/* Focus ring token */
:root {
  --focus-ring: 0 0 0 3px rgba(26, 86, 219, 0.3);
}

/* Global focus styles */
*:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
  border-radius: var(--radius-xs);  /* Match adjacent element */
}

/* Dialog focus trap */
@Directive({
  selector: '[auFocusTrap]',
  standalone: true,
})
export class FocusTrapDirective implements AfterViewInit, OnDestroy {
  // Trap focus within element
  // Return focus to trigger on close
}
```

---

## 4. Keyboard Navigation

| Acción | Shortcut | Estado |
|--------|----------|--------|
| Command Palette | `⌘K` / `Ctrl+K` | Nuevo |
| Buscar en página | `⌘F` / `Ctrl+F` | Nativo |
| Navegar sidebar | `Tab` con focus visible | ✅ |
| Abrir/cerrar sidebar | `⌘B` / `Ctrl+B` | Nuevo |
| Crear cita rápida | `⌘N` / `Ctrl+N` | Nuevo |
| Ir a dashboard | `⌘D` / `Ctrl+D` | Nuevo |
| Ir a POS | `⌘P` / `Ctrl+P` | Nuevo |
| Cerrar diálogo | `Escape` | ✅ |
| Confirmar acción | `Enter` (en diálogos) | ✅ |
| Cancelar acción | `Escape` (en diálogos) | ✅ |
| Ayuda / shortcuts | `?` (en command palette) | Nuevo |

---

## 5. Screen Reader Support

### ARIA attributes por componente

```typescript
// Dialog
host: {
  '[role]': '"dialog"',
  '[attr.aria-modal]': '"true"',
  '[attr.aria-labelledby]': 'titleId',
  '[attr.aria-describedby]': 'descriptionId',
}

// Toast/Alert
host: {
  '[role]': '"alert"',
  '[attr.aria-live]': '"assertive"',
  '[attr.aria-atomic]': '"true"',
}

// Tabla
<au-table
  role="grid"
  [attr.aria-rowcount]="data.length"
  [attr.aria-colcount]="columns.length"
>
  <div role="row" *ngFor="let row of data">...</div>
</au-table>

// Status badges
<span role="status" aria-live="polite">
  <au-tag [severity]="status">Activo</au-tag>
</span>
```

### Live regions
- **Toasts**: region `assertive` — interrupción inmediata
- **Loading states**: region `polite` — "Cargando datos..." → "Listo"
- **Count updates**: region `polite` — "Ventas: $45,000 actualizado"

---

## 6. Reduced Motion

```typescript
// shared/services/reduced-motion.service.ts
@Injectable({ providedIn: 'root' })
export class ReducedMotionService {
  private readonly prefersReducedMotion = signal(false);

  constructor() {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    this.prefersReducedMotion.set(mq.matches);
    mq.addEventListener('change', (e) => this.prefersReducedMotion.set(e.matches));
  }

  get duration() {
    return this.prefersReducedMotion() ? 0 : 200;
  }

  get easing() {
    return this.prefersReducedMotion() ? 'linear' : 'cubic-bezier(0, 0, 0.2, 1)';
  }
}
```

```css
/* Global CSS */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 7. Accessibility Checklist

```
□ Todos los botones tienen aria-label si son icon-only
□ Todas las imágenes tienen alt text
□ Todos los formularios tienen labels asociados
□ Todos los diálogos tienen focus trap
□ Todos los toasts/errores tienen aria-live
□ Skip to main content link presente
□ Tab order es lógico (no tabindex > 0)
□ Sin cambios de contexto sin aviso
□ Sin parpadeos > 3Hz
□ Contraste de color verificado en modo claro y oscuro
□ Focus visible en todos los Interactive elements
□ Keyboard navigation completa en todos los módulos
□ Screen reader test en POS (flujo crítico)
□ Screen reader test en Citas (flujo crítico)
```
