import { Component, OnInit, signal, inject, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ButtonModule } from 'primeng/button';
import { MenuModule } from 'primeng/menu';
import { DashboardService } from '../../../core/services/dashboard/dashboard.service';
import { AppCurrencyPipe } from '../../../core/pipes/app-currency.pipe';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { BranchService } from '../../../core/services/branch/branch.service';
import { AuSkeleton } from '../../../shared/components';

@Component({
    standalone: true,
    selector: 'app-best-selling-widget',
    imports: [CommonModule, ButtonModule, MenuModule, AppCurrencyPipe, AuSkeleton],
    template: `
        <div class="card">
            <div class="flex justify-between items-center mb-6">
                <div class="font-semibold text-xl">{{ t('dashboard.best_selling.title') }}</div>
            </div>
            <ul class="list-none p-0 m-0">
                @if (loading()) {
                    @for (dummy of [1, 2, 3, 4]; track dummy) {
                        <li class="flex flex-col md:flex-row md:items-center md:justify-between mb-6">
                            <div>
                                <au-skeleton width="10rem" class="mb-2" />
                                <au-skeleton width="6rem" />
                            </div>
                            <div class="mt-2 md:mt-0 flex items-center">
                                <au-skeleton width="6rem" height="8px" class="mr-4" />
                                <au-skeleton width="4rem" />
                            </div>
                        </li>
                    }
                } @else {
                    @for (service of topServices(); track service.name; let i = $index) {
                    <li class="flex flex-col md:flex-row md:items-center md:justify-between mb-6">
                        <div>
                            <span class="text-surface-900 dark:text-surface-0 font-medium mr-2 mb-1 md:mb-0">{{service.name}}</span>
                            <div class="mt-1 text-surface-500 dark:text-surface-400">{{ t('dashboard.best_selling.times_requested').replace('{count}', service.count) }}</div>
                        </div>
                        <div class="mt-2 md:mt-0 flex items-center">
                            <div class="bg-slate-200 dark:bg-slate-700 rounded-border overflow-hidden w-24 sm:w-40 lg:w-24" style="height: 8px">
                                <div class="bg-violet-600 h-full" [style.width.%]="getPercentage(service.count)"></div>
                            </div>
                            <span class="text-violet-600 ml-4 font-medium">{{(service.revenue || 0) | appCurrency}}</span>
                        </div>
                    </li>
                    }
                    @if (topServices().length === 0) {
                    <li class="text-center py-4 text-surface-500 dark:text-surface-400">
                        {{ t('dashboard.best_selling.no_data') }}
                    </li>
                    }
                }
            </ul>
        </div>
    `
})
export class BestSellingWidget implements OnInit {
    private localeService = inject(LocaleService);
    private branchService = inject(BranchService);
    topServices = signal<any[]>([]);
    maxCount = 0;
    loading = signal(true);

    constructor(private dashboardService: DashboardService) {
        effect(() => {
            const branchId = this.branchService.activeBranchId();
            this.loadTopServices(branchId);
        });
    }

    ngOnInit() {
        // El effect del constructor maneja la carga inicial y los cambios de sucursal
    }

    loadTopServices(branchId?: number | null) {
        this.loading.set(true);
        // Calcular top servicios desde las ventas recientes, filtrando por sucursal
        this.dashboardService.getRecentSales(100, branchId).subscribe({
            next: (data: any) => {
                const sales = Array.isArray(data) ? data : (data.results || []);
                const serviceCount: { [key: string]: { name: string; count: number; revenue: number } } = {};
                
                sales.forEach((sale: any) => {
                    const details = sale.details || [];
                    if (Array.isArray(details) && details.length > 0) {
                        details.forEach((item: any) => {
                            if (item.item_type === 'service') {
                                const serviceName = item.name || 'Servicio';
                                const price = parseFloat(item.price || 0) * (item.quantity || 1);
                                
                                if (!serviceCount[serviceName]) {
                                    serviceCount[serviceName] = { name: serviceName, count: 0, revenue: 0 };
                                }
                                serviceCount[serviceName].count += (item.quantity || 1);
                                serviceCount[serviceName].revenue += price;
                            }
                        });
                    }
                });
                
                const services = Object.values(serviceCount)
                    .sort((a, b) => b.count - a.count)
                    .slice(0, 5);
                
                this.topServices.set(services);
                this.maxCount = services.length > 0 ? Math.max(...services.map(s => s.count), 1) : 1;
                this.loading.set(false);
            },
            error: (error: any) => {
                this.loading.set(false);
            }
        });
    }

    getPercentage(count: number): number {
        return this.maxCount > 0 ? (count / this.maxCount) * 100 : 0;
    }

    t(key: string): string {
        return this.localeService.t(key as any);
    }
}
