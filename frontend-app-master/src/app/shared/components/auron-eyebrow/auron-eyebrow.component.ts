import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

@Component({
  selector: 'auron-eyebrow',
  standalone: true,
  imports: [CommonModule],
  template: `
    <span class="auron-eyebrow" [class]="'auron-eyebrow auron-eyebrow--' + variant">
      @if (icon) {
        <i [class]="icon"></i>
      }
      <span>{{ label }}</span>
    </span>
  `,
  styles: [`
    .auron-eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      width: fit-content;
      border-radius: 999px;
      border: 1px solid color-mix(in srgb, var(--surface-border) 70%, transparent);
      padding: 0.42rem 0.82rem;
      background: color-mix(in srgb, var(--surface-card) 88%, transparent);
      color: var(--text-color-secondary);
      font-size: 0.72rem;
      font-weight: var(--font-heading);
      letter-spacing: 0.18em;
      line-height: 1;
      text-transform: uppercase;
    }

    .auron-eyebrow i {
      font-size: 0.72rem;
      letter-spacing: 0;
    }

    .auron-eyebrow--default,
    .auron-eyebrow--info {
      border-color: color-mix(in srgb, var(--brand) 18%, transparent);
      background: color-mix(in srgb, var(--brand) 9%, var(--surface-card));
      color: var(--brand);
    }

    .auron-eyebrow--success {
      border-color: color-mix(in srgb, #10b981 22%, transparent);
      background: color-mix(in srgb, #10b981 10%, var(--surface-card));
      color: #047857;
    }

    .auron-eyebrow--warning {
      border-color: color-mix(in srgb, #f59e0b 24%, transparent);
      background: color-mix(in srgb, #f59e0b 12%, var(--surface-card));
      color: #b45309;
    }

    .auron-eyebrow--danger {
      border-color: color-mix(in srgb, #ef4444 24%, transparent);
      background: color-mix(in srgb, #ef4444 10%, var(--surface-card));
      color: #dc2626;
    }

    :host-context(.app-dark) .auron-eyebrow--success {
      color: #6ee7b7;
    }

    :host-context(.app-dark) .auron-eyebrow--warning {
      color: #fcd34d;
    }

    :host-context(.app-dark) .auron-eyebrow--danger {
      color: #fca5a5;
    }
  `],
})
export class AuronEyebrowComponent {
  @Input() label = '';
  @Input() icon?: string;
  @Input() variant: 'default' | 'success' | 'warning' | 'info' | 'danger' = 'default';
}
