import { Component, OnInit, signal, inject, effect } from '@angular/core';
import { RippleModule } from 'primeng/ripple';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { CommonModule } from '@angular/common';
import { DashboardService } from '../../../core/services/dashboard/dashboard.service';
import { AppCurrencyPipe } from '../../../core/pipes/app-currency.pipe';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { BranchService } from '../../../core/services/branch/branch.service';
import { AuSkeleton } from '../../../shared/components';

@Component({
    standalone: true,
    selector: 'app-recent-sales-widget',
    imports: [CommonModule, TableModule, ButtonModule, RippleModule, AppCurrencyPipe, AuSkeleton],
    template: `
        <div class="card mb-8!">
            <div class="font-semibold text-xl mb-4">{{ t('dashboard.recent_sales.title') }}</div>
            <p-table [value]="loading() ? dummySales : sales()" [paginator]="!loading()" [rows]="5" responsiveLayout="stack">
                <ng-template #header>
                    <tr>
                        <th>{{ t('dashboard.recent_sales.client') }}</th>
                        <th>{{ t('dashboard.recent_sales.total') }}</th>
                        <th>{{ t('dashboard.recent_sales.date') }}</th>
                        <th>{{ t('dashboard.recent_sales.services') }}</th>
                    </tr>
                </ng-template>
                <ng-template #body let-sale>
                    @if (loading()) {
                        <tr>
                            <td><au-skeleton width="8rem" /></td>
                            <td><au-skeleton width="4rem" /></td>
                            <td><au-skeleton width="8rem" /></td>
                            <td><au-skeleton width="12rem" /></td>
                        </tr>
                    } @else {
                        <tr>
                            <td>{{ getClientName(sale) }}</td>
                            <td>{{ sale.total | appCurrency }}</td>
                            <td>{{ sale.date_time | date: 'short' }}</td>
                            <td>{{ getServices(sale) }}</td>
                        </tr>
                    }
                </ng-template>
            </p-table>
        </div>
    `
})
export class RecentSalesWidget implements OnInit {
    private localeService = inject(LocaleService);
    private branchService = inject(BranchService);
    sales = signal<any[]>([]);
    loading = signal(true);
    dummySales = [{}, {}, {}, {}, {}];

    constructor(private dashboardService: DashboardService) {
        effect(() => {
            const branchId = this.branchService.activeBranchId();
            this.loadRecentSales(branchId);
        });
    }

    ngOnInit() {
        // El effect del constructor maneja la carga inicial y los cambios de sucursal
    }

    loadRecentSales(branchId?: number | null) {
        this.loading.set(true);
        this.dashboardService.getRecentSales(10, branchId).subscribe({
            next: (data) => {
                const sales = Array.isArray(data) ? data : (data.results || []);
                this.sales.set(sales.slice(0, 10));
                this.loading.set(false);
            },
            error: () => {
                this.loading.set(false);
            }
        });
    }

    getClientName(sale: any): string {
        return sale.client_name || this.t('dashboard.recent_sales.anonymous');
    }

    getServices(sale: any): string {
        const details = sale.details || [];
        const services = details
            .filter((item: any) => item.item_type === 'service')
            .map((item: any) => item.name);
        return services.length > 0 ? services.join(', ') : this.t('dashboard.recent_sales.na');
    }

    t(key: string): string {
        return this.localeService.t(key as any);
    }
}
