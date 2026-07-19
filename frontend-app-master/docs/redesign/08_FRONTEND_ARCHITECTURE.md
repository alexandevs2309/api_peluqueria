# Frontend Architecture 2.0

> Principio: Angular 20 standalone, signals como estado reactivo, zoneless, SSR opcional.

---

## 1. Stack decidido

| Capa | Tecnología | Estado |
|------|-----------|--------|
| Framework | Angular 20 standalone | ✅ Actual |
| Change detection | Signals + zoneless (progresivo) | 🔄 Migrando |
| SSR | Angular SSR con hydration | 🟡 Opcional |
| CSS | Tailwind 4 + SCSS modules | ✅ Actual |
| State | Signals + computed (RxJs solo para HTTP) | 🔄 Migrando |
| Components | AURON Component Library (au-*) | 🔄 Reemplazando PrimeNG |
| Icons | SVG inline + Bootstrap Icons | ✅ Actual |
| Charts | ng2-charts | ✅ Mantener |

---

## 2. Estructura de directorios

```
src/app/
├── core/
│   ├── services/          # Business logic (Toast, Theme, Locale, Date, Chat, Auth)
│   ├── guards/            # AuthGuard, TrialGuard, FeatureGuard
│   ├── interceptors/      # ErrorInterceptor, AuthInterceptor, LoggingInterceptor
│   ├── utils/             # formatCurrency, formatDate, debounce, http-error-message
│   └── models/            # TypeScript interfaces (User, Tenant, Appointment, ...)
├── pages/
│   ├── auth/              # Login, Register, Onboarding
│   ├── client/            # Dashboard, POS, Citas, Clientes, Productos, Servicios, ...
│   └── admin/             # Tenants, Users, Plans, System config
├── shared/components/     # AURON Component Library (au-btn, au-card, au-table...)
├── layout/                # AppLayout, Sidebar, Topbar, Footer
├── app.config.ts          # App-wide providers
└── app.routes.ts          # Routes array
```

---

## 3. Pattern de componente standalone

```typescript
@Component({
  selector: 'au-btn',
  standalone: true,
  imports: [NgClass, AuIcon],
  template: `
    @if (loading()) {
      <span class="au-btn__spinner"></span>
    } @else if (icon()) {
      <au-icon [name]="icon()" class="au-btn__icon" />
    }
    <span class="au-btn__text"><ng-content /></span>
  `,
})
export class AuBtn {
  readonly variant = input<'primary' | 'secondary' | 'ghost'>('primary');
  readonly size = input<'sm' | 'md' | 'lg'>('md');
  readonly icon = input<string>();
  readonly loading = input(false);
}
```

Reglas:
- Usar `input()` y `output()` signals-based
- Template con `@if/@for` en vez de `*ngIf/*ngFor`
- No usar `ngOnInit` si se puede usar `computed` o `effect`
- No usar `ngModel` — usar `[value]` + `(input)` o `(change)`
- `ChangeDetectionStrategy.OnPush` por defecto

---

## 4. Estado global con signals

```typescript
// shared/store/ui.store.ts
export const uiStore = {
  sidebarOpen: signal(false),
  theme: signal<'light' | 'dark'>('light'),
  selectedBranch: signal<Branch | null>(null),
  toasts: signal<Toast[]>([]),
  loading: signal<Set<string>>(new Set()),
};

// Acciones
export const toggleSidebar = () => uiStore.sidebarOpen.update(v => !v);
export const showToast = (t: Toast) => uiStore.toasts.update(v => [...v, t]);
export const dismissToast = (id: string) => uiStore.toasts.update(v => v.filter(t => t.id !== id));
```

Ventajas: sin NgRx, sin boilerplate, tree-shakeable, tipado fuerte.

---

## 5. Migración de RxJs a signals

| Caso | Antes (RxJs) | Después (Signals) |
|------|-------------|-------------------|
| Estado local | `BehaviorSubject` + `async pipe` | `signal()` + `computed()` |
| HTTP call | `pipe(map(), catchError())` | `toSignal(http.get(...))` |
| Loading | `Subject<boolean>` | `signal(false)` |
| Filter/Sort | `combineLatest` + `pipe(map())` | `computed()` |
| Debounced input | `Subject.pipe(debounceTime)` | `effect()` + `setTimeout` |

No eliminar RxJs por completo — mantener para:
- WebSockets
- `combineLatest` entre múltiples HTTP calls
- `switchMap` para búsqueda con cancelación

---

## 6. Zoneless strategy

Migración progresiva:

1. Components nuevos: usar solo signals, sin Zone.js dependencies
2. Components existentes: mantener `ChangeDetectionStrategy.OnPush`
3. Cuando todos los templates usen signals: remover `zone.js` del polyfill
4. Último paso: cambiar `provideZoneChangeDetection` por `provideExperimentalZonelessChangeDetection`

Riesgos conocidos:
- PrimeNG components no son zoneless-compatibles
- `NgModel` no funciona sin zone
- `setTimeout`/`setInterval` no detectan cambios sin zone
- Solución: mantener zone.js como fallback hasta reemplazar PrimeNG

---

## 7. SSR / Hydration

```
Implementar en fase 3 o más tarde.
Prioridad: performance de primera carga.
```

Beneficios:
- Primer paint < 1s
- SEO para landing pública
- `@defer` para lazy loading de módulos pesados (POS, charts)

No implementar ahora porque:
- PrimeNG no soporta SSR completo
- La app es private (requiere login)
- El bundle actual ya es rápido con lazy loading

---

## 8. Loading strategy

```typescript
// shared/utils/loading.ts
export class LoadingService {
  private readonly loaders = signal<Map<string, boolean>>(new Map());

  readonly isLoading = computed(() =>
    Array.from(this.loaders().values()).some(v => v)
  );

  start(key: string) {
    this.loaders.update(m => { m.set(key, true); return m; });
  }

  stop(key: string) {
    this.loaders.update(m => { m.set(key, false); return m; });
  }
}
```

Orden de carga visual:
1. Shell layout (inmediato) — sidebar skeleton + topbar
2. Module header (200ms) — breadcrumb + title + actions skeleton
3. Content (500ms) — tabla o cards skeleton
4. Charts (1000ms+) — defer hasta que todo lo demás esté listo
