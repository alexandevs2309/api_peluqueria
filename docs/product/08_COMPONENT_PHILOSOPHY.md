# Component Philosophy — AURON Suite

> *No es una librería de componentes. Es una filosofía de construcción.*

---

## Qué es un componente AURON

Un componente AURON no es un elemento de UI reutilizable.

Un componente AURON es **una decisión de diseño empaquetada**.

Cada componente encapsula:
- Un propósito claro (¿qué problema resuelve?)
- Un comportamiento definido (¿cómo se comporta?)
- Un lenguaje visual (¿cómo se ve?)
- Una personalidad (¿cómo se siente?)
- Un estándar de calidad (¿qué pruebas debe pasar?)

---

## Principios de diseño de componentes

### 1. Un componente, una responsabilidad

Cada componente debe hacer una cosa y hacerla bien.

**Bien:** Un `Button` que tiene variantes (primario, secundario, outline) pero siempre es un botón.
**Mal:** Un `Button` que a veces es un link, a veces un dropdown, a veces un toggle.

### 2. Compuesto, no mágico

Los componentes complejos deben construirse componiendo componentes simples, no creando monolitos.

**Bien:** `Dialog = Backdrop + Panel + Header + Content + Footer`
**Mal:** `Dialog` de 500 líneas con 20 props booleanas.

### 3. Inteligente por defecto, flexible cuando se necesita

El componente debe funcionar con cero configuración. Las opciones avanzadas deben ser explícitas.

**Bien:** `<Button label="Guardar" />` funciona. `<Button label="Guardar" icon="check" severity="primary" />` personaliza.
**Mal:** `<Button label="Guardar" variant="primary" size="md" iconPosition="left" type="submit" />` para hacer lo básico.

### 4. Estado visible

Cada componente debe tener estados definidos y visibles:
- **Default:** El estado normal.
- **Hover:** El cursor está encima.
- **Active/Focus:** El usuario interactúa.
- **Disabled:** No disponible (con razón visible).
- **Loading:** Procesando una acción.
- **Error:** Algo salió mal.
- **Empty:** Sin datos que mostrar (para componentes de contenido).

### 5. Sin deuda de diseño

Nunca posponer una decisión de diseño en un componente. Si un componente se necesita pero no está definido, el estándar es: no usarlo hasta que esté definido, no "improvisar con estilos inline".

---

## La jerarquía de componentes

### Nivel 1: Atoms (fundación)

Elementos básicos que no pueden descomponerse más.

```
Button, Input, Select, Checkbox, Toggle,
Avatar, Badge, Tag, Icon, Spinner, Divider
```

**Reglas:**
- Sin dependencias de negocio.
- Sin estilos contextuales.
- Máximo 3 variantes.

### Nivel 2: Molecules (combinaciones)

Combinaciones de atoms que forman una unidad funcional.

```
InputGroup (Label + Input + Error),
Card (Header + Content + Footer),
SearchBar (Input + Icon + Dropdown),
DatePicker (Input + Calendar),
Dropdown (Trigger + Menu + Item),
Pagination (Buttons + Text)
```

**Reglas:**
- Pueden tener lógica de comportamiento.
- No deben conocer el dominio de negocio.
- Deben ser reutilizables entre contextos.

### Nivel 3: Organisms (dominio)

Componentes específicos del dominio de AURON.

```
ClientCard (Avatar + Name + Info + Actions),
ServiceCard (Icon + Name + Price + Duration),
SaleTicket (Items + Totals + Payment),
AppointmentCard (Time + Client + Service + Status),
MetricCard (Label + Value + Trend),
CashRegister (Status + Amount + Actions)
```

**Reglas:**
- Conocen el dominio (hablan de clientes, servicios, citas).
- Usan atoms y molecules internamente.
- Pueden tener datos mock para desarrollo.

### Nivel 4: Templates (layout)

Combinaciones de organisms que forman una página.

```
DashboardLayout, POSLayout, SettingsLayout,
AgendaLayout, ClientDetailLayout
```

**Reglas:**
- Definen posición y estructura, no contenido.
- Responsivos por defecto.
- Sin lógica de negocio.

### Nivel 5: Pages

Combinaciones de templates + organisms + molecules.

```
LoginPage, DashboardPage, POSPage,
AgendaPage, ClientsPage, SettingsPage
```

**Reglas:**
- Una página, una responsabilidad.
- Lógica mínima (delegada a servicios y stores).
- Estado de carga, vacío y error manejados.

---

## Anti-patrones de componentes

| Anti-patrón | Problema | Solución |
|-------------|----------|----------|
| **Props explosion** | Componente con 30+ inputs | Partir en componentes más pequeños |
| **Render conditionals** | Template con 15 `*ngIf` | Crear variantes explícitas del componente |
| **Style props** | `[style]="..."` en el template | Mover a CSS classes |
| **Logic in template** | Expresiones complejas en el HTML | Mover a computed/method |
| **God component** | Componente de 1000+ líneas | Dividir en subcomponentes |
| **Premature abstraction** | Componente que envuelve 1 uso | Esperar a que haya 3 usos |
| **Prop drilling** | Pasar props por 5 niveles | Usar context/state |

---

## El estándar de calidad

Cada componente debe pasar antes de ser merged:

1. **Estados:** Default, hover, active, disabled, loading, error, empty (según aplique).
2. **Responsive:** Funciona en 320px, 768px, 1024px, 1440px.
3. **Teclado:** Navegable y operable con teclado.
4. **Screen reader:** ARIA labels, roles, estados.
5. **Contraste:** WCAG AA en todas las variantes.
6. **Reduced motion:** No tiene animaciones problemáticas.
7. **Render:** No errors en consola.
8. **Unused:** No tiene CSS muerto.
