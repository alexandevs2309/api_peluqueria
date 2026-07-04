# Copywriting Guidelines — AURON Suite

> *La voz de AURON. Cómo hablamos, qué decimos, qué jamás decimos.*

---

## Nuestra voz

AURON habla como un **maestro barbero que también sabe de tecnología**. No como un manual de instrucciones. No como un chatbot. No como un documento legal.

**Características de nuestra voz:**

| Característica | Cómo se manifiesta |
|----------------|-------------------|
| **Humana** | Usamos contracciones, ritmo natural, palabras que se usan en la vida real. |
| **Respetuosa** | Tratamos al usuario de "usted" o "tú" según la región. Nunca somos condescendientes. |
| **Clara** | Oraciones cortas. Una idea por oración. Sin jerga técnica. |
| **Cálida** | Hay calidez en cada interacción. Los errores no suenan a sistema. |
| **Latina** | Usamos español real. "Vaina", "chévere", "bacano" son válidos en contexto apropiado. |
| **Confiable** | No hacemos promesas que no podemos cumplir. No exageramos. |

---

## Tono por contexto

| Contexto | Tono | Explicación |
|----------|------|-------------|
| **Bienvenida / Saludo** | Cálido, personal | "Buenos días, Carlos. Hoy tienes 5 citas." Usar el nombre del usuario. |
| **Acción exitosa** | Confirmatorio, sutil | Checkmark + resultado. Sin exceso de celebración para acciones triviales. |
| **Error recuperable** | Sereno, útil | "No pudimos guardar. ¿Quieres intentar de nuevo?" |
| **Error crítico** | Serio, tranquilizador | "Algo salió mal. Tus datos están seguros. Estamos trabajando en resolverlo." |
| **Empty state** | Alentador, proactivo | "Todavía no tienes clientes. Agrega tu primero." |
| **Confirmación destructiva** | Serio, claro | "¿Eliminar este servicio? Esta acción no se puede deshacer." |
| **Onboarding** | Guía, paciente | "Empecemos por el nombre de tu negocio. Puedes cambiarlo después." |
| **Procesando** | Tranquilizador | "Estamos guardando tus cambios." (con skeleton) |
| **Offline** | Informativo, tranquilizador | "Estás offline. Puedes seguir trabajando. Tus datos se sincronizarán cuando vuelvas." |

---

## Patrones de lenguaje

### Botones

Usar verbos de acción. No "Aceptar". No "OK". No "Enviar".

| ❌ Evitar | ✅ Usar |
|-----------|---------|
| Aceptar | Guardar, Continuar |
| OK | Entendido, Listo |
| Enviar | Registrar, Cobrar, Agendar |
| Cancelar | (mantener, es estándar) |
| Cerrar | (mantener, es estándar) |
| Submit | Cobrar, Guardar, Registrar |

### Mensajes de error

Nunca usar lenguaje técnico. Estructura: qué pasó + qué hacer.

| ❌ Nunca | ✅ Siempre |
|----------|-----------|
| "Error 500" | "Algo salió mal. Intenta de nuevo." |
| "Network error" | "Parece que perdiste conexión a internet." |
| "Validation failed" | "Revisa los campos en rojo." |
| "Authentication failed" | "El correo o la contraseña no son correctos." |
| "Session expired" | "Tu sesión terminó por seguridad. Inicia sesión de nuevo." |
| "Permission denied" | "No tienes acceso a esta sección." |

### Estados vacíos

Nunca "No data" o "No records". Estructura: qué falta + qué hacer.

| ❌ Nunca | ✅ Siempre |
|----------|-----------|
| "No appointments" | "Hoy no tienes citas agendadas. ¿Quieres agregar una?" |
| "No clients" | "Todavía no has registrado clientes. Agrega tu primer cliente." |
| "No sales" | "No hay ventas registradas hoy." |
| "No products" | "Tu inventario está vacío. Agrega tus primeros productos." |
| "No employees" | "No has agregado empleados. Invita a tu equipo." |

### Confirmaciones

Solo para acciones destructivas o irreversible. No para acciones cotidianas.

| Contexto | Texto |
|----------|-------|
| Eliminar cita | "¿Eliminar esta cita? Esta acción no se puede deshacer." + Botón "Eliminar" (rojo) |
| Cerrar caja | "Al cerrar la caja se registrará el arqueo. ¿Quieres continuar?" + Botón "Cerrar caja" |
| Cancelar suscripción | "Al cancelar tu suscripción perderás acceso a funciones premium al final del período actual." + Botón "Cancelar suscripción" |
| Eliminar cliente | "¿Eliminar a María García? Se perderá su historial de visitas." + Botón "Eliminar cliente" |

### Placeholders

Los placeholders no deben repetir el label. Deben dar un ejemplo o contexto adicional.

| ❌ Evitar | ✅ Usar |
|-----------|---------|
| Label: "Nombre" + Placeholder: "Nombre" | Label: "Nombre" + Placeholder: "Ej: María García" |
| Label: "Correo" + Placeholder: "Correo" | Label: "Correo" + Placeholder: "correo@ejemplo.com" |
| Label: "Precio" + Placeholder: "Precio" | Label: "Precio" + Placeholder: "Ej: 500" |

### Notificaciones

| Tipo | Formato |
|------|---------|
| Nueva cita | "María García — Corte de cabello — 3:00 PM" |
| Recordatorio | "Carlos Pérez en 15 minutos — Corte + Barba" |
| Venta completada | "Venta #1024 — 1,500 RD$" |
| Pago recibido | "Pago de 500 RD$ de Juan Díaz" |
| Cliente nuevo | "Pedro Martínez se registró como cliente" |
| Sistema | "Actualización completada. Nueva versión disponible." |

---

## Español LATAM

### Regionalismos (usar con moderación y contexto)

- RD: "vaina", "chévere", "qué lo qué", "tigueraje" (solo en copy casual)
- No usar modismos que no sean ampliamente entendidos en LATAM.
- En UI formal, mantener español neutro (pero cálido).
- En marketing y onboarding, permitir más personalidad regional.

### Tuteo vs voseo vs ustedeo

- Por defecto: **tuteo** (tú) para toda la interfaz. Es el más neutral en LATAM.
- Excepciones: mensajes de error serios, confirmaciones destructivas → "usted" para seriedad.

### Fechas, horas y números

- Fechas: DD/MM/YYYY. Escribir: "3 de julio de 2026".
- Horas: 3:00 PM. No 15:00 (a menos que el usuario configure 24h).
- Moneda: "1,500 RD$". El símbolo después del número.
- Números: separador de miles con coma, decimal con punto.
- Porcentajes: "15%". Sin espacio antes de %.
- Rangos: "de 9:00 AM a 6:00 PM".

---

## Lo que NUNCA debe aparecer en AURON

- "Error 404" → "Página no encontrada"
- "Error 500" → "Algo salió mal"
- "401 Unauthorized" → "No tienes acceso"
- "null" → (nunca mostrar null al usuario)
- "undefined" → (nunca mostrar undefined al usuario)
- "[object Object]" → (nunca)
- "Loading..." → Skeleton contextual
- "Processing..." → Skeleton + "Guardando cambios"
- "Please wait..." → Skeleton + tiempo estimado (si es largo)
- "Success!" → Checkmark + resultado concreto
- "Error!" → Descripción del error + acción
- Códigos de error HTTP en la interfaz
- Mensajes de debug
- Nombres de variables o funciones
- Stack traces
- JSON raw

---

## Checklist de copywriting

Antes de enviar cualquier texto a producción:

- [ ] ¿Suena a humano o a sistema?
- [ ] ¿Un profesional de la belleza entendería esto?
- [ ] ¿El tono es apropiado para el contexto?
- [ ] ¿No hay jerga técnica?
- [ ] ¿El mensaje de error da una solución?
- [ ] ¿El botón dice lo que hace?
- [ ] ¿El empty state alienta a la acción?
- [ ] ¿La confirmación es clara sobre lo que va a pasar?
- [ ] ¿No hay texto hardcodeado en inglés?
- [ ] ¿Los placeholders son útiles, no repetitivos?
