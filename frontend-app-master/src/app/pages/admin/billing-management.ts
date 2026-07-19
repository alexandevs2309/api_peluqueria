import { Component, DestroyRef, OnInit, inject, computed, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { DialogModule } from 'primeng/dialog';
import { DatePipe, CurrencyPipe } from '@angular/common';
import { BillingService } from '../../core/services/billing.service';
import { TenantService } from '../../core/services/tenant/tenant.service';
import { SettingsService } from '../../core/services/settings.service';
import { MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';
import { TooltipModule } from 'primeng/tooltip';
import { AuBtn } from '../../shared/components';
import { AdminErrorLogService } from '../../core/services/admin-error-log.service';
import { getSubscriptionPlanLabel } from '../../core/utils/subscription-plan-label';

interface Invoice {
    id?: number;
    user?: {
        id: number;
        email: string;
        full_name: string;
    };
    user_email?: string;
    user_name?: string;
    tenant_name?: string;
    plan_name?: string;
    subscription?: {
        id: number;
        plan?: {
            id: number;
            name: string;
        };
    };
    amount?: number;
    status?: string;
    description?: string;
    issued_at?: string;
    due_date?: string;
    paid_at?: string;
    is_paid?: boolean;
    payment_method?: string;
}

interface BillingStats {
    total_revenue: number;
    pending_payments: number;
    overdue_invoices: number;
    active_subscriptions: number;
}

@Component({
    selector: 'app-billing-management',
    standalone: true,
    imports: [
        FormsModule, ButtonModule, InputTextModule,
        DialogModule, DatePipe, CurrencyPipe, ToastModule, TooltipModule, AuBtn
    ],
    providers: [MessageService],
    template: `
        <p-toast></p-toast>

        <section class="mb-8 overflow-hidden rounded-[2rem] border border-surface-200/70 bg-surface-0 shadow-[0_24px_80px_-42px_rgba(15,23,42,0.45)] dark:border-surface-800 dark:bg-surface-900">
            <div class="relative overflow-hidden px-8 py-8 lg:px-10">
                <div class="hero-gradient"></div>
                <div class="relative grid gap-8 lg:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.9fr)] lg:items-start">
                    <div>
                        <div class="mb-4 inline-flex items-center gap-2 rounded-full border border-surface-200 bg-surface-50/90 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.24em] text-surface-600 dark:border-surface-700 dark:bg-surface-800/80 dark:text-surface-300">
                            <i class="pi pi-wallet text-emerald-500"></i>
                            Billing control
                        </div>
                        <h1 class="max-w-3xl text-3xl font-semibold tracking-tight text-surface-950 dark:text-surface-0 lg:text-4xl">
                            Facturación, cobros y salud de ingresos del SaaS
                        </h1>
                        <p class="mt-3 max-w-2xl text-base leading-7 text-surface-600 dark:text-surface-300">
                            Gestiona facturas, morosidad y generación manual desde un panel más claro y más ejecutivo.
                        </p>
                    </div>
                    <div class="rounded-3xl border border-surface-200 bg-white/80 p-5 shadow-sm backdrop-blur dark:border-surface-700 dark:bg-surface-800/80">
                        <div class="text-xs font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">Lectura rápida</div>
                        <div class="mt-4 grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
                            <div class="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 dark:border-emerald-900/60 dark:bg-emerald-900/10">
                                <div class="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700 dark:text-emerald-300">Ingresos</div>
                                <div class="mt-2 text-2xl font-semibold text-emerald-900 dark:text-emerald-100">{{ stats().total_revenue | currency:currencyCode() }}</div>
                            </div>
                            <div class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 dark:border-amber-900/60 dark:bg-amber-900/10">
                                <div class="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700 dark:text-amber-300">Pendiente</div>
                                <div class="mt-2 text-2xl font-semibold text-amber-900 dark:text-amber-100">{{ stats().pending_payments | currency:currencyCode() }}</div>
                            </div>
                            <div class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 dark:border-rose-900/60 dark:bg-rose-900/10">
                                <div class="text-xs font-semibold uppercase tracking-[0.18em] text-rose-700 dark:text-rose-300">Riesgo</div>
                                <div class="mt-2 text-2xl font-semibold text-rose-900 dark:text-rose-100">{{ stats().overdue_invoices }}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Stat cards -->
        <div class="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
            <div class="rounded-2xl border border-emerald-200 bg-emerald-50/80 p-5 dark:border-emerald-900/60 dark:bg-emerald-900/10">
                <div class="flex items-center justify-between">
                    <div>
                        <div class="text-2xl font-bold text-emerald-700 dark:text-emerald-300">{{ stats().total_revenue | currency:currencyCode() }}</div>
                        <div class="mt-1 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-600 dark:text-emerald-400">Ingresos totales</div>
                    </div>
                    <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-100 text-emerald-600 dark:bg-emerald-900/40 dark:text-emerald-300">
                        <i class="pi pi-dollar text-lg"></i>
                    </div>
                </div>
            </div>
            <div class="rounded-2xl border border-amber-200 bg-amber-50/80 p-5 dark:border-amber-900/60 dark:bg-amber-900/10">
                <div class="flex items-center justify-between">
                    <div>
                        <div class="text-2xl font-bold text-amber-700 dark:text-amber-300">{{ stats().pending_payments | currency:currencyCode() }}</div>
                        <div class="mt-1 text-xs font-semibold uppercase tracking-[0.18em] text-amber-600 dark:text-amber-400">Pagos pendientes</div>
                    </div>
                    <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 text-amber-600 dark:bg-amber-900/40 dark:text-amber-300">
                        <i class="pi pi-clock text-lg"></i>
                    </div>
                </div>
            </div>
            <div class="rounded-2xl border border-rose-200 bg-rose-50/80 p-5 dark:border-rose-900/60 dark:bg-rose-900/10">
                <div class="flex items-center justify-between">
                    <div>
                        <div class="text-2xl font-bold text-rose-700 dark:text-rose-300">{{ stats().overdue_invoices }}</div>
                        <div class="mt-1 text-xs font-semibold uppercase tracking-[0.18em] text-rose-600 dark:text-rose-400">Facturas vencidas</div>
                    </div>
                    <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-100 text-rose-600 dark:bg-rose-900/40 dark:text-rose-300">
                        <i class="pi pi-exclamation-triangle text-lg"></i>
                    </div>
                </div>
            </div>
            <div class="rounded-2xl border border-violet-200 bg-violet-50/80 p-5 dark:border-violet-900/60 dark:bg-violet-900/10">
                <div class="flex items-center justify-between">
                    <div>
                        <div class="text-2xl font-bold text-violet-700 dark:text-violet-300">{{ stats().active_subscriptions }}</div>
                        <div class="mt-1 text-xs font-semibold uppercase tracking-[0.18em] text-violet-600 dark:text-violet-400">Suscripciones activas</div>
                    </div>
                    <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-100 text-violet-600 dark:bg-violet-900/40 dark:text-violet-300">
                        <i class="pi pi-users text-lg"></i>
                    </div>
                </div>
            </div>
        </div>

        <!-- Table section -->
        <div class="overflow-hidden rounded-[2rem] border border-surface-200/70 bg-surface-0 shadow-[0_24px_80px_-42px_rgba(15,23,42,0.45)] dark:border-surface-800 dark:bg-surface-900">
            <div class="flex flex-wrap items-center justify-between gap-4 border-b border-surface-200 px-6 py-5 dark:border-surface-800">
                <div>
                    <div class="text-xs font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">Cobranza</div>
                    <div class="mt-1 text-lg font-semibold text-surface-950 dark:text-surface-0">Listado de facturas y estado operativo</div>
                </div>
                <div class="flex items-center gap-3">
                    <select [(ngModel)]="selectedStatus" (change)="onStatusFilter()"
                            class="rounded-lg border border-surface-200 bg-surface-0 px-3 py-2 text-sm text-surface-700 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-200">
                        <option [ngValue]="null">Todos los estados</option>
                        <option value="pending">Pendiente</option>
                        <option value="paid">Pagada</option>
                        <option value="failed">Fallida</option>
                        <option value="overdue">Vencida</option>
                        <option value="canceled">Cancelada</option>
                    </select>
                    <div class="relative">
                        <i class="pi pi-search absolute left-3 top-1/2 -translate-y-1/2 text-surface-400 text-sm"></i>
                        <input
                            type="text"
                            placeholder="Buscar facturas..."
                            (input)="onSearch($event)"
                            class="w-48 rounded-lg border border-surface-200 bg-surface-0 py-2 pl-9 pr-3 text-sm text-surface-700 placeholder:text-surface-400 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-200 dark:placeholder:text-surface-500"
                        />
                    </div>
                    <button au-btn [icon]="'pi pi-plus'" (click)="showGenerateDialog = true">Generar factura</button>
                </div>
            </div>

            <!-- Móvil: Tarjetas apiladas -->
            <div class="block md:hidden p-1 space-y-3">
                @for (invoice of displayInvoices(); track invoice.id) {
                    <div class="bg-white dark:bg-surface-900 rounded-xl border border-surface-200 dark:border-surface-800 shadow-sm overflow-hidden">
                        <div class="p-4">
                            <div class="flex items-start justify-between mb-3">
                                <div>
                                    <h4 class="font-bold text-surface-900 dark:text-white">#{{ invoice.id }}</h4>
                                    <p class="text-xs text-surface-500 dark:text-surface-400 mt-0.5">{{ invoice.tenant_name || invoice.user_name || '—' }}</p>
                                </div>
                                <span class="font-bold text-surface-900 dark:text-white">{{ invoice.amount | currency:currencyCode() }}</span>
                            </div>
                            <div class="space-y-2 text-sm">
                                <div class="flex justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Plan</span>
                                    <span class="text-surface-700 dark:text-surface-200">{{ getPlanDisplayName(invoice) }}</span>
                                </div>
                                <div class="flex items-center justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Estado</span>
                                    <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                                          [class.bg-emerald-100!]="getInvoiceDisplayStatus(invoice) === 'paid'"
                                          [class.text-emerald-700!]="getInvoiceDisplayStatus(invoice) === 'paid'"
                                          [class.dark:bg-emerald-900/30!]="getInvoiceDisplayStatus(invoice) === 'paid'"
                                          [class.dark:text-emerald-300!]="getInvoiceDisplayStatus(invoice) === 'paid'"
                                          [class.bg-amber-100!]="getInvoiceDisplayStatus(invoice) === 'pending'"
                                          [class.text-amber-700!]="getInvoiceDisplayStatus(invoice) === 'pending'"
                                          [class.dark:bg-amber-900/30!]="getInvoiceDisplayStatus(invoice) === 'pending'"
                                          [class.dark:text-amber-300!]="getInvoiceDisplayStatus(invoice) === 'pending'"
                                          [class.bg-rose-100!]="getInvoiceDisplayStatus(invoice) === 'overdue' || getInvoiceDisplayStatus(invoice) === 'failed'"
                                          [class.text-rose-700!]="getInvoiceDisplayStatus(invoice) === 'overdue' || getInvoiceDisplayStatus(invoice) === 'failed'"
                                          [class.dark:bg-rose-900/30!]="getInvoiceDisplayStatus(invoice) === 'overdue' || getInvoiceDisplayStatus(invoice) === 'failed'"
                                          [class.dark:text-rose-300!]="getInvoiceDisplayStatus(invoice) === 'overdue' || getInvoiceDisplayStatus(invoice) === 'failed'"
                                          [class.bg-surface-100!]="getInvoiceDisplayStatus(invoice) === 'canceled'"
                                          [class.text-surface-500!]="getInvoiceDisplayStatus(invoice) === 'canceled'"
                                          [class.dark:bg-surface-800!]="getInvoiceDisplayStatus(invoice) === 'canceled'"
                                          [class.dark:text-surface-400!]="getInvoiceDisplayStatus(invoice) === 'canceled'">
                                        {{ getInvoiceDisplayStatusText(invoice) }}
                                    </span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Usuario</span>
                                    <span class="text-surface-500 dark:text-surface-400">{{ invoice.user_email || invoice.user?.email || '' }}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Emisión</span>
                                    <span class="text-surface-500 dark:text-surface-400">{{ invoice.issued_at | date:'mediumDate' }}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Vencimiento</span>
                                    <span class="text-surface-500 dark:text-surface-400">{{ invoice.due_date | date:'mediumDate' }}</span>
                                </div>
                            </div>
                            <div class="flex items-center justify-end gap-2 pt-3 mt-3 border-t border-surface-100 dark:border-surface-800">
                                <button au-btn variant="ghost" [icon]="'pi pi-eye'"
                                        (click)="viewInvoice(invoice)"></button>
                                @if (!invoice.is_paid) {
                                    <button au-btn variant="ghost" [icon]="'pi pi-check'"
                                            (click)="markAsPaid(invoice)"></button>
                                }
                                <button au-btn variant="ghost" [icon]="'pi pi-print'"
                                        (click)="downloadInvoice(invoice)"></button>
                            </div>
                        </div>
                    </div>
                } @empty {
                    <div class="py-8 text-center text-surface-500 dark:text-surface-400">
                        <i class="pi pi-file-text text-3xl block mb-2 opacity-50"></i>
                        No se encontraron facturas.
                    </div>
                }
                @if (totalPages() > 1) {
                    <div class="flex items-center justify-between px-2 py-2">
                        <span class="text-sm text-surface-500 dark:text-surface-400">{{ (currentPage() - 1) * pageSize + 1 }}–{{ min(currentPage() * pageSize, filteredInvoices().length) }} de {{ filteredInvoices().length }}</span>
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
                            <th class="cursor-pointer select-none py-4 pl-6 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400" (click)="toggleSort('id')">
                                ID
                                <i class="pi ml-1" [class.pi-sort-up]="sortField() === 'id' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'id' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'id'"></i>
                            </th>
                            <th class="py-4 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">Tenant / User</th>
                            <th class="py-4 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">Plan</th>
                            <th class="cursor-pointer select-none py-4 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400" (click)="toggleSort('amount')">
                                Monto
                                <i class="pi ml-1" [class.pi-sort-up]="sortField() === 'amount' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'amount' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'amount'"></i>
                            </th>
                            <th class="py-4 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">Estado</th>
                            <th class="cursor-pointer select-none py-4 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400" (click)="toggleSort('issued_at')">
                                Emisión
                                <i class="pi ml-1" [class.pi-sort-up]="sortField() === 'issued_at' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'issued_at' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'issued_at'"></i>
                            </th>
                            <th class="cursor-pointer select-none py-4 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400" (click)="toggleSort('due_date')">
                                Vencimiento
                                <i class="pi ml-1" [class.pi-sort-up]="sortField() === 'due_date' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'due_date' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'due_date'"></i>
                            </th>
                            <th class="py-4 pr-6 text-right text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">Acción</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-surface-100 dark:divide-surface-800">
                        @for (invoice of displayInvoices(); track invoice.id) {
                            <tr class="hover:bg-surface-50 dark:hover:bg-surface-800/50 transition-colors">
                                <td class="py-4 pl-6 pr-4 font-medium text-surface-900 dark:text-surface-100">#{{ invoice.id }}</td>
                                <td class="py-4 pr-4">
                                    <div class="font-medium text-surface-900 dark:text-surface-100">{{ invoice.tenant_name || invoice.user_name || '—' }}</div>
                                    <div class="text-xs text-surface-500 dark:text-surface-400">{{ invoice.user_email || invoice.user?.email || '' }}</div>
                                </td>
                                <td class="py-4 pr-4 text-surface-600 dark:text-surface-300">{{ getPlanDisplayName(invoice) }}</td>
                                <td class="py-4 pr-4 font-medium text-surface-900 dark:text-surface-100">{{ invoice.amount | currency:currencyCode() }}</td>
                                <td class="py-4 pr-4">
                                    <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                                          [class.bg-emerald-100!]="getInvoiceDisplayStatus(invoice) === 'paid'"
                                          [class.text-emerald-700!]="getInvoiceDisplayStatus(invoice) === 'paid'"
                                          [class.dark:bg-emerald-900/30!]="getInvoiceDisplayStatus(invoice) === 'paid'"
                                          [class.dark:text-emerald-300!]="getInvoiceDisplayStatus(invoice) === 'paid'"
                                          [class.bg-amber-100!]="getInvoiceDisplayStatus(invoice) === 'pending'"
                                          [class.text-amber-700!]="getInvoiceDisplayStatus(invoice) === 'pending'"
                                          [class.dark:bg-amber-900/30!]="getInvoiceDisplayStatus(invoice) === 'pending'"
                                          [class.dark:text-amber-300!]="getInvoiceDisplayStatus(invoice) === 'pending'"
                                          [class.bg-rose-100!]="getInvoiceDisplayStatus(invoice) === 'overdue' || getInvoiceDisplayStatus(invoice) === 'failed'"
                                          [class.text-rose-700!]="getInvoiceDisplayStatus(invoice) === 'overdue' || getInvoiceDisplayStatus(invoice) === 'failed'"
                                          [class.dark:bg-rose-900/30!]="getInvoiceDisplayStatus(invoice) === 'overdue' || getInvoiceDisplayStatus(invoice) === 'failed'"
                                          [class.dark:text-rose-300!]="getInvoiceDisplayStatus(invoice) === 'overdue' || getInvoiceDisplayStatus(invoice) === 'failed'"
                                          [class.bg-surface-100!]="getInvoiceDisplayStatus(invoice) === 'canceled'"
                                          [class.text-surface-500!]="getInvoiceDisplayStatus(invoice) === 'canceled'"
                                          [class.dark:bg-surface-800!]="getInvoiceDisplayStatus(invoice) === 'canceled'"
                                          [class.dark:text-surface-400!]="getInvoiceDisplayStatus(invoice) === 'canceled'">
                                        {{ getInvoiceDisplayStatusText(invoice) }}
                                    </span>
                                </td>
                                <td class="py-4 pr-4 text-surface-600 dark:text-surface-300">{{ invoice.issued_at | date:'mediumDate' }}</td>
                                <td class="py-4 pr-4 text-surface-600 dark:text-surface-300">{{ invoice.due_date | date:'mediumDate' }}</td>
                                <td class="py-4 pr-6 text-right">
                                    <div class="flex items-center justify-end gap-1">
                                        <button pButton icon="pi pi-eye" [rounded]="true" [text]="true" severity="info"
                                                (click)="viewInvoice(invoice)" pTooltip="Ver detalle" tooltipPosition="left"></button>
                                        @if (!invoice.is_paid) {
                                            <button pButton icon="pi pi-check" [rounded]="true" [text]="true" severity="success"
                                                    (click)="markAsPaid(invoice)" pTooltip="Marcar como pagada" tooltipPosition="left"></button>
                                        }
                                        <button pButton icon="pi pi-print" [rounded]="true" [text]="true" severity="secondary"
                                                (click)="downloadInvoice(invoice)" pTooltip="Imprimir o guardar como PDF" tooltipPosition="left"></button>
                                    </div>
                                </td>
                            </tr>
                        } @empty {
                            <tr>
                                <td colspan="8" class="py-12 text-center text-surface-500 dark:text-surface-400">
                                    <i class="pi pi-file-text text-3xl block mb-2 opacity-50"></i>
                                    No se encontraron facturas.
                                </td>
                            </tr>
                        }
                    </tbody>
                </table>
            </div>
            </div>
            @if (totalPages() > 1) {
                <div class="flex items-center justify-between border-t border-surface-200 px-6 py-4 dark:border-surface-800">
                    <span class="text-sm text-surface-500 dark:text-surface-400">
                        Mostrando {{ (currentPage() - 1) * pageSize + 1 }}–{{ min(currentPage() * pageSize, filteredInvoices().length) }} de {{ filteredInvoices().length }}
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

        <!-- Generate Invoice Dialog -->
        <p-dialog [(visible)]="showGenerateDialog" [style]="{ width: '450px' }" [breakpoints]="{'960px':'75vw','640px':'100vw'}" header="Generar factura" [modal]="true">
            <ng-template #content>
                <div class="flex flex-col gap-4">
                    <div class="rounded-2xl border border-surface-200 bg-surface-50 p-4 text-sm text-surface-600 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-300">
                        Crea una factura manual usando el plan activo del tenant y deja el cobro listo desde administración.
                    </div>
                    <div>
                        <label class="block font-bold mb-2">Tenant</label>
                        <select [(ngModel)]="newInvoice.tenant"
                                class="w-full rounded-lg border border-surface-200 bg-surface-0 px-3 py-2 text-sm text-surface-700 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-200">
                            <option [ngValue]="null" disabled>Selecciona un tenant</option>
                            @for (t of tenantOptions(); track t.id) {
                                <option [ngValue]="t.id">{{ t.name }}</option>
                            }
                        </select>
                    </div>
                    <div>
                        <label class="block font-bold mb-2">Descripción (opcional)</label>
                        <input type="text" pInputText [(ngModel)]="newInvoice.description" placeholder="Factura manual de suscripción" fluid />
                    </div>
                    <div>
                        <label class="block font-bold mb-2">Fecha de vencimiento</label>
                        <input type="date" pInputText [(ngModel)]="newInvoice.due_date" fluid />
                    </div>
                    <small class="text-gray-500">
                        El monto se calcula automáticamente usando el plan activo del tenant.
                    </small>
                </div>
            </ng-template>

            <ng-template #footer>
                <p-button label="Cancelar" icon="pi pi-times" text (click)="showGenerateDialog = false" />
                <p-button label="Generar" icon="pi pi-check" (click)="generateInvoice()" />
            </ng-template>
        </p-dialog>

        <p-dialog [(visible)]="showInvoiceDetailDialog" [style]="{ width: '42rem' }" [breakpoints]="{'960px':'75vw','640px':'100vw'}" header="Detalle de factura" [modal]="true">
            <ng-template #content>
                @if (invoiceDetailLoading()) {
                    <div class="py-8 text-center text-gray-500">Cargando detalle...</div>
                } @else if (selectedInvoice(); as invoice) {
                    <div class="grid gap-4 md:grid-cols-2">
                        <div class="rounded-2xl border border-surface-200 p-4 dark:border-surface-700">
                            <div class="text-xs font-semibold uppercase tracking-[0.18em] text-surface-500 dark:text-surface-400">Factura</div>
                            <div class="mt-3 text-2xl font-semibold text-surface-950 dark:text-surface-0">#{{ invoice.id }}</div>
                            <div class="mt-2">
                                <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                                      [class.bg-emerald-100!]="getInvoiceDisplayStatus(invoice) === 'paid'"
                                      [class.text-emerald-700!]="getInvoiceDisplayStatus(invoice) === 'paid'"
                                      [class.dark:bg-emerald-900/30!]="getInvoiceDisplayStatus(invoice) === 'paid'"
                                      [class.dark:text-emerald-300!]="getInvoiceDisplayStatus(invoice) === 'paid'"
                                      [class.bg-amber-100!]="getInvoiceDisplayStatus(invoice) === 'pending'"
                                      [class.text-amber-700!]="getInvoiceDisplayStatus(invoice) === 'pending'"
                                      [class.dark:bg-amber-900/30!]="getInvoiceDisplayStatus(invoice) === 'pending'"
                                      [class.dark:text-amber-300!]="getInvoiceDisplayStatus(invoice) === 'pending'"
                                      [class.bg-rose-100!]="getInvoiceDisplayStatus(invoice) === 'overdue' || getInvoiceDisplayStatus(invoice) === 'failed'"
                                      [class.text-rose-700!]="getInvoiceDisplayStatus(invoice) === 'overdue' || getInvoiceDisplayStatus(invoice) === 'failed'"
                                      [class.dark:bg-rose-900/30!]="getInvoiceDisplayStatus(invoice) === 'overdue' || getInvoiceDisplayStatus(invoice) === 'failed'"
                                      [class.dark:text-rose-300!]="getInvoiceDisplayStatus(invoice) === 'overdue' || getInvoiceDisplayStatus(invoice) === 'failed'"
                                      [class.bg-surface-100!]="getInvoiceDisplayStatus(invoice) === 'canceled'"
                                      [class.text-surface-500!]="getInvoiceDisplayStatus(invoice) === 'canceled'"
                                      [class.dark:bg-surface-800!]="getInvoiceDisplayStatus(invoice) === 'canceled'"
                                      [class.dark:text-surface-400!]="getInvoiceDisplayStatus(invoice) === 'canceled'">
                                    {{ getInvoiceDisplayStatusText(invoice) }}
                                </span>
                            </div>
                        </div>
                        <div class="rounded-2xl border border-surface-200 p-4 dark:border-surface-700">
                            <div class="text-xs font-semibold uppercase tracking-[0.18em] text-surface-500 dark:text-surface-400">Monto</div>
                            <div class="mt-3 text-2xl font-semibold text-surface-950 dark:text-surface-0">{{ invoice.amount | currency:currencyCode() }}</div>
                            <div class="mt-2 text-sm text-surface-500 dark:text-surface-400">{{ invoice.payment_method || 'Método no registrado' }}</div>
                        </div>
                        <div class="rounded-2xl border border-surface-200 p-4 dark:border-surface-700">
                            <div class="text-xs font-semibold uppercase tracking-[0.18em] text-surface-500 dark:text-surface-400">Tenant / Usuario</div>
                            <div class="mt-3 font-medium text-surface-900 dark:text-surface-100">{{ invoice.tenant_name || invoice.user_name || '—' }}</div>
                            <div class="mt-1 text-sm text-surface-500 dark:text-surface-400">{{ invoice.user_email || invoice.user?.email || 'Sin correo' }}</div>
                        </div>
                        <div class="rounded-2xl border border-surface-200 p-4 dark:border-surface-700">
                            <div class="text-xs font-semibold uppercase tracking-[0.18em] text-surface-500 dark:text-surface-400">Plan</div>
                            <div class="mt-3 font-medium text-surface-900 dark:text-surface-100">{{ getPlanDisplayName(invoice) }}</div>
                            <div class="mt-1 text-sm text-surface-500 dark:text-surface-400">Suscripción #{{ invoice.subscription?.id || '—' }}</div>
                        </div>
                        <div class="rounded-2xl border border-surface-200 p-4 dark:border-surface-700">
                            <div class="text-xs font-semibold uppercase tracking-[0.18em] text-surface-500 dark:text-surface-400">Emisión</div>
                            <div class="mt-3 font-medium text-surface-900 dark:text-surface-100">{{ invoice.issued_at | date:'medium' }}</div>
                        </div>
                        <div class="rounded-2xl border border-surface-200 p-4 dark:border-surface-700">
                            <div class="text-xs font-semibold uppercase tracking-[0.18em] text-surface-500 dark:text-surface-400">Vencimiento</div>
                            <div class="mt-3 font-medium text-surface-900 dark:text-surface-100">{{ invoice.due_date | date:'mediumDate' }}</div>
                            <div class="mt-1 text-sm text-surface-500 dark:text-surface-400">Pagada: {{ invoice.paid_at ? (invoice.paid_at | date:'medium') : 'No' }}</div>
                        </div>
                    </div>
                    @if (invoice.description) {
                        <div class="mt-4 rounded-2xl border border-surface-200 p-4 text-sm text-surface-600 dark:border-surface-700 dark:text-surface-300">
                            {{ invoice.description }}
                        </div>
                    }
                } @else {
                    <div class="py-8 text-center text-gray-500">No hay factura seleccionada.</div>
                }
            </ng-template>

            <ng-template #footer>
                <p-button label="Cerrar" icon="pi pi-times" text (click)="showInvoiceDetailDialog = false" />
                @if (selectedInvoice(); as invoice) {
                    @if (!invoice.is_paid) {
                        <p-button label="Marcar pagada" icon="pi pi-check" severity="success" [outlined]="true" (click)="markAsPaid(invoice)" />
                    }
                    <p-button label="Imprimir" icon="pi pi-print" severity="secondary" [outlined]="true" (click)="downloadInvoice(invoice)" />
                }
            </ng-template>
        </p-dialog>
    `
})
export class BillingManagement implements OnInit {
    private readonly errorLogger = inject(AdminErrorLogService);
    invoices = signal<Invoice[]>([]);
    stats = signal<BillingStats>({ total_revenue: 0, pending_payments: 0, overdue_invoices: 0, active_subscriptions: 0 });
    loading = signal(false);
    currencyCode = signal('USD');
    selectedStatus = signal<string | null>(null);
    showGenerateDialog = false;
    showInvoiceDetailDialog = false;
    invoiceDetailLoading = signal(false);
    selectedInvoice = signal<Invoice | null>(null);

    sortField = signal<string>('');
    sortOrder = signal<'asc' | 'desc'>('asc');
    globalFilter = signal('');
    currentPage = signal(1);
    pageSize = 10;

    newInvoice = {
        tenant: null,
        description: '',
        due_date: null
    };

    tenantOptions = signal<any[]>([]);

    filteredInvoices = computed(() => {
        let list = this.invoices();

        const status = this.selectedStatus();
        if (status) {
            list = list.filter(invoice => this.getInvoiceDisplayStatus(invoice) === status);
        }

        const filter = this.globalFilter().toLowerCase();
        if (filter) {
            list = list.filter(invoice =>
                invoice.user_email?.toLowerCase().includes(filter) ||
                invoice.tenant_name?.toLowerCase().includes(filter) ||
                invoice.plan_name?.toLowerCase().includes(filter) ||
                invoice.description?.toLowerCase().includes(filter)
            );
        }

        return list;
    });

    sortedInvoices = computed(() => {
        const field = this.sortField();
        const order = this.sortOrder();
        const list = [...this.filteredInvoices()];

        if (!field) return list;

        list.sort((a: any, b: any) => {
            const aVal = a[field] ?? '';
            const bVal = b[field] ?? '';
            const cmp = typeof aVal === 'string' ? aVal.localeCompare(bVal) : (aVal > bVal ? 1 : -1);
            return order === 'asc' ? cmp : -cmp;
        });

        return list;
    });

    displayInvoices = computed(() => {
        const start = (this.currentPage() - 1) * this.pageSize;
        return this.sortedInvoices().slice(start, start + this.pageSize);
    });

    totalPages = computed(() => Math.max(1, Math.ceil(this.filteredInvoices().length / this.pageSize)));

    pages = computed(() => {
        const tp = this.totalPages();
        return Array.from({ length: tp }, (_, i) => i + 1);
    });

    constructor(
        private destroyRef: DestroyRef,
        private billingService: BillingService,
        private tenantService: TenantService,
        private settingsService: SettingsService,
        private messageService: MessageService
    ) {}

    ngOnInit() {
        this.loadCurrency();
        this.loadInvoices();
        this.loadTenants();
    }

    loadCurrency() {
        this.settingsService.getSettings().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (settings) => {
                if (settings?.default_currency) {
                    this.currencyCode.set(settings.default_currency);
                }
            },
            error: () => {}
        });
    }

    loadInvoices() {
        this.loading.set(true);
        this.billingService.getInvoices().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (response: any) => {
                const invoices = response.results || response || [];
                this.invoices.set(invoices);
                this.currentPage.set(1);
                this.loadStats();
                this.loading.set(false);
            },
            error: (error) => this.handleLoadError(error)
        });
    }

    loadTenants() {
        this.tenantService.getTenants().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (data: any) => {
                const tenants = Array.isArray(data) ? data : data.results || [];
                this.tenantOptions.set(tenants.map((t: any) => ({ name: t.name, id: t.id })));
            },
            error: () => {
                this.tenantOptions.set([]);
            }
        });
    }

    loadStats() {
        this.billingService.getAdminStats().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (stats: any) => {
                this.stats.set({
                    total_revenue: Number(stats?.total_revenue ?? 0),
                    pending_payments: Number(stats?.pending_payments ?? 0),
                    overdue_invoices: Number(stats?.overdue_invoices ?? 0),
                    active_subscriptions: Number(stats?.active_subscriptions ?? 0)
                });
            },
            error: () => {
                const invoices = this.invoices();
                const totalRevenue = invoices.filter(i => i.status === 'paid').reduce((sum, i) => sum + (+(i.amount ?? 0)), 0);
                const pendingPayments = invoices.filter(i => i.status === 'pending').reduce((sum, i) => sum + (+(i.amount ?? 0)), 0);
                const overdueInvoices = invoices.filter(i => new Date(i.due_date || '') < new Date() && i.status === 'pending').length;

                this.stats.set({
                    total_revenue: totalRevenue,
                    pending_payments: pendingPayments,
                    overdue_invoices: overdueInvoices,
                    active_subscriptions: new Set(
                        invoices
                            .map(invoice => invoice.subscription?.id)
                            .filter((id): id is number => typeof id === 'number')
                    ).size
                });
            }
        });
    }

    onStatusFilter() {
        this.currentPage.set(1);
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

    getInvoiceDisplayStatusText(invoice: Invoice): string {
        const status = this.getInvoiceDisplayStatus(invoice);
        const labels: Record<string, string> = {
            paid: 'Pagada',
            pending: 'Pendiente',
            failed: 'Fallida',
            overdue: 'Vencida',
            canceled: 'Cancelada'
        };
        return labels[status] || status;
    }

    getStatusSeverity(status: string): 'success' | 'info' | 'warn' | 'danger' | 'secondary' | 'contrast' {
        switch (status) {
            case 'paid': return 'success';
            case 'pending': return 'warn';
            case 'failed': return 'danger';
            case 'overdue': return 'danger';
            case 'canceled': return 'secondary';
            default: return 'info';
        }
    }

    getInvoiceDisplayStatus(invoice: Invoice): string {
        if (!invoice.is_paid && invoice.status === 'pending' && invoice.due_date && new Date(invoice.due_date) < new Date()) {
            return 'overdue';
        }

        return invoice.status || 'pending';
    }

    getPlanDisplayName(invoice: Invoice | null | undefined): string {
        return getSubscriptionPlanLabel(
            invoice?.plan_name,
            invoice?.subscription?.plan?.name
        );
    }

    viewInvoice(invoice: Invoice) {
        if (!invoice.id) {
            return;
        }

        this.invoiceDetailLoading.set(true);
        this.selectedInvoice.set(null);
        this.showInvoiceDetailDialog = true;

        this.billingService.getInvoice(invoice.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (detail: Invoice) => {
                this.selectedInvoice.set(detail);
                this.invoiceDetailLoading.set(false);
            },
            error: () => {
                this.selectedInvoice.set(invoice);
                this.invoiceDetailLoading.set(false);
                this.messageService.add({
                    severity: 'warn',
                    summary: 'Detalle parcial',
                    detail: 'No se pudo cargar el detalle completo; mostrando la información disponible.'
                });
            }
        });
    }

    downloadInvoice(invoice: Invoice) {
        const html = this.buildInvoicePrintHtml(invoice);
        const printWindow = window.open('', '_blank');
        if (!printWindow) {
            this.messageService.add({
                severity: 'warn',
                summary: 'Popup bloqueado',
                detail: 'Permite popups para imprimir o guardar la factura como PDF'
            });
            return;
        }

        printWindow.document.write(html);
        printWindow.document.close();
        printWindow.focus();
        setTimeout(() => {
            try {
                printWindow.print();
            } catch {
                // no-op
            }
        }, 300);
    }

    markAsPaid(invoice: Invoice) {
        if (invoice.id) {
            const invoiceId = invoice.id;
            this.billingService.markInvoiceAsPaid(invoice.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
                next: () => {
                    const paidAt = new Date().toISOString();
                    const updatedInvoices = this.invoices().map(current =>
                        current.id === invoiceId
                            ? { ...current, status: 'paid', is_paid: true, paid_at: paidAt }
                            : current
                    );
                    this.invoices.set(updatedInvoices);
                    this.updateSelectedInvoice(invoiceId, { status: 'paid', is_paid: true, paid_at: paidAt });
                    this.loadStats();
                    this.messageService.add({
                        severity: 'success',
                        summary: 'Éxito',
                        detail: 'Factura marcada como pagada'
                    });
                },
                error: (error) => this.showErrorMessage('Error al marcar la factura como pagada', error)
            });
        }
    }

    generateInvoice() {
        if (!this.newInvoice.tenant || !this.newInvoice.due_date) {
            this.messageService.add({
                severity: 'error',
                summary: 'Error',
                detail: 'Selecciona un tenant y una fecha de vencimiento'
            });
            return;
        }

        this.billingService.generateInvoiceForTenant({
            tenant_id: this.newInvoice.tenant,
            due_date: this.newInvoice.due_date,
            description: this.newInvoice.description?.trim() || undefined
        }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: () => {
                this.messageService.add({
                    severity: 'success',
                    summary: 'Factura generada',
                    detail: 'La factura se creó correctamente usando la suscripción activa del tenant'
                });
                this.newInvoice = { tenant: null, description: '', due_date: null };
                this.showGenerateDialog = false;
                this.loadInvoices();
            },
            error: (error) => this.showErrorMessage('Error al generar la factura', error)
        });
    }

    trackByInvoice(index: number, invoice: Invoice): any {
        return invoice.id || index;
    }

    private handleLoadError(error: any): void {
        this.showErrorMessage('Error al cargar las facturas', error);
        this.invoices.set([]);
        this.loading.set(false);
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
        this.errorLogger.log('BillingManagement', context, error);
    }

    private updateSelectedInvoice(invoiceId: number, patch: Partial<Invoice>): void {
        const current = this.selectedInvoice();
        if (current?.id === invoiceId) {
            this.selectedInvoice.set({ ...current, ...patch });
        }
    }

    private buildInvoicePrintHtml(invoice: Invoice): string {
        const tenantName = invoice.tenant_name || invoice.user_name || invoice.user_email || 'N/A';
        const issued = invoice.issued_at ? new Date(invoice.issued_at).toLocaleDateString() : '-';
        const due = invoice.due_date ? new Date(invoice.due_date).toLocaleDateString() : '-';
        const paid = invoice.paid_at ? new Date(invoice.paid_at).toLocaleDateString() : '-';
        const amount = this.formatMoney(Number(invoice.amount || 0));

        return `<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Factura #${invoice.id || '-'}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; color: #111; }
    .header { border-bottom: 2px solid #e5e7eb; padding-bottom: 12px; margin-bottom: 20px; }
    .muted { color: #6b7280; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
    .box { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; }
    .amount { font-size: 28px; font-weight: 700; }
    @media print { @page { margin: 1cm; } }
  </style>
</head>
<body>
  <div class="header">
    <h2 style="margin:0;">Factura</h2>
    <p class="muted" style="margin:4px 0 0 0;">Factura #${invoice.id || '-'}</p>
  </div>
  <div class="grid">
    <div class="box"><strong>Cliente/Tenant</strong><div>${this.escapeHtml(tenantName)}</div></div>
    <div class="box"><strong>Plan</strong><div>${this.escapeHtml(this.getPlanDisplayName(invoice))}</div></div>
    <div class="box"><strong>Emisión</strong><div>${issued}</div></div>
    <div class="box"><strong>Vencimiento</strong><div>${due}</div></div>
    <div class="box"><strong>Estado</strong><div>${this.escapeHtml(invoice.status || 'pending')}</div></div>
    <div class="box"><strong>Pagada</strong><div>${paid}</div></div>
  </div>
  <div class="box">
    <div class="muted">Monto</div>
    <div class="amount">${amount}</div>
  </div>
</body>
</html>`;
    }

    private formatMoney(value: number): string {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: this.currencyCode()
        }).format(Number(value || 0));
    }

    private escapeHtml(text: string): string {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
