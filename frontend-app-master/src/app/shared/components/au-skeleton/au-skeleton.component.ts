import { Component, input } from '@angular/core';

export type AuSkeletonVariant = 'text' | 'card' | 'table' | 'avatar' | 'chart' | 'badge';

@Component({
  selector: 'au-skeleton',
  standalone: true,
  template: '',
  host: {
    '[class.au-skeleton]': 'true',
    '[class.au-skeleton--text]': 'variant() === "text"',
    '[class.au-skeleton--card]': 'variant() === "card"',
    '[class.au-skeleton--table]': 'variant() === "table"',
    '[class.au-skeleton--avatar]': 'variant() === "avatar"',
    '[class.au-skeleton--chart]': 'variant() === "chart"',
    '[class.au-skeleton--badge]': 'variant() === "badge"',
    '[style.width]': 'width() || null',
    '[style.height]': 'height() || null',
    'aria-hidden': 'true',
  },
  styles: [`
    .au-skeleton {
      display: block;
      background: linear-gradient(
        90deg,
        var(--surface-border, #E5E0DB) 25%,
        var(--surface-hover, #F2EFEC) 50%,
        var(--surface-border, #E5E0DB) 75%
      );
      background-size: 200% 100%;
      animation: au-shimmer 1.8s ease-in-out infinite;
      border-radius: var(--radius-sm, 0.375rem);
    }
    .app-dark .au-skeleton {
      background: linear-gradient(
        90deg,
        var(--surface-border, #3A3530) 25%,
        var(--surface-hover, #2E2B28) 50%,
        var(--surface-border, #3A3530) 75%
      );
      background-size: 200% 100%;
    }

    .au-skeleton--text { height: 0.875rem; width: 100%; margin-bottom: 0.5rem; }
    .au-skeleton--text:last-child { width: 60%; }

    .au-skeleton--card { height: 8rem; border-radius: var(--radius-xl, 1rem); }
    .au-skeleton--table { height: 3rem; width: 100%; margin-bottom: 0.25rem; }
    .au-skeleton--table:first-child { height: 2.5rem; }

    .au-skeleton--avatar {
      width: 2.5rem;
      height: 2.5rem;
      border-radius: var(--radius-full, 9999px);
    }

    .au-skeleton--chart { height: 12rem; border-radius: var(--radius-lg, 0.75rem); }
    .au-skeleton--badge { width: 3rem; height: 1.25rem; border-radius: var(--radius-full, 9999px); }

    @keyframes au-shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
  `],
})
export class AuSkeleton {
  readonly variant = input<AuSkeletonVariant>('text');
  readonly width = input<string>();
  readonly height = input<string>();
}
