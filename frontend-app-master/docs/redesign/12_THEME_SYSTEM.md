# Theme System — Light + Dark + Color Customization

> Principio: dos modos nítidos, transición suave, color primario customizable desde admin.

---

## 1. Estructura de archivos

```
src/styles/
├── tokens.css               # CSS custom properties globales
├── tailwind.css             # Tailwind 4 @theme config
├── _palette.scss            # Paleta de colores (light + dark)
├── _prime-overrides.scss    # Puente PrimeNG → tokens
├── _components.scss         # Componentes reutilizables (glass, lift, etc)
├── _motion.scss             # Animaciones globales
└── tokens/
    ├── _color.scss          # Solo colores
    ├── _spacing.scss        # Solo espaciado
    ├── _typography.scss     # Solo tipografía
    └── _shadows.scss        # Solo sombras
```

---

## 2. Color tokens

```css
/* tokens.css — valores base (ni light ni dark) */
:root {
  /* Brand */
  --brand: #1A56DB;         /* Azul principal */
  --brand-50: #EFF6FF;
  --brand-100: #DBEAFE;
  --brand-200: #BFDBFE;
  --brand-300: #93C5FD;
  --brand-400: #60A5FA;
  --brand-500: #3B82F6;
  --brand-600: #2563EB;
  --brand-700: #1D4ED8;
  --brand-800: #1E40AF;
  --brand-900: #1E3A8A;

  /* Neutral */
  --gray-50: #F9FAFB;
  --gray-100: #F3F4F6;
  --gray-200: #E5E7EB;
  --gray-300: #D1D5DB;
  --gray-400: #9CA3AF;
  --gray-500: #6B7280;
  --gray-600: #4B5563;
  --gray-700: #374151;
  --gray-800: #1F2937;
  --gray-900: #111827;
  --gray-950: #030712;

  /* Semantic */
  --success: #10B981;
  --warning: #F59E0B;
  --danger: #EF4444;
  --info: #3B82F6;

  /* Accent */
  --accent: #8B5CF6;
}
```

---

## 3. Light theme

```css
[data-theme="light"], .light {
  /* Surfaces */
  --surface-ground: var(--gray-50);
  --surface-section: white;
  --surface-card: white;
  --surface-border: var(--gray-200);
  --surface-hover: var(--gray-100);

  /* Text */
  --text-primary: var(--gray-900);
  --text-secondary: var(--gray-500);
  --text-tertiary: var(--gray-400);
  --text-inverse: white;

  /* Shadows */
  --shadow-xs: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.1);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.07);
  --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
  --shadow-xl: 0 20px 25px rgba(0,0,0,0.1);
}
```

---

## 4. Dark theme

```css
[data-theme="dark"], .dark {
  /* Surfaces */
  --surface-ground: #0F172A;       /* slate-900 */
  --surface-section: #1E293B;      /* slate-800 */
  --surface-card: #1E293B;
  --surface-border: #334155;       /* slate-700 */
  --surface-hover: #334155;

  /* Text */
  --text-primary: #F8FAFC;         /* slate-50 */
  --text-secondary: #94A3B8;       /* slate-400 */
  --text-tertiary: #64748B;        /* slate-500 */
  --text-inverse: #0F172A;

  /* Shadows — más sutiles en dark */
  --shadow-xs: 0 1px 2px rgba(0,0,0,0.3);
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.4);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.4);
  --shadow-lg: 0 10px 15px rgba(0,0,0,0.5);
  --shadow-xl: 0 20px 25px rgba(0,0,0,0.5);
}
```

---

## 5. Color customization

Los tenants pueden cambiar el color primario desde admin (ya existe `updatePrimaryColor` en `LayoutService`).

```css
/* Cuando el admin cambia el color, se actualiza --brand via JS */
[data-brand="terracotta"] {
  --brand: #C8674A;
  --brand-50: #FDF2EF;
  --brand-100: #FBE4DD;
  --brand-200: #F5C9BB;
  --brand-300: #EFAD99;
  --brand-400: #E89177;
  --brand-500: #E1775A;
  --brand-600: #C8674A;
  --brand-700: #A5533A;
  --brand-800: #83422E;
  --brand-900: #613122;
}

[data-brand="emerald"] {
  --brand: #059669;
  --brand-50: #ECFDF5;
  --brand-100: #D1FAE5;
  --brand-200: #A7F3D0;
  --brand-300: #6EE7B7;
  --brand-400: #34D399;
  --brand-500: #10B981;
  --brand-600: #059669;
  --brand-700: #047857;
  --brand-800: #065F46;
  --brand-900: #064E3B;
}
```

Mecanismo: CSS custom properties inheritance — cambiar `--brand` en un `data-brand` attribute cambia todo el theme.

---

## 6. Transition entre themes

```css
/* Transición suave entre light/dark */
:root {
  transition:
    background-color 0.3s ease,
    color 0.3s ease,
    border-color 0.3s ease,
    box-shadow 0.3s ease;
}
```

No poner en `*` selector (causa performance issues en animaciones complejas). Solo en `:root` y componentes específicos.

---

## 7. Config theme (Tailwind 4)

```css
/* tailwind.css */
@import "tailwindcss";
@theme {
  --color-brand: var(--brand);
  --color-brand-50: var(--brand-50);
  --color-brand-100: var(--brand-100);
  --color-brand-200: var(--brand-200);
  --color-brand-300: var(--brand-300);
  --color-brand-400: var(--brand-400);
  --color-brand-500: var(--brand-500);
  --color-brand-600: var(--brand-600);
  --color-brand-700: var(--brand-700);
  --color-brand-800: var(--brand-800);
  --color-brand-900: var(--brand-900);

  --color-surface-ground: var(--surface-ground);
  --color-surface-card: var(--surface-card);
  --color-surface-border: var(--surface-border);
  --color-surface-hover: var(--surface-hover);

  --color-text-primary: var(--text-primary);
  --color-text-secondary: var(--text-secondary);
  --color-text-tertiary: var(--text-tertiary);
  --color-text-inverse: var(--text-inverse);
}
```

Esto permite usar `bg-brand`, `text-brand-600`, `border-surface-border`, `text-text-secondary` en Tailwind.
