# Visual Language — AURON Suite

> *Iconografía, ilustraciones, fotografía, patrones, texturas — el vocabulario visual de AURON.*

---

## Iconografía

### Filosofía

Los iconos de AURON no son decoración. Son comunicación visual. Cada icono debe ser reconocible al instante sin necesidad de label.

### Principios

1. **Específicos del oficio.** Siempre que exista una herramienta real del oficio, usamos esa. Tijeras, navajas, peines, brochas, secadores, cortadoras. No iconos genéricos.

2. **Estilo único.** Outlined, 1.5px stroke, esquinas redondeadas, ángulos consistentes. Todos los iconos deben sentirse de la misma familia.

3. **Cada icono, un significado.** Un icono no puede tener dos significados en distintas partes del producto. Si necesitas dos significados, necesitas dos iconos.

4. **Sistema cerrado.** No más de 80 iconos en todo el producto. Si no está en el set, no se usa. Si realmente falta, el set se actualiza, pero no se añaden iconos sueltos.

### Iconos del oficio (el set AURON)

```
/* Herramientas de barbería */
tijera,         navaja,         peine,
cepillo,        secador,        cortadora,
brocha,         pinza,          alisadora,
rizadora,       maquinilla,     toalla,
capa,           espejo,         silla-barberia

/* Herramientas de salón/spa */
tijera-pelos,   peine-pelo,     cepillo-pelo,
pinza-pelo,     rulo,           gorra-calor,
mascarilla,     vela,           piedra-caliente,
paleta-maquillaje,              brocha-maquillaje

/* Herramientas de uñas */
corta-unas,     lima,           esmalte,
lámpara-uv,     removedor,      palito-naranja
```

### Iconos funcionales

```
/* Navegación y acción */
agregar,        eliminar,        editar,
buscar,         cerrar,          atras,
adelante,       menu,            mas,
menos,          check,           check-doble,

/* Estado */
alerta,         error,           exito,
info,           advertencia,     pendiente,
confirmado,     cancelado,       completado,
offline,        online,          sincronizando,

/* Negocio */
calendario,     reloj,           cliente,
empleado,       servicio,        producto,
inventario,     precio,          descuento,
pago,           efectivo,        tarjeta,
transferencia,  factura,         reporte,
dashboard,      configuracion,   perfil,
sucursal,       whatsapp,        email,
telefono,       direccion,       nota,

/* POS */
carrito,        caja,            abrir-caja,
cerrar-caja,    arqueo,          ticket,
cobrar,         escaner,         camara,
promocion,      fidelidad,       punto,

/* Personas */
usuario,        grupo,           estrella,
corona,         certificado,     medalla
```

### Reglas de uso

- Los iconos siempre deben tener un propósito comunicativo claro.
- No usar iconos como bullet points decorativos.
- Los iconos en botones deben estar a la izquierda del texto (excepto botones de "siguiente" donde van a la derecha).
- Tamaño base para iconos en UI: 16px (inline), 20px (botones), 24px (navegación), 32px (headers de sección).
- El color del icono debe tener contraste suficiente contra su fondo.

---

## Ilustraciones

### Filosofía

Las ilustraciones de AURON no son formas abstractas ni decoraciones geométricas. Son **escenas que cuentan historias**. Muestran personas reales en situaciones reales del oficio.

### Estilo

1. **Escenas, no vectores genéricos.** Un cliente en la silla. Un barbero trabajando. Un estilista mezclando color. Una spa preparando una sala.

2. **Paleta limitada.** 3-4 colores de la paleta de marca + neutros. Sin degradados complejos.

3. **Línea orgánica.** No vectores perfectos e impersonales. Trazo variado que da calidez.

4. **Propósito claro.** Toda ilustración debe:
   - Llenar un vacío (empty state)
   - Demostrar un concepto (landing, features)
   - Celebrar un estado (success, onboarding completado)
   - Guiar una acción (onboarding, tutorial)

### Dónde usar ilustraciones

- **Empty states** — No hay citas, no hay clientes, no hay ventas.
- **Landing page** — Hero, features, testimonios.
- **Pantallas de sistema** — 404, error, mantenimiento.
- **Onboarding** — Bienvenida, progreso, tutoriales.
- **Celebración** — Registro exitoso, primera venta, primer cliente.

### Dónde NO usar ilustraciones

- En la interfaz funcional del día a día (POS, agenda, dashboard).
- Donde ocupen espacio que podría usarse para información útil.
- Como decoración sin propósito.
- En formularios.

---

## Fotografía

### Estilo

- **Real, no de stock.** Fotos reales de barberías, salones y spas LATAM. Si no hay fotos reales disponibles, no usar fotos genéricas.

- **Cálida, no fría.** Luz natural cálida. Tonos dorados en la luz. Sin filtros azules o fríos.

- **Transformación, no solo proceso.** Mostrar antes/después. Mostrar el resultado, no solo el trabajo.

- **Ambiente, no solo producto.** Mostrar el local, la atmósfera, la experiencia completa.

### Tratamiento técnico

- Leve tono cálido en highlights.
- Contraste suave (no HDR).
- Saturación ligeramente reducida (no vibrante).
- Sin viñetas ni efectos dramáticos.
- Sin texto superpuesto sobre la imagen (excepto en hero de landing con gradiente).

### Dónde usar fotografía

- Landing page (hero, testimonios con foto real del dueño).
- Casos de éxito.
- Blog/tutoriales (fotos del proceso real).
- Perfiles de negocio (logo, foto del local).

### Dónde NO usar fotografía

- En UI funcional (tablas, formularios, listas).
- Donde una ilustración comunica mejor.
- Donde ralentice la carga de la pantalla.

---

## Patrones y texturas

### Fondo de página

- El fondo no debe ser blanco puro `#FFFFFF`. Usar `#FAF8F6`.
- Se puede aplicar una micro-textura CSS invisible (sin peso de imagen) que dé calidez táctil.

### Patrones decorativos

Solo en landing page y marketing. Nunca en producto.

- **Rayas de barbero** (rojo-blanco-azul) solo en contexto de celebración (checkout exitoso, registro completado). Con sutileza, no como patrón de fondo de página.

- **Líneas orgánicas** para separar secciones en landing. Trazo fino, opacidad baja.

### Tarjetas y superficies

- Borde sutil con `--au-neutral-200`.
- Sombra suave con `--au-shadow-sm`.
- Hover: elevar a `--au-shadow-md` con transición suave.
- Esquinas: `--au-radius-lg` (12px).
