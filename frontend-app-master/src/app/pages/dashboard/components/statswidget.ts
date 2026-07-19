import { Component, OnInit, signal, ChangeDetectionStrategy, inject, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DashboardService } from '../../../core/services/dashboard/dashboard.service';
import { AppCurrencyPipe } from '../../../core/pipes/app-currency.pipe';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { BranchService } from '../../../core/services/branch/branch.service';
import { AuSkeleton } from '../../../shared/components';

@Component({
    standalone: true,
    selector: 'app-stats-widget',
    imports: [CommonModule, AppCurrencyPipe, AuSkeleton],
    changeDetection: ChangeDetectionStrategy.OnPush,
    template: `
        <div class="col-span-12 lg:col-span-6 xl:col-span-3">
            <div class="au-metric-card">
                <div class="au-metric-header">
                    <span class="au-metric-icon"><i class="pi pi-dollar"></i></span>
                    <span class="au-metric-label">{{ t('dashboard.stats.total_sales') }}</span>
                </div>
                @if (loading()) {
                    <au-skeleton width="7rem" height="2.5rem" class="au-metric-value" />
                    <au-skeleton width="5rem" height="1rem" class="au-metric-context" />
                } @else {
                    <div class="au-metric-value neutral">{{ (stats()?.revenue_range || 0) | appCurrency }}</div>
                    <div class="au-metric-context">{{ stats()?.transactions_range || 0 }} {{ t('dashboard.stats.transactions') }}</div>
                }
            </div>
        </div>
        <div class="col-span-12 lg:col-span-6 xl:col-span-3">
            <div class="au-metric-card">
                <div class="au-metric-header">
                    <span class="au-metric-icon"><i class="pi pi-chart-line"></i></span>
                    <span class="au-metric-label">{{ t('dashboard.stats.average_ticket') }}</span>
                </div>
                @if (loading()) {
                    <au-skeleton width="7rem" height="2.5rem" class="au-metric-value" />
                    <au-skeleton width="5rem" height="1rem" class="au-metric-context" />
                } @else {
                    <div class="au-metric-value neutral">{{ (stats()?.average_ticket || 0) | appCurrency }}</div>
                    <div class="au-metric-context">{{ t('dashboard.stats.per_sale') }} {{ t('dashboard.stats.average_label') }}</div>
                }
            </div>
        </div>
        <div class="col-span-12 lg:col-span-6 xl:col-span-3">
            <div class="au-metric-card">
                <div class="au-metric-header">
                    <span class="au-metric-icon"><i class="pi pi-calendar"></i></span>
                    <span class="au-metric-label">{{ t('dashboard.stats.monthly_income').replace('{month}', currentMonthLabel()) }}</span>
                </div>
                @if (loading()) {
                    <au-skeleton width="7rem" height="2.5rem" class="au-metric-value" />
                    <au-skeleton width="5rem" height="1rem" class="au-metric-context" />
                } @else {
                    <div class="au-metric-value positive">{{ monthRevenue() | appCurrency }}</div>
                    <div class="au-metric-context">{{ currentMonthLabel() }} · {{ t('dashboard.stats.accumulated') }}</div>
                }
            </div>
        </div>
        <div class="col-span-12 lg:col-span-6 xl:col-span-3">
            <div class="au-metric-card">
                <div class="au-metric-header">
                    <span class="au-metric-icon"><i class="pi pi-shopping-cart"></i></span>
                    <span class="au-metric-label">{{ t('dashboard.stats.recent_sales') }}</span>
                </div>
                @if (loading()) {
                    <au-skeleton width="7rem" height="2.5rem" class="au-metric-value" />
                    <au-skeleton width="5rem" height="1rem" class="au-metric-context" />
                } @else {
                    <div class="au-metric-value neutral">{{ stats()?.transactions_range || 0 }}</div>
                    <div class="au-metric-context">{{ t('dashboard.stats.total_label') }} {{ t('dashboard.stats.registered') }}</div>
                }
            </div>
        </div>
    `
})
export class StatsWidget implements OnInit {
    private localeService = inject(LocaleService);
    private branchService = inject(BranchService);
    stats = signal<any>(null);
    monthRevenue = signal<number>(0);
    currentMonthLabel = signal('');
    loading = signal(true);

    constructor(private dashboardService: DashboardService) {
        const now = new Date();
        this.currentMonthLabel.set(this.t(`date.month.${now.getMonth()}`));
        // Recargar automáticamente al cambiar de sucursal
        effect(() => {
            const branchId = this.branchService.activeBranchId();
            this.loadStats(branchId);
        });
    }

    ngOnInit() {
        // El effect del constructor maneja la carga inicial y los cambios de sucursal
    }

    loadStats(branchId?: number | null) {
        this.loading.set(true);
        this.dashboardService.getDashboardStats(branchId).subscribe({
            next: (data) => {
                this.stats.set(data);
                this.updateMonthRevenue(data);
                this.loading.set(false);
            },
            error: () => {
                this.loading.set(false);
            }
        });
    }

    t(key: string): string {
        return this.localeService.t(key as any);
    }

    private updateMonthRevenue(data: any) {
        const monthlyRevenue = data?.monthly_revenue || [];
        if (monthlyRevenue.length > 0) {
            this.monthRevenue.set(monthlyRevenue[monthlyRevenue.length - 1].revenue || 0);
        } else {
            this.monthRevenue.set(0);
        }
    }
}
