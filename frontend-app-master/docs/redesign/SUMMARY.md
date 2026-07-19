# AURON Redesign — Document Index

> 12 documentos estratégicos que definen el rediseño completo del frontend.

---

## Core Strategy

| # | Documento | Propósito |
|---|-----------|-----------|
| 00 | [AUDITORIA](00_AUDITORIA.md) | UX/UI audit con 15 problemas, 7 principios de Medina Labs, decisiones estratégicas |
| 01 | [DESIGN_SYSTEM](01_DESIGN_SYSTEM.md) | Sistema de diseño: tokens, colores, tipografía, spacing, componentes, reemplazo PrimeNG |
| 02 | [MOTION_SYSTEM](02_MOTION_SYSTEM.md) | Animaciones, page transitions, count-up, micro-interactions, skeleton loaders |
| 03 | [COMPONENT_LIBRARY](03_COMPONENT_LIBRARY.md) | Catálogo de componentes au-*, 3 capas, estándar, CSS architecture, bundle targets |
| 04 | [LAYOUT_SYSTEM](04_LAYOUT_SYSTEM.md) | Shell, sidebar, topbar, module header, responsive breakpoints |
| 05 | [DASHBOARD_BLUEPRINT](05_DASHBOARD_BLUEPRINT.md) | Dashboard hero, KPIs, onboarding checklist, widgets, signals |
| 06 | [RESPONSIVE](06_RESPONSIVE.md) | 6 breakpoints, patrones mobile-first por módulo, touch targets |
| 07 | [ACCESSIBILITY](07_ACCESSIBILITY.md) | WCAG AA, contrast ratios, focus, keyboard shortcuts, reduced motion |
| 08 | [FRONTEND_ARCHITECTURE](08_FRONTEND_ARCHITECTURE.md) | Angular 20 standalone, signals, zoneless, SSR, loading strategy |
| 09 | [PERFORMANCE](09_PERFORMANCE.md) | Lighthouse 100 target, bundle optimization, @defer, checklist |
| 10 | [MIGRATION_PLAN](10_MIGRATION_PLAN.md) | 10 sprints, un cambio visible por sprint, impacto y riesgos |
| 11 | [NAVIGATION_SYSTEM](11_NAVIGATION_SYSTEM.md) | Sidebar final, command palette ⌘K, topbar, breadcrumbs, shortcuts, onboarding tour |
| 12 | [THEME_SYSTEM](12_THEME_SYSTEM.md) | Light/dark tokens, color customization por tenant, Tailwind 4 @theme |

---

## Implementation Order

```
Sprint 1:  Tokens + Layout shell      (12_THEME + 04_LAYOUT)
Sprint 2:  Botones + Cards + Icons    (03_COMPONENT — layer 1-2)
Sprint 3:  Dialog + Toast + Empty      (03_COMPONENT — layer 2)
Sprint 4:  Table + Pagination          (03_COMPONENT — layer 3)
Sprint 5:  Input + Select + Forms      (03_COMPONENT — layer 2)
Sprint 6:  Dashboard + Charts          (05_DASHBOARD)
Sprint 7:  POS redesign                (06_RESPONSIVE + 03_COMPONENT)
Sprint 8:  Calendar + Appointments     (06_RESPONSIVE)
Sprint 9:  Reports + Admin             (03_COMPONENT + 06_RESPONSIVE)
Sprint 10: Performance + Accesibilidad (09_PERFORMANCE + 07_ACCESSIBILITY)
```

Cross-cutting: Navigation system (11) y architecture (08) se aplican gradualmente desde Sprint 1.

---

## Principios rectores

1. Un cambio visible por sprint
2. Cada componente debe justificar su existencia
3. No mezclar refactors con features
4. Build limpio obligatorio antes de avanzar
5. Mobile-first en cada componente nuevo
6. WCAG AA no es opcional
7. Documentar decisiones en PROJECT_STATE.md
