import { Component, ViewChild, signal, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth/auth.service';
import { LocaleService } from '../../core/services/locale/locale.service';
import { SaasStatsWidget } from '../dashboard/components/saas-stats-widget';
import { NotificationsWidget } from '../dashboard/components/notificationswidget';
import { Subscription, interval } from 'rxjs';
import { finalize } from 'rxjs/operators';
import { SaasMetricsService, SaasMetrics } from '../../core/services/saas-metrics.service';

@Component({
    selector: 'app-admin-dashboard',
    standalone: true,
    imports: [CommonModule, SaasStatsWidget, NotificationsWidget],
    template: `
        @if (currentUser(); as user) {
            <section class="au-metric-card" style="margin-bottom: var(--dash-section-gap)">
                <div class="au-dash-header" style="border-bottom: none; padding-bottom: 0; margin-bottom: 16px">
                    <div>
                        <p class="au-dash-section-title">
                            <i class="pi pi-crown" style="color:var(--brand)"></i>
                            {{ t('dashboard.admin.control_global_saas') }}
                        </p>
                        <h2 class="au-dash-title">{{ t('dashboard.admin.workspace_overview') }}</h2>
                        <div style="display:flex;flex-wrap:wrap;gap:16px;margin-top:6px">
                            <span style="font-size:13px;color:var(--text-color-secondary);display:flex;align-items:center;gap:6px">
                                <i class="pi pi-shield" style="color:var(--brand)"></i>
                                {{ getRoleDisplayName(user.role) }}
                            </span>
                            <span style="font-size:13px;color:var(--text-color-secondary);display:flex;align-items:center;gap:6px">
                                <i class="pi pi-calendar" style="color:var(--brand)"></i>
                                {{ getCurrentDate() }}
                            </span>
                            <span style="font-size:13px;color:var(--text-color-secondary);display:flex;align-items:center;gap:6px">
                                <i class="pi pi-clock" style="color:var(--brand)"></i>
                                {{ getCurrentTime() }}
                            </span>
                            <span style="font-size:13px;color:var(--text-color-secondary);display:flex;align-items:center;gap:6px">
                                <i class="pi pi-user" style="color:var(--brand)"></i>
                                {{ user.full_name }}
                            </span>
                        </div>
                    </div>
                    <div style="display:flex;gap:8px">
                        <button type="button" (click)="refreshDashboard()" [disabled]="loading()" class="au-btn au-btn-secondary au-btn-sm">
                            <i class="pi pi-refresh" [class.pi-spin]="loading()"></i>
                            {{ t('dashboard.admin.refresh') }}
                        </button>
                        <button type="button" (click)="goToReports()" class="au-btn au-btn-primary au-btn-sm">
                            <i class="pi pi-chart-bar"></i>
                            {{ t('dashboard.admin.view_reports') }}
                        </button>
                    </div>
                </div>

                <div class="au-dash-grid">
                    <div class="au-metric-card au-metric-card--clients">
                        <p class="au-metric-label"><i class="pi pi-building"></i>{{ t('dashboard.admin.tenants') }}</p>
                        <p class="au-metric-value neutral">{{ metrics()?.total_tenants ?? 0 }}</p>
                        <div class="au-metric-context">
                            <span class="au-delta up">{{ metrics()?.active_tenants ?? 0 }} {{ t('dashboard.admin.active') }}</span>
                            &nbsp;·&nbsp;{{ inactiveTenants() }} {{ t('dashboard.admin.inactive') }}
                        </div>
                    </div>
                    <div class="au-metric-card au-metric-card--services">
                        <p class="au-metric-label"><i class="pi pi-hourglass"></i>{{ t('dashboard.admin.trials') }}</p>
                        <p class="au-metric-value brand">{{ metrics()?.expiring_trials_7d ?? 0 }}</p>
                        <div class="au-metric-context">
                            <span class="au-delta" [ngClass]="(metrics()?.expiring_trials_7d ?? 0) > 0 ? 'down' : 'neutral'">
                                {{ formatPercent(metrics()?.trial_conversion_rate) }} {{ t('dashboard.admin.historical_conversion') }}
                            </span>
                        </div>
                    </div>
                    <div class="au-metric-card au-metric-card--pos">
                        <p class="au-metric-label"><i class="pi pi-dollar"></i>{{ t('dashboard.admin.revenue') }}</p>
                        <p class="au-metric-value positive">{{ formatMoney(metrics()?.mrr) }}</p>
                        <div class="au-metric-context">
                            <span class="au-delta" [ngClass]="(metrics()?.growth_rate ?? 0) >= 0 ? 'up' : 'down'">
                                {{ formatSignedPercent(metrics()?.growth_rate) }}
                            </span>
                            {{ t('dashboard.admin.growth') }} · {{ t('dashboard.admin.churn') }} {{ formatPercent(metrics()?.churn_rate) }}
                        </div>
                    </div>
                </div>
            </section>

            <div class="mt-8 grid grid-cols-12 gap-8">
                <div class="col-span-12">
                    <div class="au-metric-card" style="margin-bottom: var(--dash-section-gap)">
                        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
                            <div>
                                <p class="au-dash-section-title">{{ t('dashboard.admin.executive_summary') }}</p>
                                <h2 class="au-dash-title">{{ t('dashboard.admin.business_overview') }}</h2>
                            </div>
                            <span style="display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--text-color-secondary)">
                                <i class="pi pi-pulse" style="color:var(--brand)"></i>
                                {{ t('dashboard.admin.real_time_updated') }}
                            </span>
                        </div>
                    </div>
                </div>
                <app-saas-stats-widget class="contents" />
                <div class="col-span-12 xl:col-span-6">
                    <div class="au-metric-card">
                        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
                            <div>
                                <p class="au-dash-section-title">{{ t('dashboard.admin.activity') }}</p>
                                <h3 style="font-size:1rem;font-weight:700;color:var(--text-color);margin:0">{{ t('dashboard.admin.notification_center') }}</h3>
                            </div>
                            <span class="au-delta neutral">
                                <i class="pi pi-bell"></i>
                                {{ t('dashboard.admin.recent_operations') }}
                            </span>
                        </div>
                        <app-notifications-widget />
                    </div>
                </div>
            </div>
        }
    `
})
export class AdminDashboard implements OnInit, OnDestroy {
    @ViewChild(SaasStatsWidget) private statsWidget?: SaasStatsWidget;

    currentUser = signal<any>(null);
    metrics = signal<SaasMetrics | null>(null);
    loading = signal(false);
    currentTime = signal(new Date());
    private subscription = new Subscription();

    constructor(
        private authService: AuthService,
        private saasMetricsService: SaasMetricsService,
        private router: Router,
        private localeService: LocaleService
    ) {}

    t(key: string): string {
        return this.localeService.t(key as any);
    }

    ngOnInit() {
        this.subscription.add(
            this.authService.currentUser$.subscribe(user => {
                this.currentUser.set(user);
            })
        );
        this.loadMetrics();
        this.subscription.add(
            interval(60000).subscribe(() => this.currentTime.set(new Date()))
        );
        this.subscription.add(
            interval(300000).subscribe(() => this.loadMetrics())
        );
    }

    ngOnDestroy() {
        this.subscription.unsubscribe();
    }

    private readonly roleTranslationKeys: Record<string, string> = {
        'SUPER_ADMIN': 'dashboard.admin.role_super_admin',
        'CLIENT_ADMIN': 'dashboard.admin.role_client_admin',
        'CLIENT_STAFF': 'dashboard.admin.role_client_staff',
    };

    getRoleDisplayName(role: string): string {
        const key = this.roleTranslationKeys[role];
        return key ? this.t(key) : role;
    }

    getCurrentDate(): string {
        return this.currentTime().toLocaleDateString('es-ES', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    }

    getCurrentTime(): string {
        return this.currentTime().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
    }

    inactiveTenants(): number {
        const metrics = this.metrics();
        if (!metrics) return 0;
        return Math.max((metrics.total_tenants || 0) - (metrics.active_tenants || 0), 0);
    }

    formatPercent(value?: number): string {
        return `${(value || 0).toFixed(1)}%`;
    }

    formatSignedPercent(value?: number): string {
        const safeValue = value || 0;
        return `${safeValue > 0 ? '+' : ''}${safeValue.toFixed(1)}%`;
    }

    formatMoney(value?: number): string {
        return new Intl.NumberFormat('es-DO', {
            style: 'currency',
            currency: 'USD',
            maximumFractionDigits: 0
        }).format(value || 0);
    }

    refreshDashboard(): void {
        this.loadMetrics(true);
        this.statsWidget?.loadMetrics();
    }

    goToReports(): void {
        this.router.navigate(['/admin/reports']);
    }

    loadMetrics(showLoading = false): void {
        if (showLoading) {
            this.loading.set(true);
        }

        this.subscription.add(
            this.saasMetricsService.getSaasMetrics().pipe(
                finalize(() => {
                    if (showLoading) {
                        this.loading.set(false);
                    }
                })
            ).subscribe({
                next: (metrics) => this.metrics.set(metrics),
                error: () => this.metrics.set(null)
            })
        );
    }
}
