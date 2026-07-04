# UX Principles — AURON Suite

> *Cómo se comporta el producto, cómo se siente, cómo respeta el tiempo y la atención del usuario.*

---

## Principio 1: Una pantalla, una pregunta

Cada pantalla debe responder una sola pregunta del usuario. Si una pantalla responde dos preguntas, está mal diseñada.

**Las preguntas que responde cada pantalla:**

| Pantalla | Pregunta que responde |
|----------|----------------------|
| Login | "¿Quién eres?" |
| Dashboard | "¿Cómo va tu día?" |
| Agenda | "¿Qué sigue?" |
| POS | "¿Qué vas a cobrar?" |
| Historial de ventas | "¿Cuánto vendiste?" |
| Ficha del cliente | "¿Quién es y qué prefiere?" |
| Perfil del empleado | "¿Cuánto trabajó y ganó?" |
| Reportes | "¿Cómo va el negocio?" |
| Configuración | "¿Cómo quieres que funcione?" |
| Onboarding | "¿Qué necesitas para empezar?" |

**Si el usuario no puede responder la pregunta en 3 segundos, la pantalla falla.**

---

## Principio 2: El estado siempre es visible

El usuario nunca debe preguntarse:
- "¿Se guardó?"
- "¿Estoy offline?"
- "¿Esta cita está confirmada?"
- "¿El POS está abierto?"
- "¿Hay alguien antes que yo?"

**Cómo se logra:**
- Indicadores de estado permanentes en el contexto apropiado.
- Offline badge visible en el POS cuando no hay conexión.
- Check verde en citas confirmadas.
- Badge "Abierto / Cerrado" en el POS siempre visible.
- Lista de espera visible para el profesional.

**Si el usuario tiene que hacer clic para saber el estado, el diseño falla.**

---

## Principio 3: La acción principal primero

En cada pantalla, la acción principal debe ser la más fácil de encontrar y ejecutar.

**Jerarquía de acciones:**
- **Primaria:** Una por pantalla. La razón de ser de la pantalla. Botón grande, color primario, posición prominente.
- **Secundaria:** Máximo 2-3 por pantalla. Acciones relacionadas pero no centrales. Botón outline o texto.
- **Terciaria:** Menú contextual, acciones avanzadas. Icono, texto pequeño o menú.

**Ejemplos:**
- POS → Primaria: "Cobrar". Secundarias: "Buscar cliente", "Agregar descuento".
- Agenda → Primaria: "Nueva cita". Secundarias: "Ver día/semana/mes".
- Clientes → Primaria: "Nuevo cliente". Secundarias: "Buscar", "Filtrar".

---

## Principio 4: La carga es parte de la experiencia

El estado de carga no es un accidente que hay que ocultar. Es parte del diseño.

**Reglas:**
- **< 100ms:** No mostrar nada. La respuesta es instantánea.
- **100ms - 300ms:** Mostrar feedback sutil (cambio de opacidad, skeleton instantáneo).
- **300ms - 1s:** Mostrar skeleton contextual con la forma del contenido real.
- **1s - 3s:** Skeleton + indicador de progreso (si se puede medir).
- **> 3s:** Permitir que el usuario siga navegando. Procesamiento en background con notificación al completar.

**Nunca usar:**
- Spinner genérico sin contexto.
- Pantalla en blanco mientras carga.
- "Cargando..." sin indicación de progreso.

---

## Principio 5: El error es una conversación, no una interrupción

Cuando algo sale mal, el usuario no debe sentirse castigado. Debe sentirse guiado.

**Estructura de un error:**
1. **Qué pasó** — en lenguaje humano, sin términos técnicos.
2. **Por qué pasó** — solo si ayuda a prevenir que vuelva a ocurrir.
3. **Qué puede hacer** — acción concreta y visible.

**Ejemplo:**
> ❌ "Error 500: Internal Server Error"
> ✅ "No pudimos guardar la venta. Parece que hay un problema con el servidor. No te preocupes, tu carrito está seguro. Puedes intentar de nuevo en unos segundos o continuar con otra cosa mientras se resuelve."

**Reglas:**
- Nunca mostrar códigos de error HTTP al usuario.
- Nunca usar lenguaje técnico ("null pointer", "exception", "timeout").
- Siempre ofrecer una acción de recuperación.
- Si no hay acción disponible, ofrecer contacto de soporte.

---

## Principio 6: Los formularios son conversaciones, no interrogatorios

Un formulario no es un cuestionario que el usuario debe completar. Es una conversación guiada.

**Cómo se logra:**
- **Preguntar solo lo necesario.** Si un campo puede inferirse, no preguntar.
- **Una cosa a la vez.** Formularios largos se parten en pasos lógicos.
- **Validación oportuna.** Validar después de que el usuario termina de escribir, no mientras escribe.
- **Contexto visible.** Mostrar por qué se pide cada información.
- **Guardado automático.** No perder datos si el usuario cierra la pantalla.

**Ejemplo vs anti-ejemplo:**
> ❌ Formulario de 20 campos en una página con "Guardar" al final.
> ✅ 3 pasos: (1) Datos del cliente, (2) Servicio y precio, (3) Confirmar.

---

## Principio 7: La navegación debe ser predecible

El usuario nunca debe perderse. Nunca debe preguntar "¿dónde estoy?" o "¿cómo vuelvo?".

**Reglas:**
- El breadcrumb (miga de pan) debe estar presente en pantallas anidadas.
- El botón "Atrás" debe funcionar como el usuario espera (como el back del navegador si es una página nueva, como "cerrar" si es un modal).
- Las secciones principales deben ser accesibles desde la navegación global en todo momento.
- El cambio entre secciones no debe ser desorientador (transiciones suaves, posición consistente de elementos).

---

## Principio 8: La accesibilidad no es opcional

AURON debe ser utilizable por:
- Personas con visión reducida (contraste suficiente, soporte de screen reader)
- Personas con movilidad reducida (navegación completa por teclado, objetivos táctiles grandes)
- Personas con daltonismo (no usar solo color para comunicar información)
- Personas mayores (texto legible, interacciones simples)
- Personas con baja alfabetización digital (interfaz intuitiva, lenguaje simple)

**WCAG 2.1 AA es el mínimo. AAA es el objetivo donde sea práctico.**

---

## Principio 9: La consistencia reduce la carga cognitiva

El usuario no debería aprender a usar cada pantalla desde cero.

**Consistente:**
- La misma acción siempre en la misma posición.
- El mismo icono siempre significa lo mismo.
- El mismo color siempre significa lo mismo.
- El mismo patrón de interacción para acciones similares.

**Inconsistente (prohibido):**
- "Guardar" a veces a la izquierda, a veces a la derecha.
- El icono de eliminar cambia entre papelera y cruz.
- El mismo tipo de formulario tiene distinto layout en distintas pantallas.

---

## Principio 10: El feedback es inmediato y claro

Cada acción del usuario debe tener una respuesta perceptible en menos de 50ms.

**Tipos de feedback:**
- **Visual inmediato:** El botón cambia de estado al hacer clic.
- **Visual de resultado:** Aparece un toast, badge o cambio en la interfaz.
- **Auditivo (opcional):** Sonido sutil para acciones importantes (cobro, error).
- **Táctil (móvil):** Vibración sutil en acciones clave.

**Regla:** Si el usuario hace clic y no pasa nada en 50ms, el software se siente roto.
