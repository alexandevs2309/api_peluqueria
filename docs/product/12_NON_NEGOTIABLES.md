# Non-Negotiables — AURON Suite

> *Líneas rojas. Cosas que jamás haremos, aunque sean tendencia, aunque la competencia las tenga, aunque sean más baratas.*

---

## Diseño visual

1. **Jamás usaremos glassmorphism como tratamiento visual por defecto.**
   - No es AURON. Es una tendencia de 2021. No comunica nuestra identidad.

2. **Jamás usaremos gradientes decorativos sin función.**
   - Un gradiente debe tener una función: profundidad, dirección, énfasis. Si no tiene función, es ruido.

3. **Jamás usaremos azul corporativo (#2563EB o similar) como color principal.**
   - Ese azul no nos pertenece. Es el color de miles de startups. No queremos parecernos a ellas.

4. **Jamás usaremos fondos blancos puros (#FFFFFF).**
   - El blanco AURON tiene temperatura: `#FAF8F6`. El blanco puro es frío y genérico.

5. **Jamás usaremos sombras negras.**
   - Las sombras deben usar `rgba(30, 27, 24, opacity)` (warm-slate-900). Las sombras negras son frías y artificiales.

6. **Jamás redondearemos esquinas a 4px o menos.**
   - Nuestras esquinas son generosas (8px-16px). Reflejan calidez y accesibilidad.

7. **Jamás pondremos borde a una tarjeta si podemos usar sombra.**
   - Los bordes son para formularios y tablas. Las tarjetas usan sombras suaves.

8. **Jamás usaremos una textura o patrón que no tenga relación con el oficio.**
   - Sin formas abstractas. Sin geometrías sin significado. Cada textura debe contar una historia.

---

## UX e interacción

9. **Jamás pondremos un spinner genérico en lugar de un skeleton contextual.**
   - El usuario merece saber qué forma tiene lo que está cargando. Un spinner es vago y frustrante.

10. **Jamás diremos "No records found."**
    - Es frío, genérico y no ayuda. Siempre un empty state con ilustración y CTA.

11. **Jamás pediremos confirmación para acciones cotidianas.**
    - Solo para acciones destructivas o irreversibles. Confirmar todo es no confiar en el usuario.

12. **Jamás tendremos un formulario de más de 8 campos visibles sin partirlo en pasos.**
    - La carga cognitiva de un formulario largo mata la conversión y la paciencia.

13. **Jamás ocultaremos el estado de una operación.**
    - "¿Se guardó?" es una pregunta que el usuario nunca debe hacerse.

14. **Jamás haremos que el usuario espere sin saber cuánto falta.**
    - Si tarda más de 3s, mostramos progreso. Si no podemos medirlo, mostramos un mensaje tranquilizador.

15. **Jamás usaremos animaciones que el usuario no pueda desactivar.**
    - `prefers-reduced-motion` no es opcional. Es obligatorio.

---

## Funcionalidad

16. **Jamás cobraremos comisión por cita.**
    - No somos un marketplace. Somos una herramienta. El dueño del salón paga por el software, no por sus clientes.

17. **Jamás ocultaremos el precio.**
    - Los precios son claros, sin asteriscos, sin "desde", sin cargos ocultos.

18. **Jamás venderemos los datos de los clientes del salón.**
    - Los clientes son del dueño del salón, no nuestros. No hacemos nada con sus datos sin su permiso explícito.

19. **Jamás haremos que el dueño del salón dependa de nosotros para comunicarse con sus clientes.**
    - WhatsApp, email y teléfono son del dueño. No los secuestramos. Si decide irse, se lleva sus contactos.

20. **Jamás forzaremos al usuario a usar un flujo que no se adapta a su negocio.**
    - ¿El salón no usa productos? Ocultamos inventario. ¿No tiene empleados? Ocultamos gestión de equipo. El software se adapta al negocio, no al revés.

---

## Técnico

21. **Jamás usaremos una librería de UI que imponga su identidad sobre la nuestra.**
    - PrimeNG es una herramienta, no un destino. La personalización no es opcional, es obligatoria.

22. **Jamás tendremos componentes con más de 800 líneas.**
    - Si un componente supera 800 líneas, merece ser dividido. No hay excepciones.

23. **Jamás tendremos estilos inline en los templates.**
    - `[style]="..."` es deuda de diseño. Las clases CSS son el estándar.

24. **Jamás dejaremos código comentado en SCSS/HTML/TS.**
    - `// era:` y cualquier otro comentario de desarrollo debe eliminarse antes de commit.

25. **Jamás ignoraremos la accesibilidad por velocidad de desarrollo.**
    - Una feature inaccesible no es una feature completa. No se libera.

---

## Marca

26. **Jamás usaremos iconos genéricos donde exista un icono del oficio.**
    - Si existe una tijera, un peine o una navaja, usamos esa. No un engranaje, no un ajuste.

27. **Jamás pondremos "Iniciar sesión" cuando podemos decir "Entrar a tu negocio".**
    - El lenguaje genérico diluye la identidad. Cada palabra cuenta.

28. **Jamás copiaremos el diseño de un competidor, aunque sea exitoso.**
    - Podemos inspirarnos en la calidad, no en la apariencia. No queremos parecernos a nadie.

29. **Jamás haremos un cambio visual sin actualizar la documentación de identidad.**
    - Si el color cambia, el documento cambia. Si el componente cambia, el documento cambia. No hay cambios silenciosos.

30. **Jamás aprobaremos un diseño que podría pertenecer a otro producto.**
    - La prueba definitiva: si le sacamos el logo y podría ser de otra app, el diseño no es AURON. Se rechaza.
