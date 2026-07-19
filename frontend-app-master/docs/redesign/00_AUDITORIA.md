# AURON Suite 2.0 — Auditoría UX/UI

> Fecha: 2026-07-13
> Equipo: VP Product Design (Stripe) + Staff Designer (Linear) + Principal Designer (Vercel)

---

## 1. Problemas detectados

### 🔴 Críticos

| # | Problema | Impacto | Principio violado |
|---|----------|---------|-------------------|
| P1 | 442 líneas `!important` en `_platform.scss` remapeando colores de Tailwind | Cualquier nuevo componente Tailwind requiere override manual. Escala mal. | Mantenibilidad |
| P2 | Sistema de tokens duplicado: `--al-*` en `tokens.css` y `--brand-*`/`--gray-*` en `_palette.scss` | Componentes usan tokens distintos → inconsistencias visuales | Consistencia |
| P3 | Branch selector hace `window.location.reload()` | Pierde estado del carrito POS, sesión, cache local | UX Fluida |
| P4 | Dashboard tiene colores brand hardcodeados (`rgba(26,86,219,0.1)`) | No respeta custom branding del tenant | Personalización |
| P5 | Menú lateral no está i18n — strings hardcodeados en español | Rompe internacionalización | Accesibilidad global |

### 🟡 Medios

| # | Problema | Impacto |
|---|----------|---------|
| P6 | "Search bar" en topbar no es un command palette real — solo dropdown con links | Falsa expectativa de búsqueda |
| P7 | LayoutService `updatePrimaryColor()` tiene colores hardcodeados que no coinciden con `--brand` | Brand override roto |
| P8 | Footer siempre visible — ocupa espacio sin valor en páginas de gestión | Ruido visual |
| P9 | Sidebar fijo con 300px de ancho en contenido gestionable | Espacio desperdiciado en módulos densos (POS, citas) |
| P10 | Dark mode SOLO por toggle, sin respetar `prefers-color-scheme` | Accesibilidad |

### 🟢 Bajos

| # | Problema | Impacto |
|---|----------|---------|
| P11 | Sin animaciones de página (transiciones entre rutas) | Percepción de lentitud |
| P12 | Sin empty states ilustrados para la mayoría de módulos | Frustración en datos vacíos |
| P13 | Sin skeleton loaders en tablas (solo en dashboard) | Percepción de carga lenta |
| P14 | Diálogos de confirmación genéricos sin personalidad | Poca identidad de marca |
| P15 | Sin shortcut keys ni navegación por teclado | Accesibilidad |

---

## 2. Principios extraídos de Medina Labs

Basado en el dashboard referenciado, estos son los principios de UX que funcionan:

| Principio | Explicación | Cómo aplica a Auron |
|-----------|-------------|---------------------|
| **Espacio generoso** | El contenido respira. No hay elementos apretados. Whitespace es feature. | Aumentar padding de cards, reducir densidad de tablas, más gap entre widgets |
| **Progreso visible** | Checklist de onboarding con barra de progreso numérica (5/7, 71%). Reduce ansiedad del setup. | Implementar onboarding wizard persistente en dashboard |
| **Acción primaria destacada** | Link de reservas con botón "Copiar" en dashboard. La acción que genera ingresos es prominente. | Mover "Compartir link" al hero del dashboard. Priorizar acciones que generan revenue. |
| **Calidez contextual** | Saludo con hora del día ("Buenas tardes, Desarrollo") + fecha. Humaniza la interfaz. | Saludar por nombre + hora + rol. Pequeño detalle, gran impacto en pertenencia. |
| **Navegación mínima** | Sin categorías complejas. Items planos o agrupación mínima. Menos fricción cognitiva. | Simplificar sidebar: menos secciones, items más descriptivos. |
| **Tarjetas con border-radius grande** | Bordes muy redondeados (16-24px) dan sensación de app nativa, no web. | Aumentar border-radius global de 16px a 20-24px en contenedores principales. |
| **Color como herramienta, no decoración** | Colores usados para significado (estado, alerta, acción) no para decorar. | Revisar paleta semántica: cada color debe comunicar algo. |
| **Sin clutter de configuración** | No mezclar contenido con config. El dashboard solo muestra lo que importa hoy. | Dashboard actual tiene demasiada info. Simplificar a 3 bloques máximos. |

---

## 3. Decisiones estratégicas

### Eliminar
1. `_platform.scss` — reemplazar por tokens nativos de PrimeNG + Tailwind
2. `tokens.css` (sistema `--al-*`) — unificar todo en `_palette.scss`
3. Footer en páginas de gestión (mostrar solo en landing)
4. Branch selector con reload — migrar a señal de cambio de sucursal sin recarga
5. Colores brand hardcodeados en templates — migrar a `var(--brand)`

### Mantener
1. Sistema de 4 capas (palette → theme → bridge → components) — es correcto
2. Display typography con EB Garamond — es diferenciador
3. Warm color palette con neutros cálidos — alinea con identidad de marca
4. `color-mix()` para transparencias — moderno y limpio
5. Glassmorphism en elementos superpuestos (dialogs, activity panel)
6. `startViewTransition()` para dark mode — premium feel

### Crear
1. AURON Component Library — standalone, reemplazo progresivo de PrimeNG
2. Motion System — page transitions, number animations, skeleton avanzado
3. Command Palette (⌘K) — búsqueda global + acciones rápidas
4. Onboarding Checklist — wizard persistente en dashboard
5. Empty States ilustrados — SVG custom por módulo
6. Keyboard Navigation System — shortcuts globales
7. Zoneless Change Detection — Angular 20 sin zone.js

---

## 4. Referencias de calidad

Cada módulo rediseñado debe pasar esta prueba:

```
□ ¿Podría confundirse con un template genérico?
   → Si la respuesta es sí, no está listo.
□ ¿Comunica identidad de marca sin logos?
   → La paleta, tipografía y motion deben ser reconocibles.
□ ¿Funciona en modo claro Y oscuro?
   → No es "soporte" — debe brillar en ambos.
□ ¿La acción principal es obvia sin leer?
   → Un nuevo usuario debe saber qué hacer en <3 segundos.
□ ¿Hay whitespace o es información apretada?
   → Cada elemento debe tener espacio para respirar.
□ ¿Las animaciones tienen propósito o son decorativas?
   → Motion debe guiar, no distraer.
□ ¿Podría confundirse con PrimeNG por defecto?
   → Si se parece a PrimeNG, no es AURON.
```
