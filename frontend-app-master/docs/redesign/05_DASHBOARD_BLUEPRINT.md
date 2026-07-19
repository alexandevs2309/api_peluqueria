# AURON Dashboard Blueprint 2.0

> Inspirado en el dashboard de Medina Labs (principios, no copia): acción primaria prominente, progreso visible, calidez contextual.

---

## 1. Dashboard Hero (NUEVO)

```
┌─────────────────────────────────────────────────────────┐
│  {☀️} Buenas tardes, Alexander               [Hoy, 13 Jul] │
│  Gerente · Sucursal Principal                           │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Compartí tu link de reservas                    │   │
│  │  auronsuite.com/reserva/mi-peluqueria            │   │
│  │  [🔗 Copiar link]  [📱 Compartir WhatsApp]       │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                   │
│  │$45K  │ │234   │ │89%   │ │$980  │                   │
│  │Ventas│ │Citas │ │Ocup. │ │Ticket│                   │
│  │  ↑12%│ │  ↑5% │ │  ↓2% │ │  ↑8% │                   │
│  └──────┘ └──────┘ └──────┘ └──────┘                   │
│                                                         │
│  ┌────────────────────┐ ┌────────────────────┐          │
│  │  📊 Ingresos       │ │  🗓️ Próximas       │          │
│  │  (chart semanal)   │ │  citas (5)         │          │
│  │                    │ │  • María - 3pm     │          │
│  │                    │ │  • Juan - 4:30pm   │          │
│  └────────────────────┘ └────────────────────┘          │
│                                                         │
│  [Onboarding: 5/7 pasos completos  █████░░  71%]        │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Componentes del dashboard

### Hero Section
```
Propósito: saludar, orientar, acción principal.
```

- **Saludo contextual**: "Buenos días/tardes/noches, [nombre]" con formato según hora local
- **Rol + sucursal**: texto secundario informativo
- **Share booking link**: card destacada (no banner) con link de reservas + botón copiar
- **Fecha**: formato "lunes, 13 de julio 2026"

### KPI Row
```
Propósito: el estado del negocio en 4 números.
```

- Ventas (hoy): con trend ↑↓
- Citas (hoy): con trend
- Ocupación (%): con trend
- Ticket promedio: con trend
- Cada KPI: número animado (countUp al cargar), icono SVG, tooltip con detalle

### Gráficos
- **Ingresos semanales**: área chart (últimos 7 días vs. semana anterior)
- **Próximas citas**: mini-list con avatar + nombre + hora + servicio

### Onboarding Checklist (NUEVO)
```
Propósito: guiar al usuario a completar configuración.
```

- Barra de progreso: "5/7 pasos completos"
- Lista de pasos con checkmark/actual/pendiente
- Cerrable (dismiss permanent)
- Pasos: Conectar WhatsApp, Configurar horarios, Agregar servicios, Invitar empleados, ...

---

## 3. Reglas de dashboard

1. **Máximo 3 bloques de contenido vertical**
   - Hero (información + acción)
   - KPIs (4 números)
   - Widget principal (chart o lista)

2. **No mezclar contenido con configuración**
   - La configuración está en /settings
   - En dashboard solo: estado, alertas, acción principal

3. **Onboarding visible solo para tenants con setup incompleto**
   - Checklist desaparece al completar todos los pasos
   - No molestar usuarios avanzados

4. **Cada KPI debe ser clickeable** → lleva al módulo correspondiente
   - Ventas → Reportes
   - Citas → Calendario
   - Ocupación → Horarios
   - Ticket → POS

---

## 4. Estado actual vs. objetivo

| Aspecto | Actual | Objetivo |
|---------|--------|----------|
| Acción principal | Navegación genérica | Compartir link de reservas |
| Saludo | "Dashboard" | "Buenas tardes, Alexander" |
| Onboarding | No existe | Checklist persistente |
| KPIs | Números estáticos | Números animados + trend |
| Charts | Solo ingresos | Ingresos + próximas citas |
| Config | En dashboard | En /settings |

---

## 5. Signals state

```typescript
interface DashboardState {
  greeting: string;
  userName: string;
  userRole: string;
  branchName: string;
  bookingLink: string;
  kpis: {
    revenue: { value: number; trend: number; label: string };
    appointments: { value: number; trend: number; label: string };
    occupancy: { value: number; trend: number; label: string };
    avgTicket: { value: number; trend: number; label: string };
  };
  upcomingAppointments: UpcomingAppointment[];
  onboarding: {
    totalSteps: number;
    completedSteps: number;
    steps: OnboardingStep[];
    dismissed: boolean;
  };
}
```
