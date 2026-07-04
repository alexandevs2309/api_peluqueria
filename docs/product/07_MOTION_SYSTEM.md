# Motion System — AURON Suite

> *El movimiento comunica. Cada animación debe tener un propósito y una personalidad.*

---

## Filosofía del movimiento

El movimiento en AURON debe sentirse **orgánico, no mecánico**. Como un objeto con peso y fricción reales, no como un elemento digital que aparece y desaparece.

**Principios:**
1. **El movimiento guía la atención.** No decora. No distrae.
2. **El movimiento comunica jerarquía.** Lo que aparece primero es lo más importante.
3. **El movimiento respeta el tiempo del usuario.** Rápido, eficiente, sin esperas.
4. **El movimiento debe ser opcional.** `prefers-reduced-motion` debe desactivar todo movimiento no esencial.

---

## Timing

```css
--au-duration-instant:  0ms      /* Sin animación (reduced motion) */
--au-duration-fast:     150ms    /* Hovers, micro-interacciones */
--au-duration-normal:   250ms    /* Dropdowns, tooltips, toggles */
--au-duration-slow:     400ms    /* Modales, sidebars, transiciones */
--au-duration-xslow:    600ms    /* Hero, onboarding, celebraciones */
```

## Easing

```css
--au-ease-out:        cubic-bezier(0.16, 1, 0.3, 1)     /* Apariciones */
--au-ease-in:         cubic-bezier(0.4, 0, 0.68, 0.06)   /* Desapariciones */
--au-ease-in-out:     cubic-bezier(0.65, 0, 0.35, 1)     /* Transiciones entre estados */
--au-ease-spring:     cubic-bezier(0.34, 1.56, 0.64, 1)  /* Micro-interacciones con énfasis */
--au-ease-linear:     cubic-bezier(0, 0, 1, 1)           /* Progress bars, loading */
```

**Regla de easing:**
- Los elementos que **aparecen** deben salir de la nada con `ease-out` (rápido al inicio, suave al final).
- Los elementos que **desaparecen** deben hacerlo con `ease-in` (suave al inicio, rápido al final).
- Las **transiciones entre estados** usan `ease-in-out` (equilibrado).
- Los **elementos con peso** (gestos de arrastre, swipes) usan `spring`.

---

## Transiciones

### Page transitions

```css
/* Transición estándar entre páginas */
.pagina-entrando {
    opacity: 0;
    animation: au-fade-in var(--au-duration-slow) var(--au-ease-out) forwards;
}

@keyframes au-fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
}
```

Sin slide ni efectos complejos. Un cross-fade limpio. El contenido debe estar listo antes de que termine la transición.

### Modal transitions

```css
/* Modal apareciendo */
.modal-backdrop {
    opacity: 0;
    animation: au-fade-in var(--au-duration-fast) var(--au-ease-out) forwards;
}

.modal-content {
    opacity: 0;
    transform: scale(0.95) translateY(8px);
    animation: au-modal-enter var(--au-duration-slow) var(--au-ease-out) forwards;
}

@keyframes au-modal-enter {
    from {
        opacity: 0;
        transform: scale(0.95) translateY(8px);
    }
    to {
        opacity: 1;
        transform: scale(1) translateY(0);
    }
}
```

El modal entra desde abajo (como si emergiera de la pantalla). No desde arriba. El backdrop aparece primero, el contenido después (50-100ms de retraso).

### Sidebar/Panel transitions

```css
/* Panel deslizándose desde la derecha */
.panel-sidebar {
    transform: translateX(100%);
    transition: transform var(--au-duration-slow) var(--au-ease-out);
}

.panel-sidebar.is-open {
    transform: translateX(0);
}
```

Los paneles laterales se deslizan desde el borde correspondiente. La dirección debe tener sentido físico (el panel de notificaciones viene de la derecha, el menú del sidebar está a la izquierda).

### Dropdown transitions

```css
.dropdown {
    opacity: 0;
    transform: translateY(-4px);
    transition:
        opacity var(--au-duration-fast) var(--au-ease-out),
        transform var(--au-duration-fast) var(--au-ease-out);
}

.dropdown.is-open {
    opacity: 1;
    transform: translateY(0);
}
```

Los dropdowns aparecen con un pequeño desplazamiento hacia abajo que da sensación de "caída" natural. Rápido (150-200ms).

---

## Micro-interacciones

### Botones

```css
button {
    transition:
        background-color var(--au-duration-fast) var(--au-ease-out),
        transform var(--au-duration-fast) var(--au-ease-out),
        box-shadow var(--au-duration-fast) var(--au-ease-out);
}

button:hover {
    transform: translateY(-1px);
    box-shadow: var(--au-shadow-md);
}

button:active {
    transform: translateY(0);
    box-shadow: var(--au-shadow-sm);
}
```

- Hover: el botón se eleva 1px (como si respondiera al acercarse).
- Active: vuelve a su posición (como si presionaras un botón real).

### Cards

```css
.card {
    transition:
        transform var(--au-duration-normal) var(--au-ease-out),
        box-shadow var(--au-duration-normal) var(--au-ease-out);
}

.card:hover {
    transform: translateY(-2px);
    box-shadow: var(--au-shadow-lg);
}
```

### Toggles y switches

```css
.toggle-track {
    transition: background-color var(--au-duration-normal) var(--au-ease-out);
}

.toggle-thumb {
    transition: transform var(--au-duration-normal) var(--au-ease-spring);
}
```

El thumb (círculo) del toggle usa spring easing para dar sensación de "enganche" magnético.

### Badge count

```css
.badge-count {
    transition: transform var(--au-duration-fast) var(--au-ease-spring);
}

.badge-count.is-new {
    animation: au-badge-pop 300ms var(--au-ease-spring);
}

@keyframes au-badge-pop {
    0% { transform: scale(1); }
    50% { transform: scale(1.3); }
    100% { transform: scale(1); }
}
```

### Checkmark animado

```css
@keyframes au-checkmark {
    0% { stroke-dashoffset: 24; }
    100% { stroke-dashoffset: 0; }
}

.checkmark-path {
    stroke-dasharray: 24;
    animation: au-checkmark 300ms var(--au-ease-out) forwards;
    animation-delay: 100ms;
}
```

---

## Loading states

### Skeleton pulse

```css
.skeleton {
    background: linear-gradient(
        90deg,
        var(--au-neutral-100) 25%,
        var(--au-neutral-50) 50%,
        var(--au-neutral-100) 75%
    );
    background-size: 200% 100%;
    animation: au-skeleton-pulse 1500ms ease-in-out infinite;
}

@keyframes au-skeleton-pulse {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}
```

El skeleton debe reflejar la forma del contenido real (skeleton de tarjeta de cliente = forma de tarjeta de cliente).

### Progress bar

```css
.progress-bar-fill {
    transition: width var(--au-duration-normal) var(--au-ease-out);
    background-color: var(--au-terracotta);
}
```

La barra de progreso se mueve suavemente, sin saltos.

---

## Reduced motion

```css
@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }

    /* Mantener animaciones funcionales sin movimiento */
    .skeleton {
        animation: none;
        background: var(--au-neutral-100);
    }

    .progress-bar-fill {
        transition: none;
    }
}
```

Cuando el usuario prefiere reducir movimiento:
- Sin animaciones decorativas.
- Sin skeletons animados (fondo estático).
- Sin micro-interacciones (hover sin translateY).
- Las transiciones funcionales (abrir modal, toggle) ocurren instantáneamente.
- Las barras de progreso cambian sin animación.
