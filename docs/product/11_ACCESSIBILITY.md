# Accessibility — AURON Suite

> *Un producto que no puede ser usado por todos es un producto incompleto.*

---

## Estándar

AURON debe cumplir **WCAG 2.1 Nivel AA** como mínimo en todo el producto.

Donde sea práctico, apuntamos a **AAA** (especialmente en contraste de texto, etiquetas de formulario, y navegación por teclado).

---

## Principios

### 1. Perceptible

La información debe ser presentada de forma que todos los usuarios puedan percibirla.

**Reglas:**
- Todo contenido no textual (iconos, imágenes, ilustraciones) debe tener un equivalente textual (`alt`, `aria-label`).
- Los iconos funcionales deben tener `aria-label`. Los iconos decorativos deben tener `aria-hidden="true"`.
- El color nunca debe ser el único medio para comunicar información. Acompañar siempre con icono, texto o patrón.
- El contraste de color debe cumplir 4.5:1 para texto normal y 3:1 para texto grande.
- Los medios temporales (animaciones, video) deben tener controles de pausa/stop.

### 2. Operable

Todos los componentes de la interfaz deben ser operables desde el teclado.

**Reglas:**
- Toda funcionalidad disponible con mouse debe ser disponible con teclado.
- El orden de tabulación debe seguir el orden visual (arriba → abajo, izquierda → derecha).
- El foco visible debe estar presente en todo elemento interactivo. Prohibido `outline: none` sin reemplazo.
- Las trampas de foco en modales y sidebars deben gestionarse correctamente (focus trap).
- Todas las páginas deben tener un "Saltar al contenido" (skip-to-content) como primer elemento enfocable.

### 3. Comprensible

La información y la operación de la interfaz deben ser comprensibles.

**Reglas:**
- Los labels de formulario deben estar asociados a sus inputs (`<label for="...">`).
- Los mensajes de error deben ser claros y específicos.
- Los cambios de estado deben ser anunciados por screen readers (`role="status"`, `aria-live`).
- El idioma de la página debe estar definido (`lang="es"` en el `<html>`).
- La navegación debe ser consistente en todo el producto.

### 4. Robusto

El contenido debe ser compatible con tecnologías de asistencia actuales y futuras.

**Reglas:**
- HTML semántico (`<nav>`, `<main>`, `<section>`, `<h1>`-`<h6>`, `<button>` para botones).
- Roles ARIA usados solo cuando HTML semántico no es suficiente.
- Las customizaciones de PrimeNG deben mantener y mejorar (nunca eliminar) los atributos ARIA por defecto.

---

## Implementaciones específicas

### Navegación por teclado

```html
<!-- Skip to content -->
<a href="#main-content" class="au-skip-link">Saltar al contenido principal</a>
<main id="main-content"><!-- contenido --></main>
```

```css
.au-skip-link {
    position: absolute;
    top: -100%;
    left: 8px;
    padding: 8px 16px;
    background: var(--au-terracotta);
    color: white;
    z-index: 10000;
    border-radius: 8px;
}

.au-skip-link:focus {
    top: 8px;
}
```

### Focus visible

```css
/* Custom focus ring, never outline: none without replacement */
*:focus-visible {
    outline: 2px solid var(--au-terracotta);
    outline-offset: 2px;
    border-radius: 4px;
}

/* Remove default focus for mouse users but keep for keyboard */
*:focus:not(:focus-visible) {
    outline: none;
}
```

### ARIA labels

```html
<!-- Icon button -->
<button aria-label="Buscar cliente" (click)="search()">
    <i class="icon-search" aria-hidden="true"></i>
</button>

<!-- Toggle -->
<button
    role="switch"
    [attr.aria-checked]="isEnabled"
    [attr.aria-label]="isEnabled ? 'POS abierto' : 'POS cerrado'"
    (click)="toggle()">
    <span class="toggle-track">
        <span class="toggle-thumb"></span>
    </span>
</button>

<!-- Live region for notifications -->
<div aria-live="polite" aria-atomic="true" class="sr-only">
    {{ notificationMessage }}
</div>
```

### Formularios

```html
<label for="client-name">Nombre del cliente</label>
<input
    id="client-name"
    type="text"
    [formControl]="nameControl"
    [attr.aria-invalid]="nameControl.invalid && nameControl.touched"
    [attr.aria-describedby]="nameControl.invalid ? 'client-name-error' : null"
    autocomplete="name"
/>

<div
    *ngIf="nameControl.invalid && nameControl.touched"
    id="client-name-error"
    role="alert"
    class="au-field-error">
    El nombre es obligatorio.
</div>
```

### Diálogos modales

```html
<div
    role="dialog"
    aria-modal="true"
    [attr.aria-label]="'Eliminar cliente'"
    (keydown.escape)="close()">
    <!-- Focus trap: al abrir, enfocar el primer elemento interactivo -->
    <!-- Al cerrar, devolver foco al elemento que abrió el modal -->
</div>
```

### Tablas

```html
<table role="grid" aria-label="Lista de clientes">
    <thead>
        <tr>
            <th scope="col">Nombre</th>
            <th scope="col">Teléfono</th>
            <th scope="col">Última visita</th>
        </tr>
    </thead>
    <tbody>
        <tr *ngFor="let client of clients">
            <td>{{ client.name }}</td>
            <td>{{ client.phone }}</td>
            <td>{{ client.lastVisit }}</td>
        </tr>
    </tbody>
</table>
```

---

## Color y contraste

### Relaciones de contraste mínimas

| Uso | Ratio | Ejemplo |
|-----|-------|---------|
| Texto normal (< 18px) | 4.5:1 | Texto terracota sobre blanco |
| Texto grande (≥ 18px bold, ≥ 24px regular) | 3:1 | Título display sobre fondo |
| Componentes UI (bordes, iconos funcionales) | 3:1 | Icono de búsqueda sobre fondo |
| Texto deshabilitado | 3:1 mínimo (ideal 4.5:1) | Label de input deshabilitado |
| Estados de foco | 3:1 contra el fondo | Outline de foco |

### No comunicar solo con color

```html
<!-- Mal: solo color -->
<span style="color: green;">Activo</span>
<span style="color: red;">Inactivo</span>

<!-- Bien: color + icono + texto -->
<span class="status status-active">
    <i class="icon-check-circle" aria-hidden="true"></i>
    Activo
</span>
<span class="status status-inactive">
    <i class="icon-x-circle" aria-hidden="true"></i>
    Inactivo
</span>
```

---

## Responsive y zoom

- La interfaz debe ser funcional con zoom del navegador hasta 200%.
- Sin pérdida de contenido o funcionalidad.
- Sin scroll horizontal forzado.
- Objetivos táctiles mínimos de 44x44px (WCAG 2.2).

---

## Testing de accesibilidad

Cada pantalla debe pasar antes de liberarse:

1. **Teclado:** Navegar toda la pantalla solo con Tab, Shift+Tab, Enter, Escape.
2. **Screen reader:** La pantalla debe ser comprensible solo con VoiceOver/NVDA.
3. **Zoom:** Funcional al 200%.
4. **Contraste:** Verificar con axe DevTools o WAVE.
5. **Reduced motion:** Verificar que no hay animaciones problemáticas.
6. **Formularios:** Todos los campos tienen label asociado, mensajes de error claros.
7. **Landmarks:** La página usa `<nav>`, `<main>`, `<aside>` correctamente.
8. **Headings:** Jerarquía correcta (`h1` → `h2` → `h3`) sin saltos.
