import { Component, DestroyRef, OnInit, inject, computed, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CurrencyPipe } from '@angular/common';
import { ConfirmationService, MessageService } from 'primeng/api';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { RippleModule } from 'primeng/ripple';
import { ToastModule } from 'primeng/toast';
import { InputTextModule } from 'primeng/inputtext';
import { TextareaModule } from 'primeng/textarea';
import { InputNumberModule } from 'primeng/inputnumber';
import { DialogModule } from 'primeng/dialog';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { TooltipModule } from 'primeng/tooltip';
import { AuBtn } from '../../shared/components';
import { SubscriptionService } from '../../core/services/subscription/subscription.service';
import { AdminErrorLogService } from '../../core/services/admin-error-log.service';

interface SubscriptionPlan {
    id?: number;
    name?: string;
    display_name?: string;
    description?: string;
    price?: number;
    max_users?: number;
    duration_month?: number;
    stripe_price_id?: string | null;
    allows_multiple_branches?: boolean;
    features?: Record<string, boolean> | string[];
    features_list?: string[];
    commercial_benefits?: string[];
    is_public?: boolean;
    is_active?: boolean;
    created_at?: string;
    updated_at?: string;
}

@Component({
    selector: 'app-subscription-plans',
    standalone: true,
    imports: [
        FormsModule,
        ButtonModule,
        RippleModule,
        ToastModule,
        InputTextModule,
        TextareaModule,
        InputNumberModule,
        DialogModule,
        ConfirmDialogModule,
        TooltipModule,
        CurrencyPipe,
        AuBtn,
    ],
    template: `
        <section class="mb-8 overflow-hidden rounded-[2rem] border border-surface-200/70 bg-surface-0 shadow-[0_24px_80px_-42px_rgba(15,23,42,0.45)] dark:border-surface-800 dark:bg-surface-900">
            <div class="relative overflow-hidden px-8 py-8 lg:px-10">
                <div class="lg:flex lg:items-start lg:justify-between">
                    <div class="min-w-0 flex-1">
                        <div class="mb-2 inline-flex items-center gap-2 rounded-full border border-surface-200 bg-surface-50/90 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.24em] text-surface-600 dark:border-surface-700 dark:bg-surface-800/80 dark:text-surface-300">
                            <i class="pi pi-credit-card text-primary"></i>
                            Suscripciones
                        </div>
                        <h1 class="text-2xl font-bold tracking-tight text-surface-950 dark:text-surface-0 sm:text-3xl">
                            Planes de Suscripción
                        </h1>
                        <div class="mt-1 text-sm text-surface-500 dark:text-surface-400">
                            Gestiona los planes del sistema, precios, funciones y disponibilidad.
                        </div>
                    </div>
                    <div class="mt-4 flex items-center gap-3 lg:mt-0 lg:ml-4">
                        <button au-btn [icon]="'pi pi-plus'" (click)="openNew()">Nuevo Plan</button>
                        <div class="relative">
                            <i class="pi pi-search absolute left-3 top-1/2 -translate-y-1/2 text-surface-400 text-sm"></i>
                            <input
                                #searchInput
                                type="text"
                                placeholder="Buscar planes..."
                                (input)="onSearch($event)"
                                class="w-56 rounded-lg border border-surface-200 bg-surface-0 py-2 pl-9 pr-3 text-sm text-surface-700 placeholder:text-surface-400 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-200 dark:placeholder:text-surface-500"
                            />
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <div class="overflow-hidden rounded-[2rem] border border-surface-200/70 bg-surface-0 shadow-[0_24px_80px_-42px_rgba(15,23,42,0.45)] dark:border-surface-800 dark:bg-surface-900">
            <!-- Móvil: Tarjetas apiladas -->
            <div class="block md:hidden p-4 space-y-4">
                @for (plan of sortedPlans(); track plan.id) {
                    <div class="bg-white dark:bg-surface-900 rounded-xl border border-surface-200 dark:border-surface-800 shadow-sm overflow-hidden">
                        <div class="p-4">
                            <div class="flex items-start justify-between mb-3">
                                <div>
                                    <h4 class="font-bold text-surface-900 dark:text-white">{{ plan.display_name || plan.name }}</h4>
                                    <p class="text-xs text-surface-500 dark:text-surface-400 mt-0.5">{{ plan.name }}</p>
                                </div>
                                <span class="font-bold text-lg text-primary-600 dark:text-primary-400">{{ plan.price | currency:'USD' }}</span>
                            </div>
                            <p class="text-sm text-surface-600 dark:text-surface-300 mb-3 line-clamp-2">{{ plan.description }}</p>
                            <div class="space-y-2 text-sm">
                                <div class="flex justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Duración</span>
                                    <span class="text-surface-700 dark:text-surface-200">{{ formatDuration(plan.duration_month) }}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Usuarios</span>
                                    <span class="text-surface-700 dark:text-surface-200">{{ plan.max_users || 'Ilimitado' }}</span>
                                </div>
                                <div class="flex items-center justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Multi-Suc.</span>
                                    <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                                          [class.bg-emerald-100!]="plan.allows_multiple_branches"
                                          [class.text-emerald-700!]="plan.allows_multiple_branches"
                                          [class.dark:bg-emerald-900/30!]="plan.allows_multiple_branches"
                                          [class.dark:text-emerald-300!]="plan.allows_multiple_branches"
                                          [class.bg-surface-100!]="!plan.allows_multiple_branches"
                                          [class.text-surface-500!]="!plan.allows_multiple_branches"
                                          [class.dark:bg-surface-800!]="!plan.allows_multiple_branches"
                                          [class.dark:text-surface-400!]="!plan.allows_multiple_branches">
                                        {{ plan.allows_multiple_branches ? 'Si' : 'No' }}
                                    </span>
                                </div>
                                <div class="flex items-center justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Estado</span>
                                    <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                                          [class.bg-emerald-100!]="plan.is_active"
                                          [class.text-emerald-700!]="plan.is_active"
                                          [class.dark:bg-emerald-900/30!]="plan.is_active"
                                          [class.dark:text-emerald-300!]="plan.is_active"
                                          [class.bg-rose-100!]="!plan.is_active"
                                          [class.text-rose-700!]="!plan.is_active"
                                          [class.dark:bg-rose-900/30!]="!plan.is_active"
                                          [class.dark:text-rose-300!]="!plan.is_active">
                                        {{ plan.is_active ? 'Activo' : 'Inactivo' }}
                                    </span>
                                </div>
                            </div>
                            <div class="flex items-center justify-end pt-3 mt-3 border-t border-surface-100 dark:border-surface-800">
                                <button au-btn variant="ghost" [icon]="'pi pi-pencil'"
                                        (click)="editPlan(plan)"></button>
                            </div>
                        </div>
                    </div>
                } @empty {
                    <div class="py-8 text-center text-surface-500 dark:text-surface-400">
                        <i class="pi pi-credit-card text-3xl block mb-2 opacity-50"></i>
                        No hay planes de suscripción
                    </div>
                }
                @if (totalPages() > 1) {
                    <div class="flex items-center justify-between px-2 py-2">
                        <span class="text-sm text-surface-500 dark:text-surface-400">{{ (currentPage() - 1) * pageSize + 1 }}–{{ min(currentPage() * pageSize, filteredPlans().length) }} de {{ filteredPlans().length }}</span>
                        <div class="flex items-center gap-2">
                            <button au-btn variant="ghost" [icon]="'pi pi-chevron-left'"
                                    [disabled]="currentPage() === 1" (click)="prevPage()"></button>
                            <span class="text-sm text-surface-500 dark:text-surface-400">{{ currentPage() }}/{{ totalPages() }}</span>
                            <button au-btn variant="ghost" [icon]="'pi pi-chevron-right'"
                                    [disabled]="currentPage() === totalPages()" (click)="nextPage()"></button>
                        </div>
                    </div>
                }
            </div>

            <!-- Desktop: Tabla -->
            <div class="hidden md:block">
            <div class="overflow-x-auto">
                <table class="w-full text-sm">
                    <thead>
                         <tr class="border-b border-surface-200 dark:border-surface-700 bg-surface-50/50 dark:bg-surface-800/50">
                            <th class="cursor-pointer select-none py-4 pl-6 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400" (click)="toggleSort('name')">
                                Plan
                                <i class="pi ml-1" [class.pi-sort-up]="sortField() === 'name' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'name' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'name'"></i>
                            </th>
                            <th class="py-4 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">Descripción</th>
                            <th class="cursor-pointer select-none py-4 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400" (click)="toggleSort('price')">
                                Precio
                                <i class="pi ml-1" [class.pi-sort-up]="sortField() === 'price' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'price' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'price'"></i>
                            </th>
                            <th class="py-4 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">Duración</th>
                            <th class="py-4 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">Usuarios</th>
                            <th class="py-4 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">Multi-Suc.</th>
                            <th class="cursor-pointer select-none py-4 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400" (click)="toggleSort('is_active')">
                                Estado
                                <i class="pi ml-1" [class.pi-sort-up]="sortField() === 'is_active' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'is_active' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'is_active'"></i>
                            </th>
                            <th class="py-4 pr-6 text-right text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">Acción</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-surface-100 dark:divide-surface-800">
                        @for (plan of sortedPlans(); track plan.id) {
                            <tr class="hover:bg-surface-50 dark:hover:bg-surface-800/50 transition-colors">
                                <td class="py-4 pl-6 pr-4">
                                    <div class="font-medium text-surface-900 dark:text-surface-100">{{ plan.display_name || plan.name }}</div>
                                    <div class="text-xs text-surface-500 dark:text-surface-400">{{ plan.name }}</div>
                                </td>
                                <td class="py-4 pr-4 text-surface-600 dark:text-surface-300 max-w-xs truncate">{{ plan.description }}</td>
                                <td class="py-4 pr-4 font-medium text-surface-900 dark:text-surface-100">{{ plan.price | currency:'USD' }}</td>
                                <td class="py-4 pr-4 text-surface-600 dark:text-surface-300">{{ formatDuration(plan.duration_month) }}</td>
                                <td class="py-4 pr-4 text-surface-600 dark:text-surface-300">{{ plan.max_users || 'Ilimitado' }}</td>
                                <td class="py-4 pr-4">
                                    <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                                          [class.bg-emerald-100!]="plan.allows_multiple_branches"
                                          [class.text-emerald-700!]="plan.allows_multiple_branches"
                                          [class.dark:bg-emerald-900/30!]="plan.allows_multiple_branches"
                                          [class.dark:text-emerald-300!]="plan.allows_multiple_branches"
                                          [class.bg-surface-100!]="!plan.allows_multiple_branches"
                                          [class.text-surface-500!]="!plan.allows_multiple_branches"
                                          [class.dark:bg-surface-800!]="!plan.allows_multiple_branches"
                                          [class.dark:text-surface-400!]="!plan.allows_multiple_branches">
                                        {{ plan.allows_multiple_branches ? 'Si' : 'No' }}
                                    </span>
                                </td>
                                <td class="py-4 pr-4">
                                    <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                                          [class.bg-emerald-100!]="plan.is_active"
                                          [class.text-emerald-700!]="plan.is_active"
                                          [class.dark:bg-emerald-900/30!]="plan.is_active"
                                          [class.dark:text-emerald-300!]="plan.is_active"
                                          [class.bg-rose-100!]="!plan.is_active"
                                          [class.text-rose-700!]="!plan.is_active"
                                          [class.dark:bg-rose-900/30!]="!plan.is_active"
                                          [class.dark:text-rose-300!]="!plan.is_active">
                                        {{ plan.is_active ? 'Activo' : 'Inactivo' }}
                                    </span>
                                </td>
                                <td class="py-4 pr-6 text-right">
                                    <button pButton icon="pi pi-pencil" [rounded]="true" [text]="true" severity="info"
                                            (click)="editPlan(plan)"
                                            pTooltip="Editar plan" tooltipPosition="left"></button>
                                </td>
                            </tr>
                        } @empty {
                            <tr>
                                <td colspan="8" class="py-12 text-center text-surface-500 dark:text-surface-400">
                                    <i class="pi pi-credit-card text-3xl block mb-2 opacity-50"></i>
                                    No hay planes de suscripción
                                </td>
                            </tr>
                        }
                    </tbody>
                </table>
            </div>
            @if (totalPages() > 1) {
                <div class="flex items-center justify-between border-t border-surface-200 px-6 py-4 dark:border-surface-800">
                    <span class="text-sm text-surface-500 dark:text-surface-400">
                        Mostrando {{ (currentPage() - 1) * pageSize + 1 }}–{{ min(currentPage() * pageSize, filteredPlans().length) }} de {{ filteredPlans().length }}
                    </span>
                    <div class="flex items-center gap-2">
                        <button au-btn variant="ghost" [icon]="'pi pi-chevron-left'"
                                [disabled]="currentPage() === 1" (click)="prevPage()"></button>
                        @for (p of pages(); track p) {
                            <button au-btn [variant]="p === currentPage() ? 'primary' : 'ghost'"
                                    (click)="goToPage(p)">{{ p }}</button>
                        }
                        <button au-btn variant="ghost" [icon]="'pi pi-chevron-right'"
                                [disabled]="currentPage() === totalPages()" (click)="nextPage()"></button>
                    </div>
                </div>
            }
            </div>
        </div>

        <p-dialog [(visible)]="planDialog" [style]="{ width: '640px' }" [breakpoints]="{'960px':'75vw','640px':'100vw'}" header="Detalle del plan" [modal]="true">
            <ng-template #content>
                <div class="flex flex-col gap-6">
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label for="name" class="block font-bold mb-3">Nombre técnico</label>
                            <input type="text" pInputText id="name" [(ngModel)]="plan.name" [disabled]="true" fluid />
                            @if (submitted && !plan.name) {
                                <small class="text-red-500">El nombre es obligatorio.</small>
                            }
                        </div>

                        <div>
                            <label for="price" class="block font-bold mb-3">Precio (USD)</label>
                            <p-inputnumber id="price" [(ngModel)]="plan.price" mode="currency" currency="USD" locale="en-US" fluid />
                        </div>
                    </div>

                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label for="display_name" class="block font-bold mb-3">Nombre visible</label>
                            <input type="text" pInputText id="display_name" [ngModel]="plan.display_name || plan.name" [disabled]="true" fluid />
                            <small class="text-muted">Se deriva del tipo de plan y no se edita desde este panel.</small>
                        </div>

                        <div>
                            <label for="duration_month" class="block font-bold mb-3">Duración (meses)</label>
                            <p-inputnumber id="duration_month" [(ngModel)]="plan.duration_month" [min]="1" fluid />
                        </div>
                    </div>

                    <div>
                        <label for="description" class="block font-bold mb-3">Descripción</label>
                        <textarea id="description" pTextarea [(ngModel)]="plan.description" rows="3" fluid></textarea>
                    </div>

                    <div>
                        <label for="max_users" class="block font-bold mb-3">Máximo de usuarios activos</label>
                        <p-inputnumber id="max_users" [(ngModel)]="plan.max_users" [min]="1" fluid />
                        <small class="text-muted">Es el límite comercial efectivo del plan. Déjalo vacío para ilimitado.</small>
                    </div>

                    <div>
                        <label class="block font-bold mb-3">Funciones técnicas</label>
                        <div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                            <p class="text-sm text-gray-600 dark:text-gray-400 mb-2">Capacidades del sistema controladas por el plan:</p>
                            <div class="grid grid-cols-2 gap-2">
                                @for (feature of getFeaturesList(plan.features || plan.features_list); track feature) {
                                    <div class="flex items-center gap-2">
                                        <i class="pi pi-check text-green-500"></i>
                                        <span class="text-sm">{{ feature }}</span>
                                    </div>
                                }
                            </div>
                            <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">Las funciones técnicas se configuran automáticamente.</p>
                        </div>
                    </div>

                    <div>
                        <label class="block font-bold mb-3">Beneficios comerciales</label>
                        <div class="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg border border-blue-100 dark:border-blue-900/40">
                            <p class="text-sm text-gray-600 dark:text-gray-300 mb-2">Beneficios operativos o comerciales no gobernados por feature flags:</p>
                            @if ((plan.commercial_benefits || []).length) {
                                <div class="flex flex-col gap-2">
                                    @for (benefit of plan.commercial_benefits || []; track benefit) {
                                        <div class="flex items-center gap-2">
                                            <i class="pi pi-briefcase text-blue-500"></i>
                                            <span class="text-sm">{{ benefit }}</span>
                                        </div>
                                    }
                                </div>
                            } @else {
                                <p class="text-sm text-gray-500 dark:text-gray-400 m-0">Este plan no tiene beneficios comerciales adicionales definidos.</p>
                            }
                        </div>
                    </div>

                    <div class="flex items-center gap-2">
                        <input type="checkbox" id="allows_multiple_branches" [(ngModel)]="plan.allows_multiple_branches" />
                        <label for="allows_multiple_branches">Permite múltiples sucursales</label>
                    </div>

                    <div class="flex items-center gap-2">
                        <input type="checkbox" id="is_active" [(ngModel)]="plan.is_active" />
                        <label for="is_active">Activo</label>
                    </div>
                </div>
            </ng-template>

            <ng-template #footer>
                <p-button label="Cancelar" icon="pi pi-times" text (click)="hideDialog()" />
                <p-button label="Guardar" icon="pi pi-check" (click)="savePlan()" [loading]="saving()" />
            </ng-template>
        </p-dialog>

        <p-confirmdialog [style]="{ width: '450px' }" />
        <p-toast />
    `,
    providers: [MessageService, ConfirmationService]
})
export class SubscriptionPlans implements OnInit {
    private readonly errorLogger = inject(AdminErrorLogService);

    planDialog: boolean = false;
    plans = signal<SubscriptionPlan[]>([]);
    plan!: SubscriptionPlan;
    selectedPlans!: SubscriptionPlan[] | null;
    submitted: boolean = false;
    loading = signal(false);
    saving = signal(false);

    sortField = signal<string>('');
    sortOrder = signal<'asc' | 'desc'>('asc');
    globalFilter = signal('');
    currentPage = signal(1);
    pageSize = 10;

    filteredPlans = computed(() => {
        const visible = this.plans().filter(p => p.is_public !== false);
        const filter = this.globalFilter().toLowerCase();
        if (!filter) return visible;
        return visible.filter(p =>
            (p.name?.toLowerCase() || '').includes(filter) ||
            (p.display_name?.toLowerCase() || '').includes(filter) ||
            (p.description?.toLowerCase() || '').includes(filter) ||
            (p.price?.toString() || '').includes(filter)
        );
    });

    sortedPlans = computed(() => {
        const field = this.sortField();
        const order = this.sortOrder();
        const list = [...this.filteredPlans()];

        if (!field) return list;

        list.sort((a: any, b: any) => {
            const aVal = a[field] ?? '';
            const bVal = b[field] ?? '';
            const cmp = typeof aVal === 'string' ? aVal.localeCompare(bVal) : (aVal > bVal ? 1 : -1);
            return order === 'asc' ? cmp : -cmp;
        });

        const start = (this.currentPage() - 1) * this.pageSize;
        return list.slice(start, start + this.pageSize);
    });

    totalPages = computed(() => Math.max(1, Math.ceil(this.filteredPlans().length / this.pageSize)));

    pages = computed(() => {
        const tp = this.totalPages();
        return Array.from({ length: tp }, (_, i) => i + 1);
    });

    constructor(
        private destroyRef: DestroyRef,
        private subscriptionService: SubscriptionService,
        private messageService: MessageService,
        private confirmationService: ConfirmationService
    ) {}

    ngOnInit() {
        this.loadPlans();
    }

    loadPlans() {
        this.loading.set(true);
        this.subscriptionService.getPlans().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (data: any) => {
                const plans = Array.isArray(data) ? data : (data.results || []);
                this.plans.set(plans);
                this.loading.set(false);
            },
            error: (error: any) => {
                this.showErrorMessage('Error al cargar los planes', error);
                this.plans.set([]);
                this.loading.set(false);
            }
        });
    }

    onSearch(event: Event) {
        this.globalFilter.set((event.target as HTMLInputElement).value);
        this.currentPage.set(1);
    }

    toggleSort(field: string) {
        if (this.sortField() === field) {
            this.sortOrder.set(this.sortOrder() === 'asc' ? 'desc' : 'asc');
        } else {
            this.sortField.set(field);
            this.sortOrder.set('asc');
        }
        this.currentPage.set(1);
    }

    prevPage() {
        if (this.currentPage() > 1) this.currentPage.update(p => p - 1);
    }

    nextPage() {
        if (this.currentPage() < this.totalPages()) this.currentPage.update(p => p + 1);
    }

    goToPage(page: number) {
        this.currentPage.set(page);
    }

    min(a: number, b: number): number {
        return Math.min(a, b);
    }

    openNew() {
        this.plan = {} as SubscriptionPlan;
        this.submitted = false;
        this.planDialog = true;
    }

    editPlan(plan: SubscriptionPlan) {
        this.plan = { ...plan };
        this.planDialog = true;
    }

    hideDialog() {
        this.planDialog = false;
        this.submitted = false;
    }

    getFeaturesList(features: any): string[] {
        if (!features) return [];
        if (Array.isArray(features)) {
            return features;
        }
        if (typeof features === 'object' && features !== null) {
            try {
                return Object.entries(features)
                    .filter(([_, value]) => value === true)
                    .map(([key]) => this.translateFeature(key));
            } catch {
                return [];
            }
        }
        return [];
    }

    private translateFeature(key: string): string {
        const translations: { [key: string]: string } = {
            appointments: 'Gestión de Citas',
            reports: 'Reportes e Analíticas',
            multi_location: 'Sucursales básicas (aislamiento avanzado en desarrollo)',
            custom_branding: 'Marca Personalizada',
            priority_support: 'Soporte Prioritario',
            cash_register: 'Caja y Ventas',
            client_history: 'Historial de Clientes',
            export_reports: 'Exportación a Excel',
            whatsapp_notifications: 'Notificaciones por WhatsApp',
        };
        return translations[key] || key;
    }

    formatDuration(durationMonths?: number): string {
        if (!durationMonths || durationMonths <= 1) {
            return '1 mes';
        }
        return `${durationMonths} meses`;
    }

    savePlan() {
        this.submitted = true;

        if (this.plan.name?.trim()) {
            this.saving.set(true);

            if (this.plan.id) {
                this.subscriptionService.updatePlan(this.plan.id, {
                    description: this.plan.description,
                    price: this.plan.price,
                    duration_month: this.plan.duration_month,
                    max_users: this.plan.max_users,
                    allows_multiple_branches: this.plan.allows_multiple_branches,
                    is_active: this.plan.is_active
                }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
                    next: (updatedPlan: any) => {
                        const plans = this.plans();
                        const index = plans.findIndex(p => p.id === this.plan.id);
                        if (index !== -1) {
                            plans[index] = updatedPlan;
                            this.plans.set([...plans]);
                        }
                        this.messageService.add({
                            severity: 'success',
                            summary: 'Exitoso',
                            detail: 'Plan actualizado correctamente',
                            life: 3000
                        });
                        this.planDialog = false;
                        this.saving.set(false);
                    },
                    error: (error: any) => {
                        this.showErrorMessage('Error al actualizar el plan', error);
                        this.saving.set(false);
                    }
                });
            }
        }
    }

    trackByPlan(index: number, plan: SubscriptionPlan): any {
        return plan.id || index;
    }

    trackByFeature(index: number, value: string): any {
        return value || index;
    }

    private showErrorMessage(message: string, error?: any): void {
        this.logError(message, error);
        this.messageService.add({
            severity: 'error',
            summary: 'Error',
            detail: this.sanitizeErrorMessage(error, message),
            life: 3000
        });
    }

    private sanitizeErrorMessage(error: any, fallback: string): string {
        const errorMessage = error?.error?.message || error?.message;
        return typeof errorMessage === 'string' ? errorMessage.substring(0, 200) : fallback;
    }

    private logError(context: string, error: any): void {
        this.errorLogger.log('SubscriptionPlans', context, error);
    }
}
