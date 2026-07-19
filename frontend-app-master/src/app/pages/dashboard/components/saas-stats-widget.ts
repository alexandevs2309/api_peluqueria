import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SaasMetricsService, SaasMetrics } from '../../../core/services/saas-metrics.service';
import { LocaleService } from '../../../core/services/locale/locale.service';

@Component({
    standalone: true,
    selector: 'app-saas-stats-widget',
    imports: [CommonModule],
    template: `
        <div class="col-span-12 lg:col-span-6 xl:col-span-3">
            <div class="au-metric-card au-metric-card--pos">
                <p class="au-metric-label"><i class="pi pi-dollar"></i>{{ t('dashboard.saas.mrr') }}</p>
                <p class="au-metric-value positive">{{(metrics()?.mrr || 0) | currency:'USD':'symbol':'1.0-0'}}</p>
                <div class="au-metric-context">
                    <span class="au-delta" [ngClass]="(metrics()?.growth_rate || 0) >= 0 ? 'up' : 'down'">
                        <i class="pi" [ngClass]="growthIconClass()"></i>{{ growthDisplay() }}
                    </span>
                    {{ t('dashboard.saas.growth') }}
                </div>
            </div>
        </div>
        <div class="col-span-12 lg:col-span-6 xl:col-span-3">
            <div class="au-metric-card au-metric-card--clients">
                <p class="au-metric-label"><i class="pi pi-users"></i>{{ t('dashboard.saas.active_tenants') }}</p>
                <p class="au-metric-value neutral">{{metrics()?.active_tenants || 0}}</p>
                <div class="au-metric-context">
                    <span class="au-delta neutral">{{ metrics()?.total_tenants || 0 }} {{ t('dashboard.saas.total_label') }}</span>
                    &nbsp;·&nbsp;{{ metrics()?.trial_tenants || 0 }} {{ t('dashboard.saas.in_trial') }}
                </div>
            </div>
        </div>
        <div class="col-span-12 lg:col-span-6 xl:col-span-3">
            <div class="au-metric-card au-metric-card--services">
                <p class="au-metric-label"><i class="pi pi-chart-line"></i>{{ t('dashboard.saas.churn_rate') }}</p>
                <p class="au-metric-value"
                   [class.negative]="(metrics()?.churn_rate || 0) > 2"
                   [class.neutral]="(metrics()?.churn_rate || 0) <= 2">
                    {{(metrics()?.churn_rate || 0).toFixed(1)}}%
                </p>
                <div class="au-metric-context">{{ t('dashboard.saas.monthly') }} · {{ t('dashboard.saas.cancellations') }}</div>
            </div>
        </div>
        <div class="col-span-12 lg:col-span-6 xl:col-span-3">
            <div class="au-metric-card au-metric-card--agenda">
                <p class="au-metric-label"><i class="pi pi-clock"></i>{{ t('dashboard.saas.active_trials') }}</p>
                <p class="au-metric-value brand">{{metrics()?.trial_tenants || 0}}</p>
                <div class="au-metric-context">
                    <span class="au-delta" [ngClass]="(metrics()?.expiring_trials_7d || 0) > 0 ? 'down' : 'neutral'">
                        {{ metrics()?.expiring_trials_7d || 0 }} {{ t('dashboard.saas.expire_7d') }}
                    </span>
                </div>
            </div>
        </div>
    `
})
export class SaasStatsWidget implements OnInit {
    private localeService = inject(LocaleService);
    metrics = signal<SaasMetrics | null>(null);

    constructor(private saasMetricsService: SaasMetricsService) {}

    ngOnInit() {
        this.loadMetrics();
    }

    loadMetrics() {
        this.saasMetricsService.getSaasMetrics().subscribe({
            next: (data) => this.metrics.set(data),
            error: () => this.metrics.set(null)
        });
    }

    growthDisplay(): string {
        const value = this.metrics()?.growth_rate || 0;
        if (value > 0) return `+${value}%`;
        if (value < 0) return `${value}%`;
        return '0%';
    }

    growthValueClass(): string {
        const value = this.metrics()?.growth_rate || 0;
        if (value > 0) return 'text-green-500';
        if (value < 0) return 'text-red-500';
        return 'text-surface-500 dark:text-surface-300';
    }

    growthIconClass(): string {
        const value = this.metrics()?.growth_rate || 0;
        if (value > 0) return 'pi-arrow-up';
        if (value < 0) return 'pi-arrow-down';
        return 'pi-minus';
    }

    t(key: string): string {
        return this.localeService.t(key as any);
    }
}
