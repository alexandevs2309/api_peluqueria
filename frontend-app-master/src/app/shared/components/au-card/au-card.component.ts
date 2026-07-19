import { Component, input } from '@angular/core';

@Component({
  selector: 'au-card',
  standalone: true,
  template: `
    @if (title() || subtitle()) {
      <div class="au-card__header">
        @if (title()) {
          <h3 class="au-card__title">{{ title() }}</h3>
        }
        @if (subtitle()) {
          <p class="au-card__subtitle">{{ subtitle() }}</p>
        }
      </div>
    }
    <div class="au-card__body"><ng-content /></div>
  `,
  host: {
    '[class.au-card]': 'true',
    '[class.au-card--glass]': 'variant() === "glass"',
    '[class.au-card--lift]': 'variant() === "lift"',
    '[class.au-card--bordered]': 'variant() === "bordered"',
    '[class.au-card--flat]': 'variant() === "flat"',
  },
  styles: [`
    .au-card {
      display: block;
      width: 100%;
      background: var(--surface-card, #FFFFFF);
      border: 1px solid var(--surface-border, #E5E0DB);
      border-radius: var(--radius-xl, 1rem);
      padding: 1.5rem;
      box-shadow: var(--shadow-card, 0 1px 3px rgba(30,27,24,0.06));
      transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .au-card--glass {
      background: rgba(255, 255, 255, 0.78);
      backdrop-filter: blur(20px) saturate(170%);
      -webkit-backdrop-filter: blur(20px) saturate(170%);
      border-color: rgba(228, 231, 236, 0.6);
    }
    .app-dark .au-card--glass {
      background: rgba(19, 22, 29, 0.80);
      border-color: rgba(31, 35, 48, 0.7);
    }

    .au-card--lift:hover {
      transform: translateY(-3px);
      box-shadow: 0 20px 60px -30px rgba(30, 27, 24, 0.20);
    }

    .au-card--bordered {
      border-left: 4px solid var(--brand, #1A56DB);
      border-radius: 0 var(--radius-xl, 1rem) var(--radius-xl, 1rem) 0;
    }

    .au-card--flat {
      background: transparent;
      border: none;
      box-shadow: none;
      padding: 0;
    }

    .au-card__header {
      margin-bottom: 1rem;
    }

    .au-card__title {
      font-size: var(--text-lg, 1.125rem);
      font-weight: var(--font-semibold, 600);
      color: var(--text-color, #1E1B18);
      margin: 0;
      letter-spacing: var(--tracking-tight, -0.02em);
    }

    .au-card__subtitle {
      font-size: var(--text-sm, 0.875rem);
      color: var(--text-color-secondary, #9C948C);
      margin: 0.25rem 0 0;
      line-height: var(--leading-normal, 1.5);
    }

    .au-card__body {
      color: var(--text-color, #1E1B18);
    }
  `],
})
export class AuCard {
  readonly variant = input<'glass' | 'lift' | 'bordered' | 'flat' | 'default'>('default');
  readonly title = input<string>();
  readonly subtitle = input<string>();
}
