import { Component, input } from '@angular/core';

export type AuBtnVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type AuBtnSize = 'sm' | 'md' | 'lg';

@Component({
  selector: 'button[au-btn], a[au-btn]',
  standalone: true,
  template: `
    @if (loading()) {
      <span class="au-btn__spinner" aria-hidden="true"></span>
    }
    @if (icon()) {
      <i [class]="icon()" aria-hidden="true"></i>
    }
    <ng-content />
  `,
  host: {
    '[class.au-btn]': 'true',
    '[class.au-btn--primary]': 'variant() === "primary"',
    '[class.au-btn--secondary]': 'variant() === "secondary"',
    '[class.au-btn--ghost]': 'variant() === "ghost"',
    '[class.au-btn--danger]': 'variant() === "danger"',
    '[class.au-btn--sm]': 'size() === "sm"',
    '[class.au-btn--lg]': 'size() === "lg"',
    '[class.au-btn--loading]': 'loading()',
    '[class.au-btn--icon-only]': 'iconOnly()',
    '[disabled]': 'disabled() || loading()',
  },
  styles: [`
    .au-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      border-radius: var(--radius-full, 9999px);
      border: 1px solid transparent;
      font-family: var(--font-family, 'Inter', sans-serif);
      font-weight: var(--font-semibold, 600);
      font-size: var(--text-sm, 0.875rem);
      line-height: 1.1;
      padding: 0.55rem 1.25rem;
      min-height: 2.5rem;
      cursor: pointer;
      transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease, border-color 160ms ease;
      user-select: none;
      text-decoration: none;
      white-space: nowrap;
      font-family: inherit;
    }
    .au-btn:hover { transform: translateY(-1px); }
    .au-btn:active { transform: translateY(0); }
    .au-btn:focus-visible {
      outline: 2px solid var(--brand, #1A56DB);
      outline-offset: 2px;
    }
    .au-btn:disabled { opacity: 0.5; cursor: not-allowed; pointer-events: none; }

    .au-btn--primary {
      background: var(--brand, #1A56DB);
      border-color: var(--brand, #1A56DB);
      color: #FFFFFF;
      box-shadow: 0 12px 28px color-mix(in srgb, var(--brand, #1A56DB) 24%, transparent);
    }
    .au-btn--primary:hover { background: var(--brand-hover, #1447C0); border-color: var(--brand-hover, #1447C0); }

    .au-btn--secondary {
      background: transparent;
      border-color: color-mix(in srgb, var(--brand, #1A56DB) 36%, var(--surface-border, #E5E0DB));
      color: var(--brand, #1A56DB);
    }
    .au-btn--secondary:hover { background: color-mix(in srgb, var(--brand, #1A56DB) 8%, transparent); }

    .au-btn--ghost {
      background: transparent;
      color: var(--text-color, #1E1B18);
      border-color: transparent;
    }
    .au-btn--ghost:hover { background: var(--surface-hover, #F2EFEC); }

    .au-btn--danger {
      background: var(--danger, #B84A4A);
      border-color: var(--danger, #B84A4A);
      color: #FFFFFF;
      box-shadow: 0 12px 28px color-mix(in srgb, var(--danger, #B84A4A) 22%, transparent);
    }
    .au-btn--danger:hover { background: var(--danger-600, #A23D3D); border-color: var(--danger-600, #A23D3D); }

    .au-btn--sm { padding: 0.45rem 0.9rem; font-size: var(--text-xs, 0.75rem); min-height: 2rem; }
    .au-btn--lg { padding: 0.75rem 1.5rem; font-size: var(--text-base, 1rem); min-height: 3rem; }

    .au-btn--icon-only { padding: 0.55rem; min-width: 2.5rem; }
    .au-btn--sm.au-btn--icon-only { padding: 0.45rem; min-width: 2rem; }
    .au-btn--lg.au-btn--icon-only { padding: 0.75rem; min-width: 3rem; }

    .au-btn--loading { pointer-events: none; opacity: 0.7; }

    .au-btn__spinner {
      width: 1em;
      height: 1em;
      border: 2px solid currentColor;
      border-top-color: transparent;
      border-radius: 50%;
      animation: au-spin 0.6s linear infinite;
    }
    @keyframes au-spin { to { transform: rotate(360deg); } }
  `],
})
export class AuBtn {
  readonly variant = input<AuBtnVariant>('primary');
  readonly size = input<AuBtnSize>('md');
  readonly loading = input(false);
  readonly disabled = input(false);
  readonly icon = input<string>();
  readonly iconOnly = input(false);
}
