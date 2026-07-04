# Brand Identity — AURON Suite

> *Lo que el ojo ve, lo que la mente recuerda, lo que el corazón siente.*

---

## El sistema de color

### Paleta primaria — La tierra y el oficio

Nuestra paleta nace de los materiales del oficio: el cuero de la silla de barbería, el metal de las tijeras, la madera del piso del salón, el calor de la luz natural.

```css
--au-terracotta:     #C8674A  /* Color principal. Cálido, confiable, con carácter */
--au-terracotta-600: #B85A3E  /* Hover states */
--au-terracotta-700: #A04D34  /* Active states */
--au-terracotta-100: #FDF2EF  /* Fondos claros */

--au-gold:           #D4A84B  /* Acento de valor. Premium sin ser ostentoso */
--au-gold-600:       #C49A40  /* Hover */
--au-gold-700:       #B48A36  /* Active */
--au-gold-100:       #FFF8EB  /* Fondos */

--au-coral:          #E0586A  /* Energía, acción. Lo que hay que hacer AHORA */
--au-coral-600:      #D04858  /* Hover */
--au-coral-700:      #C04048  /* Active */
--au-coral-100:      #FFF0F2  /* Fondos */
```

### Paleta neutra — Cálida y natural

Nunca grises fríos. Nunca slate. Nuestros neutros tienen temperatura.

```css
--au-neutral-50:     #FAF8F6  /* Fondo de página */
--au-neutral-100:    #F2EFEC  /* Fondo de sección */
--au-neutral-200:    #E5E0DB  /* Bordes sutiles */
--au-neutral-300:    #D1CAC4  /* Bordes */
--au-neutral-400:    #B8B0A8  /* Texto placeholder */
--au-neutral-500:    #9C948C  /* Texto secundario */
--au-neutral-600:    #7A726A  /* Texto terciario */
--au-neutral-700:    #5C544C  /* Texto corporal */
--au-neutral-800:    #3A3530  /* Títulos */
--au-neutral-900:    #1E1B18  /* Texto principal. Casi negro, pero más cálido */
```

### Paleta de estado — Templada

```css
--au-success:        #4A8C5C  /* Verde templado. No neón */
--au-success-bg:     #F0F7F2  /* Fondo */
--au-warning:        #D4A84B  /* Amarillo (mismo que gold) */
--au-warning-bg:     #FFF8EB  /* Fondo */
--au-error:          #B84A4A  /* Rojo templado. No neón */
--au-error-bg:       #FDF0F0  /* Fondo */
--au-info:           #C8674A  /* Info usa terracota */
--au-info-bg:        #FDF2EF  /* Fondo */
```

### Dark mode — Carbón cálido

```css
--au-dark-bg:        #1A1816  /* Fondo de página */
--au-dark-surface:   #242120  /* Tarjetas */
--au-dark-elevated:  #2E2B28  /* Elementos elevados */
--au-dark-border:    #3A3530  /* Bordes */
--au-dark-text:      #E8E4E0  /* Texto principal */
--au-dark-text-sec:  #A09892  /* Texto secundario */
```

### Reglas de uso del color

1. **Terracota es el color AURON.** Si solo puedes usar un color, usa terracota. Botones primarios, links, iconos activos, headers.

2. **Gold es premium.** No abuses de él. Solo en badges de suscripción, métricas destacadas, estrellas, logros, y detalles de precio.

3. **Coral es acción urgente.** Se usa en: botón de cobrar, notificaciones importantes, alertas de tiempo crítico.

4. **Los neutros siempre tienen temperatura.** Prohibido usar grises fríos tipo `#6B7280`. Cada gris debe tener un matiz marrón/terracota.

5. **El blanco nunca es blanco puro.** El blanco de fondo es `#FAF8F6`. El blanco de tarjetas es `#FFFFFF` **pero** sobre fondo `#FAF8F6`. Esto da calidez sin que el usuario lo note conscientemente.

6. **Dark mode no es invertir colores.** Es rediseñar para oscuridad. Los fondos oscuros tienen temperatura cálida (carbón, no pizarra). El texto sobre oscuro tiene 2% de amarillo para calidez.

7. **El verde y rojo deben ser templados.** Prohibido usar verde neón (`#22C55E`) o rojo neón (`#EF4444`). Usar siempre versiones templadas.

---

## Tipografía

### Display — Para marca y grandes titulares

**Familia:** `DM Serif Display` o `Instrument Serif` o `EB Garamond`

Uso exclusivo para:
- Título de landing
- Bienvenida en dashboard ("Buenos días, Carlos")
- Números grandes de métricas
- Precios
- Citas destacadas
- Empty states

No usar para:
- Texto de interfaz
- Labels
- Tablas
- Formularios

Tamaños:
```css
--au-display-4xl: 3.5rem  (56px) — Hero landing
--au-display-3xl: 2.5rem  (40px) — Page titles
--au-display-2xl: 2rem    (32px) — Section headers
--au-display-xl:  1.5rem  (24px) — Card titles
--au-display-lg:  1.25rem (20px) — Small display
```

### UI — Para interfaz

**Familia:** `Inter` (por legibilidad y rendimiento)

Usos: todo texto de interfaz, formularios, tablas, etiquetas, botones, navegación.

Tamaños:
```css
--au-text-xs:    0.75rem   (12px) — Captions, badges
--au-text-sm:    0.8125rem (13px) — Labels
--au-text-base:  0.875rem  (14px) — Body
--au-text-lg:    1rem      (16px) — Body large
--au-text-xl:    1.125rem  (18px) — Subheaders
```

### Monospace — Para datos precisos

**Familia:** `JetBrains Mono`

Usos: códigos NCF, números de transacción, tiempo, valores numéricos en contexto técnico.

### Jerarquía tipográfica

```
Página: display-2xl → header-xl → text-base
Tarjeta: display-lg → text-base → text-sm
Modal: display-xl → text-base → text-sm
Formulario: header-xl → text-sm → text-base
```

---

## Logotipo

### Principios

- El logotipo debe funcionar en una línea (horizontal) y como icono (favicon)
- Debe contener un símbolo del oficio (tijera, navaja, peine) integrado en la marca
- Debe ser legible a 16px y a 200px
- Debe funcionar sobre terracota, sobre blanco y sobre fondo oscuro

### Variantes

- **Completo:** AURON Suite + símbolo
- **Abreviado:** AURON + símbolo
- **Icono:** Solo símbolo (para app, favicon, avatar)
- **Monograma:** "AS" estilizado (para espacios muy pequeños)

### Zona de resguardo

- Alrededor del logotipo completo: mínimo 24px
- Alrededor del icono: mínimo 12px
- Alrededor del monograma: mínimo 8px

### Usos incorrectos

- No cambiar el color del logotipo fuera de la paleta
- No poner el logotipo sobre fondos con poco contraste
- No rotar, deformar o distorsionar el logotipo
- No añadir efectos (sombras, gradientes, glow) al logotipo
- No usar el icono como decoración repetida

---

## Elementos visuales distintivos

### Esquinas y formas

- **Esquinas redondeadas generosas** en toda la interfaz (12px tarjetas, 8px inputs, 6px badges)
- **Formas orgánicas** solo en ilustraciones y elementos de marca. Nunca en UI funcional.
- **La silla de barbería** como forma de inspiración para ciertos contornos (no literal, sino la curva del respaldo).

### Material y textura

- **Micro-textura sutil** en fondos de página (no visible conscientemente, pero el ojo nota la diferencia contra blanco plano)
- **Sombras cálidas** (usar `rgba(30, 27, 24, opacity)` en lugar de `rgba(0, 0, 0, opacity)`)
- **Elevación limitada** a 3 niveles: superficie, elevada (cards), flotante (modales)

### Patrones

- **Rayas de barbero** (rojo, blanco, azul) solo en contexto de marca. No en UI. Es un cliché, pero manejado con sutileza puede ser un detalle de reconocimiento en momentos de celebración (pago exitoso, registro completado).
- **Líneas finas decorativas** solo en landing page y marketing. Nunca en interfaz de producto.

---

## Consistencia visual

1. **Todos los componentes de la misma familia.** No mezclar estilos. Si un botón usa terracota, todos los botones primarios usan terracota.

2. **Un elemento, un propósito.** No usar un color decorativo donde no cumple una función. No usar una sombra donde no hay elevación.

3. **La forma sigue la función.** La jerarquía visual debe reflejar la jerarquía de importancia. Lo más importante debe ser lo más visible.

4. **La repetición crea reconocimiento.** Los mismos colores, formas y tratamientos deben aparecer consistentemente en todo el producto.

5. **La variación debe tener razón de ser.** Si algo es diferente, debe haber una razón que el usuario pueda entender.
