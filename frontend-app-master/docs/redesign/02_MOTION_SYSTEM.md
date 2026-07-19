# AURON Motion System 2.0

> Principio: toda animación debe tener propósito — guiar atención, feedback de estado, transición entre contextos.

---

## 1. Filosofía

```
No motion es mejor que motion incorrecto.
Motion inconsistente crea la percepción de "app barata".
Cada transición debe responder a: ¿qué está sucediendo?
```

**Reglas:**
- Duración máxima: 300ms (excepto números animados: 500-800ms)
- Mínimo 3 transiciones por página como estándar
- `prefers-reduced-motion` debe respetarse estrictamente: 0ms, no animaciones decorativas
- No animar desplazamientos de layout (CLS)
- `transform` y `opacity` son las únicas propiedades animadas

---

## 2. Page Transitions

```typescript
// app.component.ts
@Component({
  template: `
    <div class="page-transition" [@pageTransition]="o.getRouteAnimation(outlet)">
      <router-outlet #outlet="outlet" />
    </div>
  `,
  animations: [
    trigger('pageTransition', [
      transition('* => *', [
        query(':enter', [
          style({ opacity: 0, transform: 'translateY(8px)' }),
          animate('200ms {{ease-out}}', style({ opacity: 1, transform: 'translateY(0)' })),
        ], { optional: true }),
      ]),
    ]),
  ],
})
```

**TIPOS DE TRANSICIÓN:**

| Transición | Cuándo usar | Duración | Easing |
|-----------|-------------|----------|--------|
| `fade-up` | Navegación entre páginas | 200ms | ease-out |
| `slide-right` | Abrir sidebar, panel lateral | 250ms | ease-out |
| `scale-in` | Diálogos, modales, dropdowns | 150ms | spring |
| `fade-in` | Toasts, notificaciones | 200ms | ease-out |
| `stagger` | Listas que aparecen (30-50ms por item) | 300ms total | ease-out |

---

## 3. Number Animation (CountUp)

```typescript
// Core building block, not a library
function animateNumber(
  el: HTMLElement,
  from: number,
  to: number,
  duration = 600,
  formatter = (n: number) => formatCurrency(n, 'DOP'),
) {
  const start = performance.now();

  const tick = (now: number) => {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    // easeOutExpo
    const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
    const current = from + (to - from) * eased;

    el.textContent = formatter(current);

    if (progress < 1) requestAnimationFrame(tick);
  };

  requestAnimationFrame(tick);
}
```

**Reglas:**
- Solo animar valores monetarios y contadores en dashboard
- NO animar en tablas (solo valor final)
- 600ms es el sweet spot para números
- Si `prefers-reduced-motion`, mostrar valor final inmediato

---

## 4. Micro-interactions

| Elemento | Evento | Animación | Duración |
|----------|--------|-----------|----------|
| Button | Hover | `translateY(-1px)` + shadow deepen | 150ms |
| Button | Active | `translateY(0)` + scale(0.98) | 75ms |
| Card | Hover | `translateY(-2px)` + shadow grow | 200ms |
| Table row | Hover | Background shift | 100ms |
| Sidebar link | Active | Left border + bg shift | 150ms |
| Toggle | Change | Knob slide + bg fade | 200ms |
| Dialog | Open | Scale in + fade backdrop | 200ms |
| Dialog | Close | Scale out + fade backdrop | 150ms |
| Toast | Enter | Slide from right + fade | 250ms |
| Toast | Exit | Fade + slide right | 200ms |
| Skeleton | Pulse | Opacity pulse 1.5s infinite | — |

---

## 5. Loading States

### Skeleton (ya implementado en dashboard)
```
Principio: el skeleton debe hacer match con la estructura real del contenido.
No usar bloques genéricos.
```

**Tipos:**
- `au-skeleton-text` — líneas de texto con widths variables
- `au-skeleton-card` — card con header + cuerpo
- `au-skeleton-table` — filas con celdas de anchor variables
- `au-skeleton-avatar` — círculo de avatar
- `au-skeleton-chart` — área de gráfico

### Progressive Loading
```
Principio: cargar primero lo visible, luego lo secundario.
```

1. Frame skeleton (inmediato)
2. Texto + números (primera carga de datos, 200ms)
3. Tablas y listados (segunda carga, 300-500ms)
4. Charts y gráficos (carga diferida, 500ms+)

---

## 6. Route Transition Map

| De | A | Transición | Notas |
|----|--|-----------|-------|
| Dashboard | Cualquier módulo | fade-up | — |
| Citas | Dashboard | fade-up | — |
| POS | Cualquiera | fade-up | Carrito permanece en store |
| Config | Cualquiera | fade-up | — |
| Login | Register | slide-right | — |
| Register | Onboarding | fade-up + confetti | Logro importante |
| Error | Cualquiera | fade-up | Con reparación |

---

## 7. Shared Animation Constants

```typescript
// shared/motion.constants.ts
export const MOTION = {
  durations: {
    instant: 0,
    fast: 100,
    normal: 200,
    slow: 300,
    slower: 500,
    number: 600,
    confetti: 1500,
  },
  easings: {
    linear: 'linear',
    out: 'cubic-bezier(0, 0, 0.2, 1)',
    in: 'cubic-bezier(0.4, 0, 1, 1)',
    inOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    spring: 'cubic-bezier(0.16, 1, 0.3, 1)',
    bounce: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
  },
  classes: {
    fadeIn: 'au-animate-fade-in',
    slideUp: 'au-animate-slide-up',
    scaleIn: 'au-animate-scale-in',
    stagger: 'au-animate-stagger',
  },
} as const;
```

---

## 8. CSS Animation Classes

```css
/* Global animation classes */
.au-animate-fade-in {
  animation: auFadeIn var(--duration-normal) var(--ease-out) both;
}

.au-animate-slide-up {
  animation: auSlideUp var(--duration-normal) var(--ease-out) both;
}

.au-animate-scale-in {
  animation: auScaleIn var(--duration-normal) var(--ease-spring) both;
}

.au-animate-stagger > * {
  animation: auSlideUp var(--duration-normal) var(--ease-out) both;
  animation-delay: calc(var(--stagger-index, 0) * 50ms);
}

@keyframes auFadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}

@keyframes auSlideUp {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes auScaleIn {
  from { opacity: 0; transform: scale(0.95); }
  to   { opacity: 1; transform: scale(1); }
}

@keyframes auSkeletonPulse {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.4; }
}
```
