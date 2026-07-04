# Design Principles — AURON Suite

> *Las reglas que gobiernan cada decisión visual y de interacción.*

---

## Principio 1: Identidad sobre tendencia

Cada elemento visual debe preguntarse: "¿Esto hace que AURON sea más reconocible?"

**Cuando dudes entre dos opciones:**
- La que refuerza la identidad de AURON → Gana.
- La que sigue una tendencia porque "se ve moderna" → Pierde.

**Esto significa:**
- No usamos glassmorphism. No porque esté mal, sino porque no es AURON.
- No usamos gradientes decorativos. Solo gradientes funcionales (profundidad, dirección).
- No usamos UI que se parezca a otra app, aunque esa app sea "exitosa".
- Creamos nuestro propio lenguaje visual, no adaptamos el de otros.

---

## Principio 2: Propósito sobre decoración

Nada existe sin una razón.

**Cada elemento debe responder:**
- ¿Qué información comunica?
- ¿Qué acción permite?
- ¿Qué decisión facilita?

**Si no puede responder, no debe existir:**
- Un borde decorativo sin función → Eliminar.
- Un icono que no ayuda a identificar → Reemplazar o eliminar.
- Una animación que no guía → Eliminar.
- Un color que no tiene significado → Usar un color neutro.

---

## Principio 3: Jerarquía sobre igualdad

No todo en la pantalla tiene la misma importancia. El diseño debe reflejar eso.

**Reglas de jerarquía:**
1. La acción principal debe ser la más visible (color, tamaño, posición).
2. La información secundaria debe ser visualmente más silenciosa.
3. La información terciaria debe poder ocultarse/expandirse.
4. Nunca dos elementos pueden competir por la misma atención.

**Cómo se logra:**
- Tamaño → Lo importante es más grande.
- Color → Lo importante usa colores de marca. Lo secundario usa neutros.
- Peso → Lo importante usa bold o semibold.
- Espacio → Lo importante tiene más espacio alrededor.
- Posición → Lo importante está arriba o a la izquierda.

---

## Principio 4: Velocidad sobre efectos

El usuario prefiere una pantalla simple que carga en 200ms a una pantalla bonita que carga en 2s.

**Esto no significa que el diseño debe ser feo. Significa que:**
- La performance es parte del diseño.
- Una animación que retrasa la interacción es una animación que sobra.
- Un skeleton contextual es mejor que un spinner.
- La carga progresiva es mejor que la carga en bloque.

---

## Principio 5: Calidez sobre frialdad

AURON no es un software corporativo. Es una herramienta para personas que trabajan con personas.

**Calidez no es:**
- Usar colores pastel.
- Poner emojis en todos lados.
- Tener un tono excesivamente casual.

**Calidez es:**
- Los neutros tienen temperatura (no grises fríos).
- Los errores suenan a conversación, no a sistema.
- Los estados vacíos tienen ilustraciones humanas, no iconos genéricos.
- El espaciado es generoso, no apretado.
- Las esquinas son suaves, no angulares.

---

## Principio 6: Consistencia sobre creatividad

La creatividad debe aplicarse donde importa (identidad, marca, experiencias clave). Donde no importa, la consistencia gana.

**Consistente en:**
- Posición de elementos similares en todas las pantallas.
- Comportamiento de componentes similares.
- Terminología en todo el producto.
- Patrones de interacción.

**Creativo en:**
- Ilustraciones de empty states.
- Animaciones de celebración.
- Copy de onboarding.
- Landing page.

---

## Principio 7: Dominio sobre genérico

Cada decisión debe reflejar que AURON es para barberías, salones y spas.

**Un botón no es "Submit". Es "Guardar servicio".**
**Una tabla no es una tabla. Es "Lista de clientes".**
**Un formulario no es un formulario. Es "Registrar un nuevo servicio".**

Esto aplica a:
- Terminología (usar "cobrar", no "procesar pago")
- Iconografía (usar tijeras, no engranajes)
- Flujos (el flujo de cobro en un salón no es el mismo que en una tienda)
- Métricas (mostrar "cortes hoy", no "transacciones")

---

## Principio 8: Confianza sobre control

El software debe confiar en el usuario. No pedir confirmación para todo. No bloquear acciones porque "podría cometer un error".

**Confiar es:**
- Acciones reversibles con undo, no con confirmación modal.
- Cambios que se guardan automáticamente.
- Drag & drop sin confirmación.
- Edición inline sin modo "editar".

**Controlar solo cuando:**
- La acción es irreversible (eliminar, pagar).
- La acción tiene consecuencias financieras.
- La acción afecta a otros usuarios.

---

## Principio 9: Progresivo sobre completo

No mostrar todo de golpe. Revelar información progresivamente a medida que el usuario la necesita.

**Esto significa:**
- Los formularios largos se parten en pasos.
- Las opciones avanzadas se ocultan tras un "Más opciones".
- Los filtros avanzados se muestran solo si se necesitan.
- El dashboard muestra primero lo esencial del día; los reportes semanales están a un clic.

---

## Principio 10: LATAM sobre global

Cuando haya conflicto entre una práctica global y una práctica local, la local gana.

**Ejemplos:**
- Aceptamos efectivo como método de pago principal, no tarjeta.
- El formato de fecha es DD/MM/YYYY.
- La moneda es RD$, no $.
- Los términos usan español LATAM, no español neutro.
- Los horarios consideran la jornada laboral LATAM (no 9-5).
