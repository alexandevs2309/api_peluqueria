import { Component, OnInit, OnDestroy, inject, signal, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChartModule } from 'primeng/chart';
import { AuSkeleton } from '../../../shared/components';
import { debounceTime, Subscription } from 'rxjs';
import { LayoutService } from '../../../layout/service/layout.service';
import { DashboardService } from '../../../core/services/dashboard/dashboard.service';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { BranchService } from '../../../core/services/branch/branch.service';

@Component({
    standalone: true,
    selector: 'app-revenue-stream-widget',
    imports: [CommonModule, ChartModule, AuSkeleton],
    template: `
        <div class="card mb-8!">
            <div class="font-semibold text-xl mb-4">{{ t('dashboard.revenue_stream.title') }}</div>
            @if (loading()) {
                <div class="flex flex-col gap-4" style="height: 320px;">
                    <au-skeleton variant="chart" width="100%" height="100%" />
                </div>
            } @else {
                <p-chart type="line" [data]="chartData()" [options]="chartOptions" class="h-100" />
            }
        </div>
    `
})
export class RevenueStreamWidget implements OnInit, OnDestroy {
    chartData = signal<any>({});
    chartOptions: any;
    subscription!: Subscription;
    private localeService = inject(LocaleService);
    private branchService = inject(BranchService);
    monthlyRevenue = signal<any[]>([]);
    loading = signal(true);

    constructor(
        public layoutService: LayoutService,
        private dashboardService: DashboardService
    ) {
        this.subscription = this.layoutService.configUpdate$.pipe(debounceTime(25)).subscribe(() => {
            this.initChart();
        });
        effect(() => {
            const branchId = this.branchService.activeBranchId();
            this.loadMonthlyRevenue(branchId);
        });
    }

    ngOnInit() {
        // El effect del constructor maneja la carga inicial y los cambios de sucursal
        this.initChart();
    }

    loadMonthlyRevenue(branchId?: number | null) {
        this.loading.set(true);
        this.dashboardService.getDashboardStats(branchId).subscribe({
            next: (data: any) => {
                const revenue = data.monthly_revenue || [];
                this.monthlyRevenue.set(revenue);
                this.updateChart();
                this.loading.set(false);
            },
            error: (error: any) => {
                this.loading.set(false);
            }
        });
    }

    updateChart() {
        const data = this.monthlyRevenue();
        const defaultLabels = [0,1,2,3,4,5].map(i => this.t(`date.month_short.${i}`));
        const labels = Array.isArray(data) ? data.map((item: any) => item.month || defaultLabels[0]) : [];
        const revenues = Array.isArray(data) ? data.map((item: any) => item.revenue || 0) : [];

        const documentStyle = getComputedStyle(document.documentElement);
        
        this.chartData.set({
            labels: labels.length > 0 ? labels : defaultLabels,
            datasets: [
                {
                    label: this.t('dashboard.revenue_stream.label'),
                    data: revenues.length > 0 ? revenues : [0, 0, 0, 0, 0, 0],
                    fill: false,
                    backgroundColor: documentStyle.getPropertyValue('--p-primary-500'),
                    borderColor: documentStyle.getPropertyValue('--p-primary-500'),
                    tension: 0.4
                }
            ]
        });
    }

    initChart() {
        const documentStyle = getComputedStyle(document.documentElement);
        const textColor = documentStyle.getPropertyValue('--text-color');
        const borderColor = documentStyle.getPropertyValue('--surface-border');
        const textMutedColor = documentStyle.getPropertyValue('--text-color-secondary');

        this.chartOptions = {
            maintainAspectRatio: false,
            aspectRatio: 0.8,
            plugins: {
                legend: {
                    labels: {
                        color: textColor
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: textMutedColor
                    },
                    grid: {
                        color: borderColor,
                        drawBorder: false
                    }
                },
                y: {
                    ticks: {
                        color: textMutedColor
                    },
                    grid: {
                        color: borderColor,
                        drawBorder: false
                    }
                }
            }
        };

        this.updateChart();
    }

    ngOnDestroy() {
        if (this.subscription) {
            this.subscription.unsubscribe();
        }
    }

    t(key: string): string {
        return this.localeService.t(key as any);
    }
}
