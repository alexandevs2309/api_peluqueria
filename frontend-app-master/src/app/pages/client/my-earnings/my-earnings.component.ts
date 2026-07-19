import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { CardModule } from 'primeng/card';
import { AuSkeleton } from '../../../shared/components';
import { firstValueFrom } from 'rxjs';
import { API_CONFIG } from '../../../core/config/api.config';
import { SettingsService } from '../../../core/services/settings/settings.service';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { I18nPipe } from '../../../core/pipes/i18n.pipe';

interface PeriodSummary {
  total_gross: number;
  total_net: number;
  total_deductions: number;
  paid_periods: number;
  pending_periods: number;
  payment_type: string;
  commission_rate: number;
}

interface MyPeriod {
  id: number;
  period_display: string;
  status: string;
  base_salary: number;
  commission_earnings: number;
  gross_amount: number;
  net_amount: number;
  deductions_total: number;
  period_start: string;
  period_end: string;
  payment_method: string | null;
  paid_at: string | null;
}

@Component({
  selector: 'app-my-earnings',
  standalone: true,
  imports: [CommonModule, TableModule, TagModule, CardModule, AuSkeleton, I18nPipe],
  template: `
    <div class="min-h-screen surface-ground p-4 md:p-6 space-y-6">
      <section class="auron-surface-card p-6">
        <div class="flex items-center gap-3 mb-1">
          <div class="w-12 h-12 rounded-2xl bg-[rgba(26,86,219,0.10)] dark:bg-[rgba(26,86,219,0.18)] flex items-center justify-center">
            <i class="pi pi-dollar text-[var(--brand)] dark:text-[var(--brand-400)] text-xl"></i>
          </div>
          <div>
            <h1 class="display-3 text-surface-900 dark:text-white">{{ 'my_earnings.title' | t }}</h1>
            <p class="text-sm text-surface-500 dark:text-surface-400">{{ 'my_earnings.subtitle' | t }}</p>
          </div>
        </div>
      </section>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="auron-surface-card p-4">
          <div class="text-xs text-surface-500 dark:text-surface-400 uppercase tracking-wide font-medium">{{ 'my_earnings.total_gross' | t }}</div>
          <div class="text-2xl font-bold text-surface-900 dark:text-white mt-1">{{ summary() ? formatMoney(summary()!.total_gross) : '-' }}</div>
        </div>
        <div class="bg-white dark:bg-surface-800 rounded-xl p-4 border border-surface-200 dark:border-surface-700">
          <div class="text-xs text-surface-500 dark:text-surface-400 uppercase tracking-wide font-medium">{{ 'my_earnings.total_net' | t }}</div>
          <div class="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">{{ summary() ? formatMoney(summary()!.total_net) : '-' }}</div>
        </div>
        <div class="bg-white dark:bg-surface-800 rounded-xl p-4 border border-surface-200 dark:border-surface-700">
          <div class="text-xs text-surface-500 dark:text-surface-400 uppercase tracking-wide font-medium">{{ 'my_earnings.deductions' | t }}</div>
          <div class="text-2xl font-bold text-red-500 dark:text-red-400 mt-1">{{ summary() ? formatMoney(summary()!.total_deductions) : '-' }}</div>
        </div>
        <div class="bg-white dark:bg-surface-800 rounded-xl p-4 border border-surface-200 dark:border-surface-700">
          <div class="text-xs text-surface-500 dark:text-surface-400 uppercase tracking-wide font-medium">{{ 'my_earnings.periods' | t }}</div>
          <div class="text-2xl font-bold text-surface-900 dark:text-white mt-1">
            <span class="text-emerald-600">{{ summary()?.paid_periods || 0 }}</span>
            <span class="text-sm text-surface-400 mx-1">/</span>
            <span class="text-amber-600">{{ summary()?.pending_periods || 0 }}</span>
          </div>
          <div class="text-xs text-surface-400 mt-0.5">{{ 'my_earnings.paid_pending' | t }}</div>
        </div>
      </div>

      <!-- Periods Table -->
      <div class="bg-white dark:bg-surface-800 rounded-xl border border-surface-200 dark:border-surface-700 overflow-hidden">
        <div class="p-4 border-b border-surface-200 dark:border-surface-700">
          <h2 class="font-semibold text-surface-900 dark:text-white">{{ 'my_earnings.periods_table_header' | t }}</h2>
        </div>

        @if (loading()) {
          <div class="p-4 space-y-3">
            @for (item of [1,2,3]; track item) {
              <au-skeleton height="48px"></au-skeleton>
            }
          </div>
        } @else if (periods().length === 0) {
          <div class="auron-empty-state">
            <div class="auron-empty-icon"><i class="pi pi-inbox"></i></div>
            <div class="auron-empty-title">{{ 'my_earnings.no_periods' | t }}</div>
            <p class="m-0">{{ 'my_earnings.subtitle' | t }}</p>
          </div>
        } @else {
          <p-table [value]="periods()" [rows]="10" [paginator]="periods().length > 10" [rowsPerPageOptions]="[10, 20, 50]" responsiveLayout="scroll">
            <ng-template pTemplate="header">
              <tr>
                <th>{{ 'my_earnings.th.period' | t }}</th>
                <th>{{ 'my_earnings.th.status' | t }}</th>
                <th>{{ 'my_earnings.th.base' | t }}</th>
                <th>{{ 'my_earnings.th.commission' | t }}</th>
                <th>{{ 'my_earnings.th.gross' | t }}</th>
                <th>{{ 'my_earnings.th.deductions' | t }}</th>
                <th>{{ 'my_earnings.th.net' | t }}</th>
                <th>{{ 'my_earnings.th.payment' | t }}</th>
              </tr>
            </ng-template>
            <ng-template pTemplate="body" let-p>
              <tr>
                <td class="font-medium">{{ p.period_display }}</td>
                <td><p-tag [value]="getStatusLabel(p.status)" [severity]="getStatusSeverity(p.status)"></p-tag></td>
                <td>{{ formatMoney(p.base_salary) }}</td>
                <td>{{ formatMoney(p.commission_earnings) }}</td>
                <td>{{ formatMoney(p.gross_amount) }}</td>
                <td class="text-red-500">{{ formatMoney(p.deductions_total) }}</td>
                <td class="font-semibold text-emerald-600">{{ formatMoney(p.net_amount) }}</td>
                <td>
                  @if (p.status === 'paid' && p.payment_method) {
                    <span class="text-xs text-surface-500">{{ p.payment_method }}</span>
                  } @else if (p.status === 'paid') {
                    <span class="text-xs text-surface-400">-</span>
                  } @else {
                    <span class="text-xs text-surface-400">{{ 'my_earnings.payment_pending' | t }}</span>
                  }
                </td>
              </tr>
            </ng-template>
          </p-table>
        }
      </div>

      <!-- Info Footer -->
      <div class="text-center text-xs text-surface-400 dark:text-surface-500">
        <span *ngIf="summary() as s">
          {{ 'my_earnings.payment_type' | t }}: <strong>{{ s.payment_type }}</strong>
          <span *ngIf="s.commission_rate"> · {{ 'my_earnings.commission_rate' | t }}: <strong>{{ s.commission_rate }}%</strong></span>
        </span>
      </div>
    </div>
  `,
  styles: [`
    :host ::ng-deep .p-table th {
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-color-secondary);
      font-weight: 600;
      padding: 0.75rem 1rem;
    }
    :host ::ng-deep .p-table td {
      padding: 0.75rem 1rem;
      font-size: 0.875rem;
    }
  `]
})
export class MyEarningsComponent implements OnInit {
  private http = inject(HttpClient);
  private settingsService = inject(SettingsService);
  private localeService = inject(LocaleService);

  loading = signal(true);
  periods = signal<MyPeriod[]>([]);
  summary = signal<PeriodSummary | null>(null);

  currencyCode = computed(() => this.settingsService.settings().currency || 'DOP');
  currencyLocale = computed(() => this.settingsService.getCurrencyLocale());

  private baseUrl = API_CONFIG.BASE_URL;

  async ngOnInit() {
    await Promise.all([this.loadPeriods(), this.loadSummary()]);
  }

  t(key: string): string {
    return this.localeService.t(key as any);
  }

  private async loadPeriods() {
    try {
      const res = await firstValueFrom(this.http.get<{ periods: MyPeriod[] }>(`${this.baseUrl}/employees/payroll/client/payroll/my-earnings/`));
      this.periods.set(res?.periods || []);
    } catch {
      this.periods.set([]);
    }
  }

  private async loadSummary() {
    try {
      const res = await firstValueFrom(this.http.get<PeriodSummary>(`${this.baseUrl}/employees/payroll/client/payroll/my-summary/`));
      this.summary.set(res || null);
    } catch {
      this.summary.set(null);
    } finally {
      this.loading.set(false);
    }
  }

  formatMoney(value: number): string {
    return new Intl.NumberFormat(this.currencyLocale(), {
      style: 'currency',
      currency: this.currencyCode(),
      minimumFractionDigits: 2
    }).format(value);
  }

  getStatusLabel(status: string): string {
    const map: Record<string, string> = {
      open: this.t('my_earnings.status.open'),
      pending_approval: this.t('my_earnings.status.pending_approval'),
      approved: this.t('my_earnings.status.approved'),
      paid: this.t('my_earnings.status.paid'),
      rejected: this.t('my_earnings.status.rejected'),
    };
    return map[status] || status;
  }

  getStatusSeverity(status: string): 'success' | 'info' | 'warn' | 'danger' | 'secondary' {
    const map: Record<string, 'success' | 'info' | 'warn' | 'danger' | 'secondary'> = {
      open: 'info',
      pending_approval: 'warn',
      approved: 'info',
      paid: 'success',
      rejected: 'danger',
    };
    return map[status] || 'secondary';
  }
}
