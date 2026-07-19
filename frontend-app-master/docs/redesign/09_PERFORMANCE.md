# Performance Targets

> Objetivo: Lighthouse 100 en desktop, CLS < 0.05, LCP < 2s, bundle < 300KB inicial.

---

## 1. Targets actuales vs deseados

| Métrica | Actual | Target | Herramienta |
|---------|--------|--------|-------------|
| FCP | < 2s | < 1.2s | Lighthouse |
| LCP | < 3s | < 2s | Lighthouse |
| TBT | < 300ms | < 100ms | Lighthouse |
| CLS | < 0.1 | < 0.05 | Lighthouse |
| Speed Index | < 3s | < 2s | Lighthouse |
| Bundle inicial | ~400KB | < 200KB | webpack-bundle-analyzer |
| Total JS | ~1.2MB | < 600KB | coverage report |
| Time to Interactive | < 3s | < 2s | Lighthouse |

---

## 2. Bundle optimization

### Estrategia principal: @defer on interaction

```typescript
// POS carga solo cuando el usuario hace click en la pestaña
@defer (on interaction) {
  <app-pos-system />
} @placeholder {
  <div class="pos-skeleton">...cargando POS...</div>
}
```

### Componentes candidatos a @defer

| Componente | Trigger | Impacto |
|------------|---------|---------|
| POS System | on interaction (tab click) | ~150KB |
| Charts (dashboard) | on viewport | ~80KB |
| Reports module | on interaction | ~200KB |
| FullCalendar | on viewport | ~100KB |
| Admin panel | on interaction | ~50KB |
| Edit dialogs | on interaction (button click) | ~30KB c/u |

### PrimeNG tree-shaking

```typescript
// app.config.ts — importar solo lo que se usa
export const appConfig: ApplicationConfig = {
  providers: [
    providePrimeNG({
      theme: { preset: Aura, options: { darkModeSelector: '.dark' } },
      ripple: true,
      inputStyle: 'filled',
    }),
    // Solo estos componentes globales:
    MessageService,
    ConfirmationService,
  ],
};
```

PrimeNG módulos que debemos eliminar primero (por peso):
1. `ChartModule` (sustituir por ng2-charts delgado)
2. `TableModule` (sustituir por au-table nativa)
3. `DialogModule` (sustituir por au-dialog)
4. `OverlayPanelModule` (sustituir por au-dropdown)

---

## 3. Image optimization

- Todas las imágenes en WebP con fallback PNG
- Lazy loading nativo: `<img loading="lazy">`
- Avatar images: max 80x80px, WebP
- Placeholder SVG generado inline (0KB extra)
- No importar imágenes grandes en JS/TS

---

## 4. Font loading

```html
<!-- index.html: preconnect + swap + subset -->
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
```

- Inter solo pesos 400, 500, 600, 700 (no 300, 800, 900)
- EB Garamond solo display (un peso, 700)
- `font-display: swap` en todas
- Variable fonts donde sea posible

---

## 5. CSS strategy

- Tailwind 4 purge elimina clases no usadas (build)
- SCSS module por componente (scoped)
- `@layer` para control de especificidad
- No usar `@import` — usar `@use`
- CSS crítico inline en `<head>` para FOUC prevention

---

## 6. Scripts de medición

```bash
# Lighthouse CI
npx lighthouse http://localhost:4200 --view

# Bundle analysis
npx ng build --stats-json && npx webpack-bundle-analyzer dist/frontend-app/stats.json

# Coverage
npx ng test --no-watch --code-coverage
```

---

## 7. Checklist de performance pre-deploy

- [ ] Lighthouse 95+ en desktop y mobile
- [ ] CLS < 0.05
- [ ] LCP < 2s
- [ ] Bundle inicial < 200KB JS
- [ ] No hay importaciones globales de PrimeNG
- [ ] `@defer` en POS, charts, admin, reports
- [ ] Imágenes lazy + WebP
- [ ] Font-display: swap
- [ ] No console.log en producción
- [ ] Source maps deshabilitados en producción
