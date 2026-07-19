import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { ButtonModule } from 'primeng/button';

@Component({
  selector: 'auron-empty-state',
  standalone: true,
  imports: [CommonModule, ButtonModule],
  template: `
    <div class="auron-empty" [class.auron-empty--contextual]="variant === 'contextual'">
      <div class="auron-empty__icon">
        <i [class]="icon"></i>
      </div>
      <h3 class="auron-empty__title">{{ title }}</h3>
      <p class="auron-empty__description">{{ description }}</p>
      @if (ctaLabel) {
        <button pButton type="button" class="au-btn au-btn-primary au-btn-sm" [label]="ctaLabel" (click)="ctaAction.emit()"></button>
      }
    </div>
  `,
  styles: [`
    .auron-empty {
      display: flex;
      min-height: 13rem;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 0.75rem;
      padding: 2.5rem 1.5rem;
      text-align: center;
      color: var(--text-color-secondary);
    }

    .auron-empty--contextual {
      border: 1px dashed var(--surface-border);
      border-radius: var(--app-radius-2xl);
      background: color-mix(in srgb, var(--surface-card) 86%, transparent);
    }

    .auron-empty__icon {
      display: grid;
      width: 3.4rem;
      height: 3.4rem;
      place-items: center;
      border-radius: var(--app-radius-xl);
      background: color-mix(in srgb, var(--brand) 10%, var(--surface-card));
      color: var(--brand);
      font-size: 1.35rem;
    }

    .auron-empty__title {
      margin: 0;
      color: var(--text-color);
      font-size: 1.05rem;
      font-weight: var(--font-heading);
    }

    .auron-empty__description {
      margin: 0;
      max-width: 28rem;
      color: var(--text-color-secondary);
      font-size: 0.92rem;
      line-height: 1.6;
    }
  `],
})
export class AuronEmptyStateComponent {
  @Input() icon = 'pi pi-inbox';
  @Input() title = '';
  @Input() description = '';
  @Input() ctaLabel?: string;
  @Input() variant: 'default' | 'contextual' = 'default';

  @Output() ctaAction = new EventEmitter<void>();
}
