import { Component, OnInit, computed, signal } from '@angular/core';
import { ConfirmationService, MessageService } from 'primeng/api';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { ToastModule } from 'primeng/toast';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { TextareaModule } from 'primeng/textarea';
import { SelectModule } from 'primeng/select';
import { DialogModule } from 'primeng/dialog';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { TenantService } from '../../core/services/tenant/tenant.service';
import { SubscriptionService } from '../../core/services/subscription/subscription.service';
import { ActivityLogService } from '../../core/services/activity-log/activity-log.service';
import { LocaleService } from '../../core/services/locale/locale.service';
import { SettingsService } from '../../core/services/settings.service';
import { AdminErrorLogService } from '../../core/services/admin-error-log.service';
import { DatePipe } from '@angular/common';
import { Router } from '@angular/router';
import { getSubscriptionPlanLabel } from '../../core/utils/subscription-plan-label';
import { toggleTenantActive, toggleTenantSuspension } from './utils/tenant-admin-actions';

interface Tenant {
    id?: number;
    name?: string;
    subdomain?: string;
    contact_email?: string;
    contact_phone?: string;
    address?: string;
    country?: string;
    subscription_plan?: any;
    plan_type?: string;
    subscription_status?: string;
    trial_end_date?: string;
    billing_info?: any;
    settings?: any;
    max_users?: number;
    branches_count?: number;
    is_active?: boolean;
    created_at?: string;
    users_count?: number;
}

@Component({
    selector: 'app-tenants-management',
    standalone: true,
    imports: [
        FormsModule,
        ButtonModule,
        ToastModule,
        InputTextModule,
        InputNumberModule,
        TextareaModule,
        SelectModule,
        DialogModule,
        ConfirmDialogModule,
        DatePipe,
    ],
    template: `
        <div class="sm:flex sm:items-center sm:justify-between">
            <div class="sm:flex-auto">
                <div class="flex items-center gap-3">
                    <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-100 text-violet-600 dark:bg-violet-900/50 dark:text-violet-400">
                        <i class="pi pi-building text-lg"></i>
                    </div>
                    <div>
                        <h1 class="text-base font-semibold text-surface-950 dark:text-surface-0">Tenants</h1>
                        <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">Gestiona todas las barberías</p>
                    </div>
                </div>
            </div>
            <div class="mt-4 flex items-center gap-3 sm:mt-0 sm:ml-16 sm:flex-none">
                <button type="button" (click)="deleteSelectedTenants()" [disabled]="!selectedTenants.length" class="inline-flex items-center rounded-lg border border-surface-200 bg-surface-0 px-3 py-2 text-sm font-semibold text-surface-700 shadow-sm hover:bg-surface-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:hover:bg-surface-700">
                    <i class="pi pi-trash mr-1.5"></i>
                    Eliminar
                </button>
                <button type="button" (click)="openNew()" class="inline-flex items-center rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-600">
                    <i class="pi pi-plus mr-1.5"></i>
                    Nuevo Tenant
                </button>
            </div>
        </div>

        <div class="mt-4">
            <div class="relative">
                <i class="pi pi-search absolute left-3 top-1/2 -translate-y-1/2 text-surface-400 text-sm"></i>
                <input type="text" (input)="onGlobalFilter($event)" placeholder="Buscar tenants..." class="w-full rounded-lg border border-surface-200 bg-surface-0 py-2 pl-9 pr-3 text-sm text-surface-700 placeholder-surface-400 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:placeholder-surface-500" />
            </div>
        </div>

        <div class="mt-4 flow-root">
            <!-- Móvil: Tarjetas apiladas -->
            <div class="block md:hidden space-y-4">
                @for (tenant of sortedTenants(); track tenant.id) {
                    <div class="bg-white dark:bg-surface-900 rounded-xl border border-surface-200 dark:border-surface-800 shadow-sm overflow-hidden">
                        <div class="p-4">
                            <div class="flex items-start justify-between mb-3">
                                <div class="flex items-center gap-3 min-w-0">
                                    <input type="checkbox" [checked]="isSelected(tenant)" (change)="toggleSelection(tenant)" class="h-4 w-4 rounded border-surface-300 text-primary focus:ring-primary dark:border-surface-600 mt-0.5 shrink-0" />
                                    <div class="min-w-0">
                                        <h4 class="font-bold text-surface-900 dark:text-white truncate">{{ tenant.name }}</h4>
                                        <code class="text-xs rounded bg-surface-100 px-1.5 py-0.5 dark:bg-surface-800 text-surface-600 dark:text-surface-400">{{ tenant.subdomain }}</code>
                                    </div>
                                </div>
                                <div class="flex items-center gap-1.5 shrink-0">
                                    <button type="button" (click)="viewTenantDetails(tenant)" class="rounded-lg p-1.5 text-surface-500 hover:bg-surface-100 hover:text-surface-700 dark:text-surface-400 dark:hover:bg-surface-800 dark:hover:text-surface-200" title="Ver detalles">
                                        <i class="pi pi-eye"></i>
                                    </button>
                                    <button type="button" (click)="editTenant(tenant)" class="rounded-lg p-1.5 text-indigo-600 hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-900/30" title="Editar">
                                        <i class="pi pi-pencil"></i>
                                    </button>
                                </div>
                            </div>
                            <div class="space-y-2 text-sm">
                                <div class="flex justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Contacto</span>
                                    <span class="text-surface-700 dark:text-surface-200 truncate ml-2">{{ tenant.contact_email }}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Plan</span>
                                    <span class="text-surface-700 dark:text-surface-200">{{ getPlanLabel(tenant.plan_type, tenant.subscription_plan?.name) }}</span>
                                </div>
                                <div class="flex justify-between items-center">
                                    <span class="text-surface-500 dark:text-surface-400">Estado</span>
                                    @if (tenant.subscription_status === 'active') {
                                        <span class="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">Activo</span>
                                    } @else {
                                        <span class="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">{{ tenant.subscription_status || 'trial' }}</span>
                                    }
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Activo</span>
                                    @if (tenant.is_active) {
                                        <span class="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">Sí</span>
                                    } @else {
                                        <span class="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/40 dark:text-red-300">No</span>
                                    }
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Fin Trial</span>
                                    <span class="text-surface-500 dark:text-surface-400">{{ tenant.trial_end_date ? (tenant.trial_end_date | date:'dd/MM/yyyy') : '-' }}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Suc.</span>
                                    <span class="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">{{ tenant.branches_count || 1 }}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Límites</span>
                                    <span class="text-surface-500 dark:text-surface-400">{{ tenant.max_users || 0 }} users</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Creado</span>
                                    <span class="text-surface-500 dark:text-surface-400">{{ tenant.created_at | date:'dd/MM/yyyy' }}</span>
                                </div>
                            </div>
                            <div class="flex items-center justify-end gap-1 pt-3 mt-3 border-t border-surface-100 dark:border-surface-800">
                                <button type="button" (click)="deleteTenant(tenant)" class="rounded-lg p-1.5 text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/30" title="Eliminar">
                                    <i class="pi pi-trash"></i>
                                </button>
                                <button type="button" (click)="toggleTenantActive(tenant)" class="rounded-lg p-1.5" [class.text-red-600]="tenant.is_active" [class.hover:bg-red-50]="tenant.is_active" [class.dark:text-red-400]="tenant.is_active" [class.dark:hover:bg-red-900/30]="tenant.is_active" [class.text-emerald-600]="!tenant.is_active" [class.hover:bg-emerald-50]="!tenant.is_active" [class.dark:text-emerald-400]="!tenant.is_active" [class.dark:hover:bg-emerald-900/30]="!tenant.is_active" title="Activar/Desactivar">
                                    <i class="pi" [class.pi-ban]="tenant.is_active" [class.pi-check-circle]="!tenant.is_active"></i>
                                </button>
                                <button type="button" (click)="toggleTenantSuspension(tenant)" class="rounded-lg p-1.5" [class.text-emerald-600]="tenant.subscription_status === 'suspended'" [class.hover:bg-emerald-50]="tenant.subscription_status === 'suspended'" [class.dark:text-emerald-400]="tenant.subscription_status === 'suspended'" [class.dark:hover:bg-emerald-900/30]="tenant.subscription_status === 'suspended'" [class.text-amber-600]="tenant.subscription_status !== 'suspended'" [class.hover:bg-amber-50]="tenant.subscription_status !== 'suspended'" [class.dark:text-amber-400]="tenant.subscription_status !== 'suspended'" [class.dark:hover:bg-amber-900/30]="tenant.subscription_status !== 'suspended'" title="Suspender/Reanudar">
                                    <i class="pi" [class.pi-play]="tenant.subscription_status === 'suspended'" [class.pi-pause]="tenant.subscription_status !== 'suspended'"></i>
                                </button>
                                <button type="button" (click)="openExtendDialog(tenant)" class="rounded-lg p-1.5 text-blue-600 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/30" title="Extender suscripción">
                                    <i class="pi pi-calendar-plus"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                } @empty {
                    <div class="text-center py-8 text-surface-500 dark:text-surface-400">
                        @if (loading()) {
                            <i class="pi pi-spin pi-spinner mr-2"></i>
                            Cargando tenants...
                        } @else {
                            No hay tenants registrados.
                        }
                    </div>
                }
                @if (totalRecords() > pageSize()) {
                    <div class="flex items-center justify-between px-2 py-2">
                        <div class="flex items-center gap-2 text-sm text-surface-500 dark:text-surface-400">
                            <span>{{ firstRecord() + 1 }}–{{ lastRecord() }} de {{ totalRecords() }}</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <button type="button" (click)="prevPage()" [disabled]="currentPage() === 0" class="inline-flex items-center rounded-lg border border-surface-200 bg-surface-0 px-2 py-1 text-sm font-medium text-surface-700 shadow-sm hover:bg-surface-50 disabled:opacity-50 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:hover:bg-surface-700">
                                <i class="pi pi-chevron-left text-xs"></i>
                            </button>
                            <span class="text-sm text-surface-500 dark:text-surface-400">{{ currentPage() + 1 }}/{{ totalPages() }}</span>
                            <button type="button" (click)="nextPage()" [disabled]="currentPage() >= totalPages() - 1" class="inline-flex items-center rounded-lg border border-surface-200 bg-surface-0 px-2 py-1 text-sm font-medium text-surface-700 shadow-sm hover:bg-surface-50 disabled:opacity-50 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:hover:bg-surface-700">
                                <i class="pi pi-chevron-right text-xs"></i>
                            </button>
                        </div>
                    </div>
                }
            </div>

            <!-- Desktop: Tabla -->
            <div class="hidden md:block">
                <div class="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
                <div class="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
                    <table class="min-w-full divide-y divide-surface-200 dark:divide-surface-700">
                        <thead>
                            <tr>
                                <th scope="col" class="py-3.5 pr-3 pl-4 text-left text-sm font-semibold text-surface-950 dark:text-surface-0 sm:pl-0" style="width:3rem">
                                    <input type="checkbox" [checked]="allSelected()" (change)="toggleSelectAll($event)" class="h-4 w-4 rounded border-surface-300 text-primary focus:ring-primary dark:border-surface-600" />
                                </th>
                                <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">
                                    <button type="button" (click)="toggleSort('name')" class="group inline-flex items-center">
                                        Nombre
                                        <span class="ml-2 flex-none rounded-sm" [class.bg-indigo-100]="sortField() === 'name'" [class.text-indigo-600]="sortField() === 'name'" [class.dark:bg-indigo-900/50]="sortField() === 'name'" [class.dark:text-indigo-400]="sortField() === 'name'" [class.invisible]="sortField() !== 'name'" [class.text-surface-500]="sortField() !== 'name'" [class.group-hover:visible]="sortField() !== 'name'">
                                            <i class="pi" [class.pi-sort-up]="sortField() === 'name' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'name' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'name'"></i>
                                        </span>
                                    </button>
                                </th>
                                <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">
                                    <button type="button" (click)="toggleSort('subdomain')" class="group inline-flex items-center">
                                        Subdominio
                                        <span class="ml-2 flex-none rounded-sm" [class.bg-indigo-100]="sortField() === 'subdomain'" [class.text-indigo-600]="sortField() === 'subdomain'" [class.dark:bg-indigo-900/50]="sortField() === 'subdomain'" [class.dark:text-indigo-400]="sortField() === 'subdomain'" [class.invisible]="sortField() !== 'subdomain'" [class.text-surface-500]="sortField() !== 'subdomain'" [class.group-hover:visible]="sortField() !== 'subdomain'">
                                            <i class="pi" [class.pi-sort-up]="sortField() === 'subdomain' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'subdomain' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'subdomain'"></i>
                                        </span>
                                    </button>
                                </th>
                                <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">Contacto</th>
                                <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">Plan</th>
                                <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">Estado Sub.</th>
                                <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">Fin Trial</th>
                                <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">Suc.</th>
                                <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">Límites</th>
                                <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">
                                    <button type="button" (click)="toggleSort('is_active')" class="group inline-flex items-center">
                                        Activo
                                        <span class="ml-2 flex-none rounded-sm" [class.bg-indigo-100]="sortField() === 'is_active'" [class.text-indigo-600]="sortField() === 'is_active'" [class.dark:bg-indigo-900/50]="sortField() === 'is_active'" [class.dark:text-indigo-400]="sortField() === 'is_active'" [class.invisible]="sortField() !== 'is_active'" [class.text-surface-500]="sortField() !== 'is_active'" [class.group-hover:visible]="sortField() !== 'is_active'">
                                            <i class="pi" [class.pi-sort-up]="sortField() === 'is_active' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'is_active' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'is_active'"></i>
                                        </span>
                                    </button>
                                </th>
                                <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">
                                    <button type="button" (click)="toggleSort('created_at')" class="group inline-flex items-center">
                                        Creado
                                        <span class="ml-2 flex-none rounded-sm" [class.bg-indigo-100]="sortField() === 'created_at'" [class.text-indigo-600]="sortField() === 'created_at'" [class.dark:bg-indigo-900/50]="sortField() === 'created_at'" [class.dark:text-indigo-400]="sortField() === 'created_at'" [class.invisible]="sortField() !== 'created_at'" [class.text-surface-500]="sortField() !== 'created_at'" [class.group-hover:visible]="sortField() !== 'created_at'">
                                            <i class="pi" [class.pi-sort-up]="sortField() === 'created_at' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'created_at' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'created_at'"></i>
                                        </span>
                                    </button>
                                </th>
                                <th scope="col" class="py-3.5 pl-3 pr-0 text-right text-sm font-semibold text-surface-950 dark:text-surface-0">
                                    <span class="sr-only">Acciones</span>
                                </th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-surface-200 dark:divide-surface-700">
                            @for (tenant of sortedTenants(); track tenant.id) {
                                <tr class="hover:bg-surface-50 dark:hover:bg-surface-800/50">
                                    <td class="py-4 pr-3 pl-4 text-sm whitespace-nowrap sm:pl-0" style="width:3rem">
                                        <input type="checkbox" [checked]="isSelected(tenant)" (change)="toggleSelection(tenant)" class="h-4 w-4 rounded border-surface-300 text-primary focus:ring-primary dark:border-surface-600" />
                                    </td>
                                    <td class="px-3 py-4 text-sm font-medium whitespace-nowrap text-surface-950 dark:text-surface-0">{{ tenant.name }}</td>
                                    <td class="px-3 py-4 text-sm whitespace-nowrap text-surface-700 dark:text-surface-200">
                                        <code class="rounded bg-surface-100 px-1.5 py-0.5 text-xs dark:bg-surface-800">{{ tenant.subdomain }}</code>
                                    </td>
                                    <td class="px-3 py-4 text-sm whitespace-nowrap text-surface-500 dark:text-surface-400">{{ tenant.contact_email }}</td>
                                    <td class="px-3 py-4 text-sm whitespace-nowrap text-surface-700 dark:text-surface-200">{{ getPlanLabel(tenant.plan_type, tenant.subscription_plan?.name) }}</td>
                                    <td class="px-3 py-4 text-sm whitespace-nowrap">
                                        @if (tenant.subscription_status === 'active') {
                                            <span class="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">Activo</span>
                                        } @else {
                                            <span class="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">{{ tenant.subscription_status || 'trial' }}</span>
                                        }
                                    </td>
                                    <td class="px-3 py-4 text-sm whitespace-nowrap text-surface-500 dark:text-surface-400">{{ tenant.trial_end_date ? (tenant.trial_end_date | date:'dd/MM/yyyy') : '-' }}</td>
                                    <td class="px-3 py-4 text-sm whitespace-nowrap">
                                        <span class="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">{{ tenant.branches_count || 1 }}</span>
                                    </td>
                                    <td class="px-3 py-4 text-sm whitespace-nowrap text-surface-500 dark:text-surface-400">{{ tenant.max_users || 0 }} users</td>
                                    <td class="px-3 py-4 text-sm whitespace-nowrap">
                                        @if (tenant.is_active) {
                                            <span class="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">Sí</span>
                                        } @else {
                                            <span class="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/40 dark:text-red-300">No</span>
                                        }
                                    </td>
                                    <td class="px-3 py-4 text-sm whitespace-nowrap text-surface-500 dark:text-surface-400">{{ tenant.created_at | date:'dd/MM/yyyy' }}</td>
                                    <td class="py-4 pl-3 pr-0 text-right text-sm whitespace-nowrap">
                                        <div class="flex items-center justify-end gap-1">
                                            <button type="button" (click)="viewTenantDetails(tenant)" class="rounded-lg p-1.5 text-surface-500 hover:bg-surface-100 hover:text-surface-700 dark:text-surface-400 dark:hover:bg-surface-800 dark:hover:text-surface-200" title="Ver detalles">
                                                <i class="pi pi-eye"></i>
                                            </button>
                                            <button type="button" (click)="editTenant(tenant)" class="rounded-lg p-1.5 text-indigo-600 hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-900/30" title="Editar">
                                                <i class="pi pi-pencil"></i>
                                            </button>
                                            <button type="button" (click)="deleteTenant(tenant)" class="rounded-lg p-1.5 text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/30" title="Eliminar">
                                                <i class="pi pi-trash"></i>
                                            </button>
                                            <button type="button" (click)="toggleTenantActive(tenant)" class="rounded-lg p-1.5" [class.text-red-600]="tenant.is_active" [class.hover:bg-red-50]="tenant.is_active" [class.dark:text-red-400]="tenant.is_active" [class.dark:hover:bg-red-900/30]="tenant.is_active" [class.text-emerald-600]="!tenant.is_active" [class.hover:bg-emerald-50]="!tenant.is_active" [class.dark:text-emerald-400]="!tenant.is_active" [class.dark:hover:bg-emerald-900/30]="!tenant.is_active" title="Activar/Desactivar">
                                                <i class="pi" [class.pi-ban]="tenant.is_active" [class.pi-check-circle]="!tenant.is_active"></i>
                                            </button>
                                            <button type="button" (click)="toggleTenantSuspension(tenant)" class="rounded-lg p-1.5" [class.text-emerald-600]="tenant.subscription_status === 'suspended'" [class.hover:bg-emerald-50]="tenant.subscription_status === 'suspended'" [class.dark:text-emerald-400]="tenant.subscription_status === 'suspended'" [class.dark:hover:bg-emerald-900/30]="tenant.subscription_status === 'suspended'" [class.text-amber-600]="tenant.subscription_status !== 'suspended'" [class.hover:bg-amber-50]="tenant.subscription_status !== 'suspended'" [class.dark:text-amber-400]="tenant.subscription_status !== 'suspended'" [class.dark:hover:bg-amber-900/30]="tenant.subscription_status !== 'suspended'" title="Suspender/Reanudar">
                                                <i class="pi" [class.pi-play]="tenant.subscription_status === 'suspended'" [class.pi-pause]="tenant.subscription_status !== 'suspended'"></i>
                                            </button>
                                            <button type="button" (click)="openExtendDialog(tenant)" class="rounded-lg p-1.5 text-blue-600 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/30" title="Extender suscripción">
                                                <i class="pi pi-calendar-plus"></i>
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            } @empty {
                                <tr>
                                    <td colspan="12" class="px-3 py-12 text-center text-sm text-surface-500 dark:text-surface-400">
                                        @if (loading()) {
                                            <i class="pi pi-spin pi-spinner mr-2"></i>
                                            Cargando tenants...
                                        } @else {
                                            No hay tenants registrados.
                                        }
                                    </td>
                                </tr>
                            }
                        </tbody>
                    </table>
                    @if (totalRecords() > pageSize()) {
                        <div class="flex items-center justify-between border-t border-surface-200 px-4 py-3 dark:border-surface-700">
                            <div class="flex items-center gap-2 text-sm text-surface-500 dark:text-surface-400">
                                <span>Mostrando {{ firstRecord() + 1 }}–{{ lastRecord() }} de {{ totalRecords() }}</span>
                                <select [value]="pageSize()" (change)="changePageSize($event)" class="rounded-md border border-surface-200 bg-surface-0 px-2 py-1 text-sm dark:border-surface-700 dark:bg-surface-800">
                                    <option value="10">10</option>
                                    <option value="20">20</option>
                                    <option value="30">30</option>
                                </select>
                            </div>
                            <div class="flex items-center gap-2">
                                <button type="button" (click)="prevPage()" [disabled]="currentPage() === 0" class="inline-flex items-center rounded-lg border border-surface-200 bg-surface-0 px-3 py-1.5 text-sm font-medium text-surface-700 shadow-sm hover:bg-surface-50 disabled:opacity-50 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:hover:bg-surface-700">
                                    <i class="pi pi-chevron-left mr-1 text-xs"></i>
                                    Anterior
                                </button>
                                <span class="text-sm text-surface-500 dark:text-surface-400">{{ currentPage() + 1 }} de {{ totalPages() }}</span>
                                <button type="button" (click)="nextPage()" [disabled]="currentPage() >= totalPages() - 1" class="inline-flex items-center rounded-lg border border-surface-200 bg-surface-0 px-3 py-1.5 text-sm font-medium text-surface-700 shadow-sm hover:bg-surface-50 disabled:opacity-50 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:hover:bg-surface-700">
                                    Siguiente
                                    <i class="pi pi-chevron-right ml-1 text-xs"></i>
                                </button>
                            </div>
                        </div>
                    }
                </div>
            </div>
            </div>
        </div>

        <p-dialog [(visible)]="tenantDialog" [style]="{ width: '450px' }" [breakpoints]="{'960px':'75vw','640px':'100vw'}" [header]="dialogHeader" [modal]="true">
            <ng-template #content>
                <div class="flex flex-col gap-6">
                    <div>
                        <label for="name" class="block font-bold mb-3">Nombre</label>
                        <input type="text" pInputText id="name" [(ngModel)]="tenant.name" required autofocus fluid />
                        @if (submitted && !tenant.name) { <small class="text-red-500">El nombre es obligatorio.</small> }
                    </div>

                    <div>
                        <label for="subdomain" class="block font-bold mb-3">Subdominio</label>
                        <input type="text" pInputText id="subdomain" [(ngModel)]="tenant.subdomain" required fluid />
                        @if (submitted && !tenant.subdomain) { <small class="text-red-500">El subdominio es obligatorio.</small> }
                    </div>

                    <div>
                        <label for="contact_email" class="block font-bold mb-3">Correo de Contacto</label>
                        <input type="email" pInputText id="contact_email" [(ngModel)]="tenant.contact_email" required fluid />
                        @if (submitted && !tenant.contact_email) { <small class="text-red-500">El correo de contacto es obligatorio.</small> }
                    </div>

                    <div>
                        <label for="contact_phone" class="block font-bold mb-3">Teléfono de Contacto</label>
                        <input type="text" pInputText id="contact_phone" [(ngModel)]="tenant.contact_phone" fluid />
                    </div>

                    <div>
                        <label for="subscription_plan" class="block font-bold mb-3">Plan de Suscripción</label>
                        <p-select [(ngModel)]="tenant.subscription_plan" inputId="subscription_plan" [options]="subscriptionPlans()" appendTo="body" optionLabel="name" optionValue="id" placeholder="Seleccionar plan" fluid />
                    </div>

                    <div class="flex items-center gap-2">
                        <input type="checkbox" id="is_active" [(ngModel)]="tenant.is_active" />
                        <label for="is_active">Activo</label>
                    </div>
                </div>
            </ng-template>

            <ng-template #footer>
                <p-button label="Cancelar" icon="pi pi-times" text (click)="hideDialog()" />
                <p-button label="Guardar" icon="pi pi-check" (click)="saveTenant()" [loading]="saving()" />
            </ng-template>
        </p-dialog>

        <p-dialog [(visible)]="showExtendDialog" [style]="{ width: '420px' }" [breakpoints]="{'960px':'75vw','640px':'100vw'}" header="Extender suscripción" [modal]="true">
            <ng-template #content>
                <div class="flex flex-col gap-4 py-2">
                    <p class="text-sm text-surface-600 dark:text-surface-400">
                        Extender suscripción de <strong>{{ extendTenant()?.name }}</strong>
                    </p>
                    <div>
                        <label class="mb-2 block text-sm font-medium text-surface-700 dark:text-surface-300">Días</label>
                        <p-inputNumber [(ngModel)]="extendDays" [min]="1" [max]="365" class="w-full" />
                    </div>
                    <div>
                        <label class="mb-2 block text-sm font-medium text-surface-700 dark:text-surface-300">Motivo (opcional)</label>
                        <textarea pInputText [(ngModel)]="extendReason" class="w-full h-20 resize-none" placeholder="Ej: Pago offline, cortesía, etc."></textarea>
                    </div>
                </div>
            </ng-template>
            <ng-template #footer>
                <p-button label="Cancelar" icon="pi pi-times" text (click)="showExtendDialog = false" />
                <p-button label="Extender" icon="pi pi-calendar-plus" (click)="confirmExtend()" [loading]="extending()" />
            </ng-template>
        </p-dialog>
        <p-confirmdialog [style]="{ width: '450px' }" />
        <p-toast />
    `,
    providers: [MessageService, ConfirmationService]
})
export class TenantsManagement implements OnInit {
    tenantDialog: boolean = false;
    tenants = signal<Tenant[]>([]);
    subscriptionPlans = signal<any[]>([]);
    tenant!: Tenant;
    selectedTenantsSet = signal<Set<number>>(new Set());
    submitted: boolean = false;
    loading = signal(false);
    saving = signal(false);

    getPlanLabel(...args: Parameters<typeof getSubscriptionPlanLabel>): string {
        return getSubscriptionPlanLabel(...args);
    }

    showExtendDialog = false;
    extendTenant = signal<Tenant | null>(null);
    extendDays = 30;
    extendReason = '';
    extending = signal(false);
    maxTenants = signal(100);
    sortField = signal<string>('created_at');
    sortOrder = signal<'asc' | 'desc'>('desc');
    currentPage = signal(0);
    pageSize = signal(10);
    globalFilter = signal('');

    sortedTenants = computed(() => {
        const all = this.tenants();
        const field = this.sortField();
        const order = this.sortOrder();
        const filter = this.globalFilter().toLowerCase();
        let filtered = all;
        if (filter) {
            filtered = all.filter(t =>
                (t.name?.toLowerCase() || '').includes(filter) ||
                (t.subdomain?.toLowerCase() || '').includes(filter) ||
                (t.contact_email?.toLowerCase() || '').includes(filter)
            );
        }
        const sorted = [...filtered].sort((a, b) => {
            const aVal = String(a[field as keyof Tenant] ?? '');
            const bVal = String(b[field as keyof Tenant] ?? '');
            return order === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
        });
        const start = this.currentPage() * this.pageSize();
        return sorted.slice(start, start + this.pageSize());
    });

    totalRecords = computed(() => {
        const all = this.tenants();
        const filter = this.globalFilter().toLowerCase();
        if (!filter) return all.length;
        return all.filter(t =>
            (t.name?.toLowerCase() || '').includes(filter) ||
            (t.subdomain?.toLowerCase() || '').includes(filter) ||
            (t.contact_email?.toLowerCase() || '').includes(filter)
        ).length;
    });

    totalPages = computed(() => Math.max(1, Math.ceil(this.totalRecords() / this.pageSize())));
    firstRecord = computed(() => this.currentPage() * this.pageSize());
    lastRecord = computed(() => Math.min(this.firstRecord() + this.pageSize(), this.totalRecords()));

    allSelected = computed(() => {
        const displayed = this.sortedTenants();
        const set = this.selectedTenantsSet();
        return displayed.length > 0 && displayed.every(t => t.id && set.has(t.id));
    });

    get selectedTenants(): Tenant[] {
        const set = this.selectedTenantsSet();
        return this.tenants().filter(t => t.id && set.has(t.id));
    }

    constructor(
        private tenantService: TenantService,
        private subscriptionService: SubscriptionService,
        private activityLogService: ActivityLogService,
        private settingsService: SettingsService,
        private router: Router,
        public localeService: LocaleService,
        private messageService: MessageService,
        private confirmationService: ConfirmationService,
        private errorLogger: AdminErrorLogService
    ) {}

    ngOnInit() {
        this.loadTenants();
        this.loadSubscriptionPlans();
        this.loadSystemSettings();
    }

    loadTenants() {
        this.loading.set(true);
        this.tenantService.getTenants().subscribe({
            next: (data: any) => {
                const tenants = Array.isArray(data) ? data : (data && data.results ? data.results : []);
                this.tenants.set(tenants);
                this.loading.set(false);
            },
            error: (error) => this.handleLoadError(error)
        });
    }

    loadSubscriptionPlans() {
        this.subscriptionService.getPlans().subscribe({
            next: (data: any) => {
                const plans = Array.isArray(data) ? data : (data.results || []);
                this.subscriptionPlans.set(plans);
            },
            error: (error) => this.handlePlansLoadError(error)
        });
    }

    loadSystemSettings() {
        this.settingsService.getSettings().subscribe({
            next: (settings: any) => {
                const max = Number(settings?.max_tenants);
                if (!Number.isNaN(max) && max > 0) {
                    this.maxTenants.set(max);
                }
            },
            error: () => {
                this.maxTenants.set(100);
            }
        });
    }

    onGlobalFilter(event: Event) {
        this.currentPage.set(0);
        this.globalFilter.set((event.target as HTMLInputElement).value);
    }

    toggleSort(field: string) {
        if (this.sortField() === field) {
            this.sortOrder.set(this.sortOrder() === 'asc' ? 'desc' : 'asc');
        } else {
            this.sortField.set(field);
            this.sortOrder.set('asc');
        }
        this.currentPage.set(0);
    }

    isSelected(tenant: Tenant): boolean {
        return tenant.id ? this.selectedTenantsSet().has(tenant.id) : false;
    }

    toggleSelection(tenant: Tenant) {
        if (!tenant.id) return;
        const set = new Set(this.selectedTenantsSet());
        if (set.has(tenant.id)) set.delete(tenant.id);
        else set.add(tenant.id);
        this.selectedTenantsSet.set(set);
    }

    toggleSelectAll(event: Event) {
        const checked = (event.target as HTMLInputElement).checked;
        const set = new Set(this.selectedTenantsSet());
        if (checked) {
            this.sortedTenants().forEach(t => { if (t.id) set.add(t.id); });
        } else {
            this.sortedTenants().forEach(t => { if (t.id) set.delete(t.id); });
        }
        this.selectedTenantsSet.set(set);
    }

    changePageSize(event: Event) {
        this.pageSize.set(Number((event.target as HTMLSelectElement).value));
        this.currentPage.set(0);
    }

    prevPage() {
        if (this.currentPage() > 0) this.currentPage.update(p => p - 1);
    }

    nextPage() {
        if (this.currentPage() < this.totalPages() - 1) this.currentPage.update(p => p + 1);
    }

    openNew() {
        this.tenant = { is_active: true };
        this.submitted = false;
        this.tenantDialog = true;
    }

    editTenant(tenant: Tenant) {
        this.tenant = { ...tenant };
        this.tenantDialog = true;
    }

    deleteSelectedTenants() {
        const selected = this.selectedTenants;
        if (!selected.length) return;

        this.confirmationService.confirm({
            message: '¿Estás seguro de eliminar los tenants seleccionados?',
            header: 'Confirmar',
            icon: 'pi pi-exclamation-triangle',
            accept: () => {
                const tenantIds = selected.map(t => t.id!).filter(id => id);
                this.tenantService.bulkDelete(tenantIds).subscribe({
                    next: () => {
                        this.loadTenants();
                        this.selectedTenantsSet.set(new Set());
                        this.messageService.add({
                            severity: 'success',
                            summary: 'Éxito',
                            detail: 'Tenants eliminados',
                            life: 3000
                        });
                    },
                    error: (error) => this.showErrorMessage('Error al eliminar tenants', error)
                });
            }
        });
    }

    deleteTenant(tenant: Tenant) {
        this.confirmationService.confirm({
            message: `¿Estás seguro de eliminar ${tenant.name || 'este tenant'}?`,
            header: 'Confirmar',
            icon: 'pi pi-exclamation-triangle',
            accept: () => {
                if (tenant.id) {
                    this.tenantService.deleteTenant(tenant.id).subscribe({
                        next: () => {
                            this.loadTenants();
                            this.messageService.add({
                                severity: 'success',
                                summary: 'Éxito',
                                detail: 'Tenant eliminado',
                                life: 3000
                            });
                        },
                        error: (error) => this.showErrorMessage('Error al eliminar tenant', error)
                    });
                }
            }
        });
    }

    hideDialog() {
        this.tenantDialog = false;
        this.submitted = false;
    }

    get dialogHeader(): string {
        return this.tenant?.id ? 'Editar Tenant' : 'Nuevo Tenant';
    }

    saveTenant() {
        this.submitted = true;

        if (this.tenant.name?.trim() && this.tenant.subdomain?.trim() && this.tenant.contact_email?.trim()) {
            if (!this.tenant.subscription_plan) {
                this.messageService.add({
                    severity: 'error',
                    summary: 'Error',
                    detail: 'Please select a subscription plan'
                });
                return;
            }

            this.saving.set(true);

            if (this.tenant.id) {
                this.tenantService.updateTenant(this.tenant.id, this.tenant).subscribe({
                    next: (updatedTenant) => {
                        const tenants = this.tenants();
                        const index = tenants.findIndex(t => t.id === this.tenant.id);
                        if (index !== -1) {
                            tenants[index] = updatedTenant;
                            this.tenants.set([...tenants]);
                        }
                        this.messageService.add({
                            severity: 'success',
                            summary: 'Éxito',
                            detail: 'Tenant actualizado',
                            life: 3000
                        });
                        this.tenantDialog = false;
                        this.saving.set(false);
                    },
                    error: (error) => {
                        this.showErrorMessage('Error al actualizar tenant', error);
                        this.saving.set(false);
                    }
                });
            } else {
                if (!this.validateTenantLimits(this.tenant.is_active !== false)) {
                    return;
                }

                const tenantData = {
                    name: this.tenant.name,
                    subdomain: this.tenant.subdomain,
                    contact_email: this.tenant.contact_email,
                    contact_phone: this.tenant.contact_phone || '',
                    subscription_plan: this.tenant.subscription_plan,
                    is_active: this.tenant.is_active
                };

                this.tenantService.createTenant(tenantData).subscribe({
                    next: (newTenant) => {
                        this.tenants.set([...this.tenants(), newTenant]);
                        this.messageService.add({
                            severity: 'success',
                            summary: 'Éxito',
                            detail: 'Tenant creado',
                            life: 3000
                        });
                        this.tenantDialog = false;
                        this.saving.set(false);
                    },
                    error: (error) => {
                        this.showErrorMessage('Error al crear tenant', error);
                        this.saving.set(false);
                    }
                });
            }
        }
    }

    validateTenantLimits(willBeActive: boolean) {
        if (!willBeActive) return true;

        const activeTenants = this.tenants().filter(t => t.is_active).length;
        const maxTenants = this.maxTenants();

        if (activeTenants >= maxTenants) {
            this.messageService.add({
                severity: 'error',
                summary: 'Limit Reached',
                detail: `Maximum number of tenants (${maxTenants}) reached`
            });
            return false;
        }
        return true;
    }

    trackByTenant(index: number, tenant: Tenant): any {
        return tenant.id || index;
    }

    viewTenantDetails(tenant: Tenant) {
        if (!tenant.id) return;
        this.router.navigate(['/admin/tenants', tenant.id]);
    }

    toggleTenantActive(tenant: Tenant) {
        const isActive = tenant.is_active;
        this.confirmationService.confirm({
            message: isActive
                ? `¿Desactivar el tenant "${tenant.name}"?`
                : `¿Activar el tenant "${tenant.name}"?`,
            header: 'Confirmar',
            icon: 'pi pi-exclamation-triangle',
            acceptLabel: isActive ? 'Desactivar' : 'Activar',
            rejectLabel: 'Cancelar',
            accept: () => {
                toggleTenantActive(
                    this.tenantService,
                    tenant,
                    () => {
                        this.showSuccessMessage(isActive ? 'Tenant desactivado' : 'Tenant activado');
                        this.loadTenants();
                    },
                    (message, error) => this.showErrorMessage(message, error)
                );
            }
        });
    }

    toggleTenantSuspension(tenant: Tenant) {
        const isSuspended = tenant.subscription_status === 'suspended';
        if (isSuspended) {
            this.confirmationService.confirm({
                message: `¿Reanudar la suscripción del tenant "${tenant.name}"?`,
                header: 'Confirmar',
                icon: 'pi pi-exclamation-triangle',
                acceptLabel: 'Reanudar',
                rejectLabel: 'Cancelar',
                accept: () => {
                    toggleTenantSuspension(
                        this.tenantService,
                        tenant,
                        () => {
                            this.showSuccessMessage('Tenant reanudado');
                            this.loadTenants();
                        },
                        (_message, error) =>
                            this.showErrorMessage('No se pudo reanudar tenant', error),
                        'Razón de suspensión del tenant:'
                    );
                }
            });
            return;
        }

        this.confirmationService.confirm({
            message: `¿Suspender la suscripción del tenant "${tenant.name}"?`,
            header: 'Confirmar',
            icon: 'pi pi-exclamation-triangle',
            acceptLabel: 'Suspender',
            rejectLabel: 'Cancelar',
            accept: () => {
                toggleTenantSuspension(
                    this.tenantService,
                    tenant,
                    () => {
                        this.showSuccessMessage('Tenant suspendido');
                        this.loadTenants();
                    },
                    (_message, error) =>
                        this.showErrorMessage('No se pudo suspender tenant', error),
                    'Razón de suspensión del tenant:'
                );
            }
        });
    }

    openExtendDialog(tenant: Tenant) {
        this.extendTenant.set(tenant);
        this.extendDays = 30;
        this.extendReason = '';
        this.showExtendDialog = true;
    }

    confirmExtend() {
        const tenant = this.extendTenant();
        if (!tenant?.id || !this.extendDays || this.extendDays < 1) return;
        this.extending.set(true);
        this.tenantService.extendSubscription(tenant.id, this.extendDays, this.extendReason).subscribe({
            next: () => {
                this.extending.set(false);
                this.showExtendDialog = false;
                this.showSuccessMessage(`Suscripción extendida ${this.extendDays} días`);
                this.loadTenants();
            },
            error: (error) => {
                this.extending.set(false);
                this.showErrorMessage('No se pudo extender la suscripción', error);
            }
        });
    }

    private handleLoadError(error: any): void {
        this.logError('Failed to load tenants', error);
        this.tenants.set([]);
        this.loading.set(false);
        this.messageService.add({
            severity: 'error',
            summary: 'Error',
            detail: 'No se pudieron cargar los tenants. Por favor, intenta de nuevo.',
            life: 5000
        });
    }

    private handlePlansLoadError(error: any): void {
        this.logError('Failed to load subscription plans', error);
        this.subscriptionPlans.set([]);
        this.messageService.add({
            severity: 'warn',
            summary: 'Advertencia',
            detail: 'No se pudieron cargar los planes de suscripción',
            life: 3000
        });
    }

    private showErrorMessage(message: string, error?: any): void {
        this.logError(message, error);
        this.messageService.add({
            severity: 'error',
            summary: 'Error',
            detail: this.sanitizeErrorMessage(error, message)
        });
    }

    private showSuccessMessage(detail: string): void {
        this.messageService.add({
            severity: 'success',
            summary: 'Exitoso',
            detail,
            life: 3000
        });
    }

    private sanitizeErrorMessage(error: any, fallback: string): string {
        const errorMessage = error?.error?.message || error?.message;
        return typeof errorMessage === 'string' ? errorMessage.substring(0, 200) : fallback;
    }

    private logError(context: string, error: any): void {
        this.errorLogger.log('TenantsManagement', context, error);
    }
}
