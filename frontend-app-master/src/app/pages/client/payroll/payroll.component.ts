import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PeriodsListComponent } from './components/periods-list/periods-list.component';
import { I18nPipe } from '../../../core/pipes/i18n.pipe';

@Component({
  selector: 'app-payroll',
  standalone: true,
  imports: [CommonModule, PeriodsListComponent, I18nPipe],
  template: `
    <div class="min-h-screen surface-ground p-4 md:p-6 space-y-6">
      <section id="onb-earnings-header" class="overflow-hidden rounded-[2rem] border border-surface-200/70 bg-surface-0 shadow-[var(--shadow-elevated)] dark:border-surface-800 dark:bg-surface-900">
        <div class="relative overflow-hidden px-8 py-8 lg:px-10">
          <div class="hero-gradient"></div>
          <div class="relative grid gap-8 lg:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.9fr)] lg:items-start">
            <div class="space-y-5">
              <div class="inline-flex items-center gap-2 rounded-full border border-surface-200 bg-surface-50/90 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.24em] text-surface-600 dark:border-surface-700 dark:bg-surface-800/80 dark:text-surface-300">
                <i class="pi pi-money-bill text-[0.7rem] text-primary"></i>
                {{ 'menu.payroll' | t }}
              </div>
              <div>
                <h1 class="display-3 text-surface-950 dark:text-surface-0">{{ 'menu.payroll' | t }}</h1>
                <p class="mt-3 max-w-3xl text-base leading-7 text-surface-600 dark:text-surface-300">{{ 'payroll.subtitle' | t }}</p>
              </div>
            </div>
            <div class="rounded-3xl border border-surface-200 bg-white/80 p-5 shadow-sm backdrop-blur dark:border-surface-700 dark:bg-surface-800/80">
              <div class="text-xs font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">{{ 'products.main_action' | t }}</div>
              <div class="mt-4 grid gap-3">
                <div class="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 dark:border-emerald-900/60 dark:bg-emerald-900/10">
                  <div class="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700 dark:text-emerald-300">{{ 'payroll.review_periods' | t }}</div>
                  <p class="mt-2 text-sm leading-6 text-surface-600 dark:text-surface-300">{{ 'payroll.review_periods_desc' | t }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div class="flex-1 rounded-[1.75rem] border border-surface-200 bg-white shadow-sm dark:border-surface-700 dark:bg-surface-900">
        <app-periods-list></app-periods-list>
      </div>
    </div>
  `,
  styles: [`
    .success-background {
      background-color: color-mix(in srgb, var(--success-color) 10%, transparent);
    }
    .success-border {
      border-color: color-mix(in srgb, var(--success-color) 30%, transparent);
    }
    .success-text {
      color: var(--success-color-text);
    }
  `]
})
export class PayrollComponent {}
