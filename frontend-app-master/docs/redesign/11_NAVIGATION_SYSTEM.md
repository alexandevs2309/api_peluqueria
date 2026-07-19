# Navigation System — Sidebar + Command Palette + Topbar

> Principio: navegación rápida, consistente, accesible. Sidebar para exploración, ⌘K para velocidad.

---

## 1. Sidebar — Estructura final

4 secciones compactas (aprobado en UI-001):

```
╔══════════════════════════════╗
║ Atencion y Caja              ║
║  📋 Agenda                   ║
║  🏪 POS                      ║
║  📊 Dashboard                ║
╠══════════════════════════════╣
║ Catalogo y Horarios          ║
║  👥 Clientes                 ║
║  💇 Servicios                ║
║  📦 Productos                ║
║  🕐 Horarios                 ║
╠══════════════════════════════╣
║ Administracion               ║
║  💰 Nomina                   ║
║  📈 Reportes                 ║
║  🏢 Sucursales               ║
║  🎯 Promociones              ║
╠══════════════════════════════╣
║ Configuracion y Soporte      ║
║  ⚙️ Configuracion            ║
║  ❓ Soporte                  ║
║  👤 Mi Perfil                ║
╚══════════════════════════════╝
```

---

## 2. Command Palette (⌘K)

### Comportamiento

- Abrir: `⌘K` o `Ctrl+K`
- Cerrar: `Escape`, click fuera, `⌘K` de nuevo
- Navegar: `↑` `↓` arrows
- Seleccionar: `Enter`
- Filtrado: fuzzy search por nombre de ruta y alias
- Animación: slide-down + backdrop blur

### Data source

```typescript
interface CommandItem {
  id: string;
  label: string;           // "Agenda"
  description?: string;    // "Ver y gestionar citas"
  icon?: string;           // "calendar"
  route: string;           // "/client/appointments"
  keywords: string[];      // ["citas", "turnos", "booking", "schedule"]
  shortcut?: string;       // "G then A"
  badge?: string;          // "5" — pending count
  section: string;         // "Navegacion", "Acciones", "Busqueda"
}
```

### Items incluidos

| Sección | Items |
|---------|-------|
| Navegacion | Todas las rutas del sidebar + auth routes |
| Acciones | Crear cita, Abrir caja, Nueva venta, Nuevo cliente |
| Busqueda | Clientes, productos, servicios (API search) |
| Recientes | Últimas 5 rutas visitadas (localStorage) |

---

## 3. Topbar — Diseño final

```
┌──────────────────────────────────────────────┐
│  ☰  AURON Suite  [⌘K Buscar...]   🏪 Sucursal ▼  🌙  🔔(3)  👤 Admin ▼ │
└──────────────────────────────────────────────┘
```

| Elemento | Descripción |
|----------|-------------|
| ☰ | Toggle sidebar (mobile: overlay, desktop: collapse) |
| AURON Suite | Logo + nombre app (link a dashboard) |
| ⌘K Buscar... | Search bar que abre command palette |
| 🏪 Sucursal ▼ | Branch selector (solo si multi-branch activo) |
| 🌙 | Theme toggle (light/dark) |
| 🔔(3) | Notifications badge + dropdown |
| 👤 Admin ▼ | User menu: Perfil, Configuracion, Cerrar sesion |

---

## 4. Breadcrumbs

```
Dashboard > Clientes > Juan Perez
```

- Se generan automáticamente desde `app.routes.ts` usando `data.breadcrumb`
- Primer elemento siempre es un link
- Último elemento es texto plano (no link)
- Mobile: solo mostrar último nivel + flecha atrás

---

## 5. Module Header Pattern

Cada módulo tiene un header estandarizado:

```
┌──────────────────────────────────────┐
│  🔙 Atras     Clientes     👥 128    │
│  Gestion de tus clientes y su historial │
│  [+ Nuevo cliente]  [📁 Exportar]  [🔍] │
└──────────────────────────────────────┘
```

Estructura:
1. Back button (solo en sub-rutas)
2. Module icon + title + count
3. Description (texto secundario)
4. Action bar (botones + filtros)

---

## 6. Keyboard shortcuts

| Atajo | Acción | Global? |
|-------|--------|---------|
| `⌘K` | Abrir command palette | ✅ |
| `⌘B` | Toggle sidebar | ✅ |
| `⌘N` | Nuevo (según contexto) | ✅ |
| `⌘D` | Ir a Dashboard | ✅ |
| `⌘P` | Ir a POS | ✅ |
| `⌘,` | Ir a Configuración | ✅ |
| `⌘S` | Guardar (formularios) | ❌ (contextual) |
| `Escape` | Cerrar dialog / palette | ✅ |
| `?` | Mostrar atajos | ✅ |
| `G then A` | Ir a Agenda | ✅ |
| `G then C` | Ir a Clientes | ✅ |
| `G then V` | Ir a Servicios | ✅ |

---

## 7. Mobile navigation

- Sidebar se convierte en bottom sheet (slide-up)
- Topbar se simplifica: solo logo + hamburger + notifications
- Branch selector en dropdown dentro del header
- Command palette full-screen en mobile

---

## 8. Tour onboarding

```
Primer login → Tour highlight de sidebar + command palette
```

Steps:
1. Sidebar: "Aqui encuentras todos los modulos" (highlight first section)
2. Command palette: "Presiona ⌘K para buscar cualquier cosa" (highlight search)
3. Notifications: "Aqui veras notificaciones de citas y pagos" (highlight bell)
4. Branch selector: "Cambia de sucursal aqui" (si multi-branch)
5. Primer módulo: "Empecemos con tu primer cliente" (auto-navegar a clientes)
