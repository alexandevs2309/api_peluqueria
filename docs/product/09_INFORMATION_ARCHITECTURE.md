# Information Architecture — AURON Suite

> *Cómo se organiza la información, cómo navega el usuario, cómo encuentra lo que necesita.*

---

## Filosofía de navegación

La navegación de AURON debe ser **predecible, mínima y contextual**.

**Predecible:** El usuario sabe dónde está y cómo llegar a cualquier sección en máximo 2 clics.

**Mínima:** No más de 5-7 secciones principales en la navegación global. Todo lo demás es contexto.

**Contextual:** La navegación debe adaptarse al rol del usuario (profesional, dueño, administrador). No mostrar al profesional secciones que solo el dueño necesita.

---

## Estructura global

### Rutas principales

```
/                          → Landing page
/auth/*                    → Autenticación (login, registro, recuperación)
/agendar/:subdomain        → Booking público

/* App autenticada (dueño/manager)
    /dashboard              → Resumen del día
    /appointments           → Agenda de citas
    /pos                    → Punto de venta
    /clients                → Clientes
    /employees              → Empleados
    /services               → Servicios
    /products               → Productos e inventario
    /reports                → Reportes
    /settings               → Configuración del negocio

/* App autenticada (profesional)
    /dashboard              → Mi día
    /appointments           → Mi agenda
    /pos                    → POS (solo cobrar)
    /clients                → Mis clientes
    /profile                → Mi perfil y comisiones

/* Admin (superadmin)
    /admin/dashboard        → Métricas globales
    /admin/tenants          → Negocios
    /admin/users            → Usuarios
    /admin/plans            → Planes
    /admin/settings         → Configuración global
```

### Secciones principales (sidebar)

El sidebar del usuario autenticado debe tener:

1. **Dashboard** (icono: dashboard) — El resumen del día
2. **Agenda** (icono: calendario) — Gestión de citas
3. **POS** (icono: cobrar) — Cobro de servicios
4. **Clientes** (icono: cliente) — Gestión de clientes
5. **Equipo** (icono: empleado) — Empleados (solo visible para dueño/manager)
6. **Servicios** (icono: tijera) — Servicios ofrecidos
7. **Reportes** (icono: reporte) — Reportes y estadísticas

**Configuración** y **Perfil** van en el menú del usuario (topbar derecha), no en la navegación principal.

**Productos** y **Promociones** son secciones secundarias accesibles desde el dashboard o configuración.

---

## Principios de organización

### 1. Lo más usado, más accesible

Las secciones que el usuario usa todos los días (POS, Agenda, Dashboard) deben estar siempre visibles en la navegación principal.

Las secciones de uso semanal (Clientes, Empleados, Servicios) están visibles pero con menor jerarquía visual.

Las secciones de uso mensual (Reportes, Configuración) están a un clic adicional.

### 2. La información se organiza por tarea, no por entidad

**Mal:** Separar "Crear cliente", "Editar cliente", "Ver historial del cliente" en distintas pantallas.
**Bien:** Una ficha de cliente que permite ver información, editar y ver historial en un solo lugar.

**Mal:** POS con 30 botones y 12 diálogos.
**Bien:** POS con flujo lineal: seleccionar servicio → cobrar → confirmar.

### 3. La profundidad máxima es 3 niveles

```
Nivel 1: /pos                  (pantalla principal)
Nivel 2: /pos/venta/:id        (detalle de venta)
Nivel 3: /pos/venta/:id/ticket (ticket de venta)
```

No permitir más de 3 niveles de anidación. Si se necesita más, la arquitectura está mal.

### 4. El contexto se mantiene

Si el usuario está en POS y abre el detalle de una venta, al cerrar vuelve al POS exactamente donde estaba (mismos filtros, misma búsqueda, mismo scroll).

Nunca reiniciar el estado de una pantalla al volver a ella.

---

## Patrones de navegación

### Sidebar (principal)

- Siempre visible en desktop. Colapsable en tablet.
- En móvil, overlay que se abre con el menú hamburguesa.
- Icono + label en cada item.
- La sección activa debe ser claramente identificable (fondo terracota suave + icono terracota).
- Sin sub-menés anidados en la navegación principal. Usar tabs dentro de la página para sub-secciones.

### Topbar (utilidades)

- Logo + nombre del negocio (click → dashboard).
- Búsqueda global (Cmd+K).
- Selector de sucursal (si aplica).
- Notificaciones (badge con count).
- Avatar del usuario (click → menú: perfil, configuración, cerrar sesión).
- Toggle de tema.

### Migas de pan (breadcrumb)

- Presentes en páginas anidadas (detalle de cliente, detalle de venta).
- Formato: "Clientes / María García"
- El primer nivel es clickeable para volver a la lista.

### Enlaces contextuales

- Desde una cita en el dashboard → click → abre la agenda en el día/hora de esa cita.
- Desde un cliente en el POS → click → abre la ficha completa del cliente.
- Desde el nombre de un empleado en una venta → ver su perfil.
- Nunca forzar al usuario a buscar información que ya está viendo.

---

## Búsqueda global

La búsqueda (Cmd+K) debe buscar en:

1. **Clientes** (por nombre, teléfono, email)
2. **Servicios** (por nombre)
3. **Productos** (por nombre, código de barras)
4. **Empleados** (por nombre)
5. **Citas** (por fecha, cliente, empleado)
6. **Pantallas** (por nombre de sección)

Resultados agrupados por categoría. Preview del resultado antes de seleccionar.

---

## Responsive IA

### Desktop (>1024px)
- Sidebar completa visible.
- Contenido principal con todo el ancho disponible.
- POS two-column (catálogo + carrito) lado a lado.

### Tablet (768px - 1024px)
- Sidebar colapsable (iconos sin labels).
- POS cambia a layout vertical con tabs (catálogo / carrito).
- Dashboard simplificado (2 columnas en lugar de 3-4).

### Móvil (<768px)
- Sin sidebar. Menú hamburguesa.
- POS: layout vertical. Tab para catálogo/carrito.
- Dashboard: una columna. Solo métricas esenciales.
- Tablas se convierten en cards apilables.
- Botones de acción principal flotantes (FAB) si aplica.
