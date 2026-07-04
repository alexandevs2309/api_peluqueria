# Product Decision Framework — AURON Suite

> *Cómo tomar decisiones cuando hay dudas, conflictos o trade-offs.*

---

## Cuándo usar este framework

Cada vez que una decisión de producto, diseño o desarrollo genere duda, conflicto o desacuerdo, se debe aplicar este framework antes de decidir.

No es opcional. Es el proceso oficial de decisión.

---

## El árbol de decisión

### Paso 1: ¿Esto es esencial para el usuario?

Pregunta: ¿El usuario objetivo va a usar esto al menos una vez por semana?

- **Sí** → Continuar.
- **No** → ¿Esto es para onboarding o configuración inicial?
  - **Sí** → Continuar (una vez es suficiente si resuelve un problema importante).
  - **No** → **No implementar.** Si se usa menos de una vez por semana, no merece espacio cognitivo ni recursos de desarrollo.

### Paso 2: ¿Esto hace que AURON sea más reconocible?

Pregunta: ¿Una captura de pantalla de esta funcionalidad sería identificable como AURON sin el logotipo?

- **Sí** → Continuar.
- **No sé** → Iterar diseño hasta que la respuesta sea sí.
- **No** → ¿Hay una alternativa que sí lo haga?
  - **Sí** → Usar la alternativa.
  - **No** → **No implementar.** Si no fortalece la identidad, no merece estar en el producto.

### Paso 3: ¿Esto contradice algún Non-Negotiable?

Revisar los Non-Negotiables.

- **No** → Continuar.
- **Sí** → **No implementar.** Los Non-Negotiables son absolutos. No hay excepciones.

### Paso 4: ¿Esto es mejor que lo que reemplaza?

Pregunta: ¿Esta nueva versión es inequívocamente mejor que la anterior para el usuario?

- **Sí** → Continuar.
- **No** → **No implementar.** No cambiamos por cambiar. Cada cambio debe ser una mejora perceptible.
- **No estoy seguro** → Hacer test A/B o entrevista con 3 usuarios.

### Paso 5: ¿Esto es simple?

Pregunta: ¿Un usuario nuevo puede completar la tarea sin instrucciones?

- **Sí** → Continuar.
- **No** → Rediseñar hasta que sea sí. Si no se puede simplificar, **no implementar**.

### Paso 6: ¿Esto es rápido?

Pregunta: ¿La operación principal toma menos de 1 segundo?

- **Sí** → Continuar.
- **No** → ¿Puede hacerse en background?
  - **Sí** → Hacerlo en background con notificación al completar.
  - **No** → Optimizar hasta que sea < 1s o mostrar progreso claro.

### Paso 7: ¿Esto es accesible?

Pregunta: ¿Cumple con WCAG 2.1 AA?

- **Sí** → Continuar.
- **No** → **No implementar.** Arreglar accesibilidad primero.

### Paso 8: Decisión final

Si llegaste hasta aquí, la decisión es **SÍ implementar**.

Pero antes de empezar, documenta:

```
Decisión: [Sí / No]
Justificación: [Por qué sí o por qué no]
Framework aplicado por: [Nombre/Rol]
Fecha: [Fecha]
```

---

## El framework rápido (para decisiones pequeñas)

Cuando la decisión es pequeña (color de un botón, posición de un elemento, texto de un label) y no justifica pasar por las 8 preguntas, usa estas 3:

1. **¿Esto refuerza la identidad AURON?** (Sí/No)
2. **¿Esto mejora la experiencia del usuario?** (Sí/No)
3. **¿Esto contradice algún Non-Negotiable?** (Sí/No)

Si 1 y 2 son Sí, y 3 es No → Adelante.

En cualquier otro caso → Detenerse y preguntar.

---

## Matriz de trade-offs

Cuando dos valores chocan, esta matriz resuelve.

| Conflicto | Gana |
|-----------|------|
| Identidad vs Velocidad | **Identidad** |
| Usabilidad vs Consistencia | **Usabilidad** |
| Simplicidad vs Funcionalidad | **Simplicidad** |
| Performance vs Animación | **Performance** |
| Contexto local vs Estándar global | **Contexto local** |
| Accesibilidad vs Estética | **Accesibilidad** |
| Confianza del usuario vs Control del sistema | **Confianza del usuario** |
| Menos funciones vs Más funciones | **Menos funciones** |

---

## Cómo decir NO

Decir no a una funcionalidad es más importante que decir sí. Cada no protege la identidad del producto.

**Cómo decir no a una solicitud de feature:**

1. Escuchar y entender la necesidad real detrás de la solicitud.
2. Validar si la necesidad ya está cubierta por otra funcionalidad.
3. Si no está cubierta, evaluar contra el árbol de decisión.
4. Si la decisión es NO, explicar por qué (no solo decir no).
5. Ofrecer una alternativa si existe.

**Lenguaje para decir no:**

- "Entendemos la necesidad. Sin embargo, esta funcionalidad diluiría la identidad del producto."
- "Preferimos tener 10 funciones excelentes que 50 funciones regulares. Esta no pasó el corte de calidad."
- "Eso solucionaría un problema para algunos usuarios, pero añadiría complejidad para todos."
- "No es un no definitivo. Es un no por ahora. Si vemos que la necesidad se repite, lo reconsideramos."

---

## Cómo decir SÍ

Decir sí también tiene responsabilidad.

1. **Documentar la decisión.** Por qué se aprobó, qué problema resuelve.
2. **Definir el alcance.** Qué incluye, qué no incluye.
3. **Priorizar.** Si todo es prioridad, nada lo es.
4. **Medir.** Cómo saber si la funcionalidad fue exitosa.
5. **Iterar.** La primera versión no será perfecta. Planificar mejora continua.

---

## Checklist de decisión final

- [ ] Pasó el árbol de decisión completo.
- [ ] No contradice ningún Non-Negotiable.
- [ ] Fortalece la identidad de AURON.
- [ ] Es simple para el usuario.
- [ ] Es técnicamente viable.
- [ ] Es medible (sabremos si funciona).
- [ ] Tenemos capacidad para hacerlo bien.
- [ ] El equipo completo está de acuerdo.
