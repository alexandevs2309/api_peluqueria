# AURON Layout System 2.0

> Principio: el layout debe ser invisible. El usuario no piensa en "layout", piensa en su trabajo.

---

## 1. Shell Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Topbar (64px)  ┌─ Logo ─┬─ [Search] ─┬─ [Branch] ─[User] │
├─────────┬───────────────────────────────────────────────┤
│         │                                               │
│  Side   │  Main Content Area                            │
│  bar    │  ┌─────────────────────────────────────────┐  │
│  (260px)│  │  Module Header (opcional)                │  │
│         │  │  ┌─ Eyebrow ─┬─ Title ─┬─ Actions ─┐   │  │
│         │  ├─────────────────────────────────────────┤  │
│         │  │  Content                                │  │
│         │  │  (max-width: 1440px, centered)          │  │
│         │  │                                         │  │
│         │  └─────────────────────────────────────────┘  │
├─────────┴───────────────────────────────────────────────┤
│  Footer (opcional, solo landing)                         │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Sidebar Redesign

### Items reorganizados (YA IMPLEMENTADO)

```
ATENCIÓN Y CAJA
  📋 Citas
  💵 POS
  🧑 Clientes

CATÁLOGO Y HORARIOS
  💇 Servicios
  📦 Productos
  🕐 Horarios

ADMINISTRACIÓN
  📊 Reportes
  💰 Nómina
  👥 Empleados

CONFIGURACIÓN Y SOPORTE
  ⚙️ Configuración
  ℹ️ Soporte
```

### Mejoras técnicas
1. Reemplazar `p-menu` por `<au-menu>` cuando esté listo
2. Pasar a signals: `sidebarCollapsed`, `activeItem`
3. Animated collapso: 260px ↔ 64px (icon-only)
4. `prefers-contrast: more` → sidebar con bordes más definidos

---

## 3. Topbar Redesign

### Componentes
```
[Logo AURON] [Search / Cmd+K] [Branch Selector] [Notifications] [Avatar + Menu]
```

### Cambios:
1. **Search** → Command Palette (⌘K) — búsqueda global + acciones rápidas
2. **Branch Selector** → NO reload. Usar `BranchService.setActiveBranch()` signal
3. **Notifications** → Badge + dropdown con `p-scrollpanel`
4. **Avatar** → Menú desplegable con: Perfil, Configuración, Cerrar sesión

### Command Palette (⌘K)

```typescript
interface CommandPaletteAction {
  id: string;
  label: string;        // "Crear cita"
  description: string;  // "Agendar un nuevo cliente"
  icon: string;         // "calendar-plus"
  category: 'navigation' | 'actions' | 'clients' | 'sales';
  shortcut?: string;    // "G, then C"
  action: () => void;
  keywords: string[];   // ["agendar", "nueva", "cita", "cliente"]
}
```

---

## 4. Module Header Pattern

Cada módulo tiene un header consistente:

```html
<!-- Module: Citas -->
<div class="module-header">
  <div class="module-header__breadcrumb">
    <au-text variant="caption">Atención y Caja</au-text>
  </div>
  <div class="module-header__title-row">
    <div>
      <h1 class="module-header__eyebrow">Estado del día</h1>  <!-- Display -->
      <h2 class="module-header__title">Citas</h2>  <!-- UI -->
    </div>
    <div class="module-header__actions">
      <au-btn icon="calendar-plus" (click)="openNewAppointment()">Nueva cita</au-btn>
    </div>
  </div>
  <div class="module-header__stats" *ngIf="stats">
    <au-kpi-card label="Hoy" [value]="stats.today" />
    <au-kpi-card label="Pendientes" [value]="stats.pending" severity="warning" />
    <au-kpi-card label="Completadas" [value]="stats.completed" severity="success" />
  </div>
</div>
```

---

## 5. Responsive Breakpoints

```scss
// _breakpoints.scss
$breakpoints: (
  'sm':  640px,
  'md':  768px,
  'lg':  1024px,
  'xl':  1280px,
  '2xl': 1536px,
);

// Sidebar behavior
@mixin respond-to($bp) {
  @media (min-width: map-get($breakpoints, $bp)) { @content; }
}

.sidebar {
  @include respond-to('lg') {
    width: var(--sidebar-width);
  }

  @include respond-to('md') {
    // Mobile overlay
    position: fixed;
    z-index: 1000;
    transform: translateX(-100%);
    transition: transform var(--duration-normal) var(--ease-out);

    &.sidebar--open {
      transform: translateX(0);
    }
  }
}
```

---

## 6. Content Area

```css
.layout-main {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  padding: calc(var(--topbar-height) + var(--topbar-inset) * 2) var(--main-padding-x) 0;
  margin-left: var(--sidebar-width);
  transition:
    margin-left var(--duration-normal) var(--ease-out),
    padding var(--duration-normal) var(--ease-out);

  &__content {
    flex: 1;
    width: 100%;
    max-width: var(--content-max-width);
    margin: 0 auto;
    padding-top: var(--space-6);
  }

  &--sidebar-collapsed {
    margin-left: 64px;
  }
}
```

---

## 7. Loading Shell

```
Principio: la shell debe aparecer en <50ms.
No esperar datos para pintar el layout.
```

```html
<!-- app.component.html -->
<app-topbar />
<div class="layout-main" [class.layout-main--sidebar-collapsed]="sidebarCollapsed()">
  <app-sidebar />
  <main class="layout-main__content">
    @defer (on immediate) {
      <router-outlet />
    } @placeholder {
      <au-skeleton type="page" />
    }
  </main>
</div>
```
