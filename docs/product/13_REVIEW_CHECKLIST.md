# Review Checklist — AURON Suite

> *Lo que debe verificarse antes de que cualquier diseño, componente, pantalla o feature llegue a producción.*

---

## Cómo usar este checklist

Cada Pull Request, cada nuevo componente, cada pantalla rediseñada debe pasar por este checklist antes de ser aprobado.

Si algún ítem no aplica, se marca como N/A con una breve justificación. Si algún ítem falla, el cambio no se aprueba hasta que se corrija.

---

## Identidad y marca

- [ ] ¿El diseño es reconocible como AURON sin el logotipo?
- [ ] ¿Usa la paleta de colores definida (terracota, gold, coral, neutros cálidos)?
- [ ] ¿La tipografía display se usa solo donde corresponde (títulos de marca)?
- [ ] ¿Los iconos son del set AURON (no PrimeIcons genéricos)?
- [ ] ¿Los colores tienen un propósito semántico claro?
- [ ] ¿No hay tendencias visuales ajenas a AURON (glassmorphism, neumorphism, etc.)?
- [ ] ¿Las ilustraciones (si las hay) siguen el estilo AURON (escenas reales, paleta limitada)?

---

## UX y propósito

- [ ] ¿La pantalla responde una sola pregunta?
- [ ] ¿Cuál es la pregunta? (escribirla)
- [ ] ¿Se puede responder en 3 segundos?
- [ ] ¿La acción principal es la más visible?
- [ ] ¿Las acciones secundarias no compiten con la principal?
- [ ] ¿El estado del sistema es visible sin hacer clic?
- [ ] ¿La navegación es predecible (el usuario sabe dónde está y cómo volver)?
- [ ] ¿No hay información innecesaria en la pantalla?

---

## Estados

- [ ] **Estado inicial:** La pantalla se ve bien recién cargada.
- [ ] **Estado de carga:** Tiene skeleton contextual (no spinner genérico).
- [ ] **Estado vacío:** Tiene ilustración + texto + CTA (no "No records found").
- [ ] **Estado de error:** Muestra mensaje humano + acción de recuperación.
- [ ] **Estado offline:** Muestra indicador visible (si aplica).
- [ ] **Estado de éxito:** Muestra confirmación clara del resultado.
- [ ] **Bordes:** Funciona con datos mínimos, típicos y extremos.

---

## Responsive

- [ ] **Móvil (< 768px):** La pantalla es funcional. No hay scroll horizontal.
- [ ] **Tablet (768-1024px):** Layout adaptado. Sidebar colapsado si aplica.
- [ ] **Desktop (> 1024px):** Layout completo con espaciado generoso.
- [ ] **Zoom al 200%:** Sin pérdida de contenido o funcionalidad.
- [ ] **Touch targets:** Mínimo 44x44px en móvil/tablet.

---

## Accesibilidad (WCAG 2.1 AA)

- [ ] **Teclado:** Toda la funcionalidad es operable con teclado (Tab, Enter, Escape).
- [ ] **Skip link:** Hay "Saltar al contenido" como primer elemento enfocable.
- [ ] **Focus visible:** Todos los elementos interactivos tienen foco visible.
- [ ] **Focus trap:** Modales y sidebars atrapan el foco correctamente.
- [ ] **ARIA labels:** Todos los iconos funcionales tienen `aria-label`.
- [ ] **Form labels:** Todos los inputs tienen `<label>` asociado.
- [ ] **Error messages:** Los errores de formulario son claros y están asociados al campo.
- [ ] **Contraste:** Relación de contraste ≥ 4.5:1 para texto normal.
- [ ] **Reduced motion:** `prefers-reduced-motion` desactiva animaciones decorativas.
- [ ] **Screen reader:** El contenido es comprensible con VoiceOver/NVDA.
- [ ] **Color alone:** No se usa solo color para transmitir información.

---

## Copy

- [ ] **Humano:** El texto suena a persona real, no a sistema.
- [ ] **Dominio:** Usa terminología de barbería/salón/spa.
- [ ] **Botones:** Usan verbos de acción ("Cobrar", "Guardar", no "Aceptar").
- [ ] **Errores:** Explican qué pasó + qué hacer.
- [ ] **Empty states:** Tienen CTA (no son solo informativos).
- [ ] **Confirmaciones:** Solo para acciones destructivas o irreversibles.
- [ ] **Placeholders:** Son ejemplos útiles, no repiten el label.
- [ ] **No hay inglés:** Todo el texto visible está en español.
- [ ] **No hay códigos:** Sin "Error 500", "null", "undefined" visibles.

---

## Rendimiento y código

- [ ] **Bundle size:** No introduce dependencias pesadas innecesarias.
- [ ] **Lazy loading:** La pantalla se carga con lazy loading.
- [ ] **Images:** Las imágenes tienen width/height para evitar CLS.
- [ ] **Loading:** El skeleton aparece en < 100ms.
- [ ] **Tamaño del componente:** < 800 líneas. Si es mayor, justificar o dividir.
- [ ] **Estilos inline:** No hay `[style]` en el template (usar clases CSS).
- [ ] **Comentarios muertos:** No hay `// era:` o código comentado.
- [ ] **PrimeNG overrides:** Si usa PrimeNG, los overrides mantienen los atributos ARIA.
- [ ] **Console errors:** No hay errores en consola del navegador.
- [ ] **Tests:** Los componentes nuevos tienen tests (unitarios o de integración).

---

## Preguntas finales (deben responderse antes de aprobar)

1. **¿Por qué existe esta pantalla/componente/cambio?**
   - Respuesta: _________________________________

2. **¿Qué pregunta responde al usuario?**
   - Respuesta: _________________________________

3. **¿La experiencia es reconocible como AURON?**
   - Sí / No (si No, no aprobar)

4. **¿Qué haría un barbero/estilista con esto en su día a día?**
   - Respuesta: _________________________________

5. **¿Alguien mirando esta pantalla (sin logo) sabría que es AURON?**
   - Sí / No (si No, no aprobar)

6. **¿Esta feature contradice algún Non-Negotiable?**
   - Sí / No (si Sí, no aprobar)
