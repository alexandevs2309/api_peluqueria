import { Component, DestroyRef, OnInit, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ConfirmationService, MessageService } from 'primeng/api';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { ToastModule } from 'primeng/toast';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { DialogModule } from 'primeng/dialog';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { AuthService } from '../../core/services/auth/auth.service';
import { TenantService } from '../../core/services/tenant/tenant.service';
import { RoleService } from '../../core/services/role/role.service';
import { PlanAccessService } from '../../core/services/plan-access.service';
import { UIHelpers } from '../../shared/utils/ui-helpers';
import { DatePipe } from '@angular/common';
import { roleKey } from '../../core/utils/role-normalizer';
import { AdminErrorLogService } from '../../core/services/admin-error-log.service';

interface User {
    id?: number;
    email?: string;
    full_name?: string;
    role?: string;
    tenant?: number;
    tenant_name?: string;
    is_active?: boolean;
    date_joined?: string;
    last_login?: string;
    password?: string;
    phone?: string;
}

import { safeGetItem } from '../../core/utils/storage';

@Component({
    selector: 'app-users-management',
    standalone: true,
    imports: [CommonModule, FormsModule, ButtonModule, ToastModule, InputTextModule, SelectModule, DialogModule, ConfirmDialogModule, DatePipe],
    template: `
        <div class="sm:flex sm:items-center sm:justify-between">
            <div class="sm:flex-auto">
                <div class="flex items-center gap-3">
                    <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-100 text-violet-600 dark:bg-violet-900/50 dark:text-violet-400">
                        <i class="pi pi-users text-lg"></i>
                    </div>
                    <div>
                        <h1 class="text-base font-semibold text-surface-950 dark:text-surface-0">Usuarios</h1>
                        <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">
                            {{ isSuperAdminView() ? 'Selecciona un tenant para gestionar sus usuarios' : 'Gestiona los usuarios de tu tenant' }}
                        </p>
                    </div>
                </div>
            </div>
            <div class="mt-4 flex items-center gap-3 sm:mt-0 sm:ml-16 sm:flex-none">
                @if (isSuperAdminView()) {
                    <p-select
                        [(ngModel)]="selectedTenantFilter"
                        [options]="tenantOptions()"
                        optionLabel="name"
                        optionValue="id"
                        [filter]="true"
                        filterBy="name,subdomain,id"
                        [showClear]="true"
                        placeholder="Selecciona Tenant"
                        emptyFilterMessage="No se encontraron tenants"
                        (onChange)="filterByTenant()"
                        styleClass="w-48"
                    />
                }
                <button type="button" (click)="deleteSelectedUsers()" [disabled]="!selectedUsers.length" class="inline-flex items-center rounded-lg border border-surface-200 bg-surface-0 px-3 py-2 text-sm font-semibold text-surface-700 shadow-sm hover:bg-surface-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:hover:bg-surface-700">
                    <i class="pi pi-trash mr-1.5"></i>
                    Eliminar
                </button>
                <button type="button" (click)="openNew()" [disabled]="isSuperAdminView() && !selectedTenantFilter" class="inline-flex items-center rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-600 disabled:opacity-50">
                    <i class="pi pi-plus mr-1.5"></i>
                    Nuevo Usuario
                </button>
            </div>
        </div>

        @if (isSuperAdminView() && !selectedTenantFilter) {
            <div class="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
                <i class="pi pi-info-circle mr-1.5"></i>
                Selecciona un tenant para ver y gestionar usuarios.
            </div>
        }

        <div class="mt-4">
            <div class="relative">
                <i class="pi pi-search absolute left-3 top-1/2 -translate-y-1/2 text-surface-400 text-sm"></i>
                <input type="text" (input)="onGlobalFilter($event)" placeholder="Buscar usuarios..." class="w-full rounded-lg border border-surface-200 bg-surface-0 py-2 pl-9 pr-3 text-sm text-surface-700 placeholder-surface-400 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:placeholder-surface-500" />
            </div>
        </div>

        <div class="mt-4 flow-root">
            <!-- Móvil: Tarjetas apiladas -->
            <div class="block md:hidden space-y-4">
                @for (user of sortedUsers(); track user.id) {
                    <div class="bg-white dark:bg-surface-900 rounded-xl border border-surface-200 dark:border-surface-800 shadow-sm overflow-hidden">
                        <div class="p-4">
                            <div class="flex items-start justify-between mb-3">
                                <div class="flex items-center gap-3 min-w-0">
                                    <input type="checkbox" [checked]="isSelected(user)" (change)="toggleSelection(user)" class="h-4 w-4 rounded border-surface-300 text-primary focus:ring-primary dark:border-surface-600 mt-0.5 shrink-0" />
                                    <div class="min-w-0">
                                        <h4 class="font-bold text-surface-900 dark:text-white truncate">{{ user.full_name }}</h4>
                                        <p class="text-xs text-surface-500 dark:text-surface-400 truncate">{{ user.email }}</p>
                                    </div>
                                </div>
                                <button type="button" (click)="editUser(user)" class="rounded-lg p-1.5 text-indigo-600 hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-900/30 shrink-0" title="Editar">
                                    <i class="pi pi-pencil"></i>
                                </button>
                            </div>
                            <div class="space-y-2 text-sm">
                                <div class="flex items-center justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Rol</span>
                                    <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium" [class]="getRoleBadgeClass(user.role)">
                                        {{ user.role }}
                                    </span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Tenant</span>
                                    <span class="text-surface-700 dark:text-surface-200">{{ user.tenant_name || 'N/A' }}</span>
                                </div>
                                <div class="flex items-center justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Estado</span>
                                    <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium" [class]="getStatusBadgeClass(user.is_active)">
                                        {{ user.is_active ? 'Activo' : 'Inactivo' }}
                                    </span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Registro</span>
                                    <span class="text-surface-500 dark:text-surface-400">{{ user.date_joined | date: 'dd/MM/yyyy' }}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-surface-500 dark:text-surface-400">Último Acceso</span>
                                    <span class="text-surface-500 dark:text-surface-400">{{ user.last_login | date: 'dd/MM/yyyy' }}</span>
                                </div>
                            </div>
                            <div class="flex items-center justify-end pt-3 mt-3 border-t border-surface-100 dark:border-surface-800">
                                <button type="button" (click)="deleteUser(user)" class="inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/30">
                                    <i class="pi pi-trash"></i>
                                    Eliminar
                                </button>
                            </div>
                        </div>
                    </div>
                } @empty {
                    <div class="text-center py-8 text-surface-500 dark:text-surface-400">
                        @if (loading()) {
                            <i class="pi pi-spin pi-spinner mr-2"></i>
                            Cargando usuarios...
                        } @else {
                            No hay usuarios registrados.
                        }
                    </div>
                }
                @if (totalRecords() > pageSize()) {
                    <div class="flex items-center justify-between px-2 py-2">
                        <div class="flex items-center gap-2 text-sm text-surface-500 dark:text-surface-400">
                            <span>{{ firstRecord() + 1 }}–{{ lastRecord() }} de {{ totalRecords() }}</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <button type="button" (click)="prevPage()" [disabled]="currentPage() === 0" aria-label="Página anterior" class="inline-flex items-center rounded-lg border border-surface-200 bg-surface-0 px-2 py-1 text-sm font-medium text-surface-700 shadow-sm hover:bg-surface-50 disabled:opacity-50 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:hover:bg-surface-700">
                                <i class="pi pi-chevron-left text-xs"></i>
                            </button>
                            <span class="text-sm text-surface-500 dark:text-surface-400">{{ currentPage() + 1 }}/{{ totalPages() }}</span>
                            <button type="button" (click)="nextPage()" [disabled]="currentPage() >= totalPages() - 1" aria-label="Siguiente página" class="inline-flex items-center rounded-lg border border-surface-200 bg-surface-0 px-2 py-1 text-sm font-medium text-surface-700 shadow-sm hover:bg-surface-50 disabled:opacity-50 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:hover:bg-surface-700">
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
                                    <input type="checkbox" [checked]="allSelected()" (change)="toggleSelectAll($event)" aria-label="Seleccionar todos los usuarios de esta página" class="h-4 w-4 rounded border-surface-300 text-primary focus:ring-primary dark:border-surface-600" />
                                </th>
                                <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">
                                    <button type="button" (click)="toggleSort('email')" class="group inline-flex items-center">
                                        Email
                                        <span class="ml-2 flex-none rounded-sm" [class.bg-indigo-100]="sortField() === 'email'" [class.text-indigo-600]="sortField() === 'email'" [class.dark:bg-indigo-900/50]="sortField() === 'email'" [class.dark:text-indigo-400]="sortField() === 'email'" [class.invisible]="sortField() !== 'email'" [class.text-surface-500]="sortField() !== 'email'" [class.group-hover:visible]="sortField() !== 'email'">
                                            <i class="pi" [class.pi-sort-up]="sortField() === 'email' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'email' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'email'"></i>
                                        </span>
                                    </button>
                                </th>
                                <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">
                                    <button type="button" (click)="toggleSort('full_name')" class="group inline-flex items-center">
                                        Nombre
                                        <span class="ml-2 flex-none rounded-sm" [class.bg-indigo-100]="sortField() === 'full_name'" [class.text-indigo-600]="sortField() === 'full_name'" [class.dark:bg-indigo-900/50]="sortField() === 'full_name'" [class.dark:text-indigo-400]="sortField() === 'full_name'" [class.invisible]="sortField() !== 'full_name'" [class.text-surface-500]="sortField() !== 'full_name'" [class.group-hover:visible]="sortField() !== 'full_name'">
                                            <i class="pi" [class.pi-sort-up]="sortField() === 'full_name' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'full_name' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'full_name'"></i>
                                        </span>
                                    </button>
                                </th>
                                <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">
                                    <button type="button" (click)="toggleSort('role')" class="group inline-flex items-center">
                                        Rol
                                        <span class="ml-2 flex-none rounded-sm" [class.bg-indigo-100]="sortField() === 'role'" [class.text-indigo-600]="sortField() === 'role'" [class.dark:bg-indigo-900/50]="sortField() === 'role'" [class.dark:text-indigo-400]="sortField() === 'role'" [class.invisible]="sortField() !== 'role'" [class.text-surface-500]="sortField() !== 'role'" [class.group-hover:visible]="sortField() !== 'role'">
                                            <i class="pi" [class.pi-sort-up]="sortField() === 'role' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'role' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'role'"></i>
                                        </span>
                                    </button>
                                </th>
                                <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">Tenant</th>
                                <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">
                                    <button type="button" (click)="toggleSort('is_active')" class="group inline-flex items-center">
                                        Estado
                                        <span class="ml-2 flex-none rounded-sm" [class.bg-indigo-100]="sortField() === 'is_active'" [class.text-indigo-600]="sortField() === 'is_active'" [class.dark:bg-indigo-900/50]="sortField() === 'is_active'" [class.dark:text-indigo-400]="sortField() === 'is_active'" [class.invisible]="sortField() !== 'is_active'" [class.text-surface-500]="sortField() !== 'is_active'" [class.group-hover:visible]="sortField() !== 'is_active'">
                                            <i class="pi" [class.pi-sort-up]="sortField() === 'is_active' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'is_active' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'is_active'"></i>
                                        </span>
                                    </button>
                                </th>
                                <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">
                                    <button type="button" (click)="toggleSort('date_joined')" class="group inline-flex items-center">
                                        Registro
                                        <span class="ml-2 flex-none rounded-sm" [class.bg-indigo-100]="sortField() === 'date_joined'" [class.text-indigo-600]="sortField() === 'date_joined'" [class.dark:bg-indigo-900/50]="sortField() === 'date_joined'" [class.dark:text-indigo-400]="sortField() === 'date_joined'" [class.invisible]="sortField() !== 'date_joined'" [class.text-surface-500]="sortField() !== 'date_joined'" [class.group-hover:visible]="sortField() !== 'date_joined'">
                                            <i class="pi" [class.pi-sort-up]="sortField() === 'date_joined' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'date_joined' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'date_joined'"></i>
                                        </span>
                                    </button>
                                </th>
                                <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">Último Acceso</th>
                                <th scope="col" class="py-3.5 pl-3 pr-0 text-right text-sm font-semibold text-surface-950 dark:text-surface-0">
                                    <span class="sr-only">Acciones</span>
                                </th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-surface-200 dark:divide-surface-700">
                            @for (user of sortedUsers(); track user.id) {
                                <tr class="hover:bg-surface-50 dark:hover:bg-surface-800/50">
                                    <td class="py-4 pr-3 pl-4 text-sm whitespace-nowrap sm:pl-0" style="width:3rem">
                                        <input type="checkbox" [checked]="isSelected(user)" (change)="toggleSelection(user)" [attr.aria-label]="'Seleccionar usuario ' + user.full_name" class="h-4 w-4 rounded border-surface-300 text-primary focus:ring-primary dark:border-surface-600" />
                                    </td>
                                    <td class="px-3 py-4 text-sm whitespace-nowrap text-surface-700 dark:text-surface-200">{{ user.email }}</td>
                                    <td class="px-3 py-4 text-sm font-medium whitespace-nowrap text-surface-950 dark:text-surface-0">{{ user.full_name }}</td>
                                    <td class="px-3 py-4 text-sm whitespace-nowrap">
                                        <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium" [class]="getRoleBadgeClass(user.role)">
                                            {{ user.role }}
                                        </span>
                                    </td>
                                    <td class="px-3 py-4 text-sm whitespace-nowrap text-surface-500 dark:text-surface-400">{{ user.tenant_name || 'N/A' }}</td>
                                    <td class="px-3 py-4 text-sm whitespace-nowrap">
                                        <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium" [class]="getStatusBadgeClass(user.is_active)">
                                            {{ user.is_active ? 'Activo' : 'Inactivo' }}
                                        </span>
                                    </td>
                                    <td class="px-3 py-4 text-sm whitespace-nowrap text-surface-500 dark:text-surface-400">{{ user.date_joined | date: 'dd/MM/yyyy' }}</td>
                                    <td class="px-3 py-4 text-sm whitespace-nowrap text-surface-500 dark:text-surface-400">{{ user.last_login | date: 'dd/MM/yyyy' }}</td>
                                    <td class="py-4 pl-3 pr-0 text-right text-sm whitespace-nowrap">
                                        <div class="flex items-center justify-end gap-2">
                                            <button type="button" (click)="editUser(user)" class="text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300">
                                                Editar<span class="sr-only">, {{ user.full_name }}</span>
                                            </button>
                                            <button type="button" (click)="deleteUser(user)" [attr.aria-label]="'Eliminar usuario ' + user.full_name" class="text-red-600 hover:text-red-500 dark:text-red-400 dark:hover:text-red-300">
                                                <i class="pi pi-trash"></i>
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            } @empty {
                                <tr>
                                    <td colspan="9" class="px-3 py-12 text-center text-sm text-surface-500 dark:text-surface-400">
                                        @if (loading()) {
                                            <i class="pi pi-spin pi-spinner mr-2"></i>
                                            Cargando usuarios...
                                        } @else {
                                            No hay usuarios registrados.
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
                                <select [value]="pageSize()" (change)="changePageSize($event)" aria-label="Cantidad de registros por página" class="rounded-md border border-surface-200 bg-surface-0 px-2 py-1 text-sm dark:border-surface-700 dark:bg-surface-800">
                                    <option value="10">10</option>
                                    <option value="20">20</option>
                                    <option value="30">30</option>
                                </select>
                            </div>
                            <div class="flex items-center gap-2">
                                <button type="button" (click)="prevPage()" [disabled]="currentPage() === 0" aria-label="Página anterior" class="inline-flex items-center rounded-lg border border-surface-200 bg-surface-0 px-3 py-1.5 text-sm font-medium text-surface-700 shadow-sm hover:bg-surface-50 disabled:opacity-50 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:hover:bg-surface-700">
                                    <i class="pi pi-chevron-left mr-1 text-xs"></i>
                                    Anterior
                                </button>
                                <span class="text-sm text-surface-500 dark:text-surface-400">{{ currentPage() + 1 }} de {{ totalPages() }}</span>
                                <button type="button" (click)="nextPage()" [disabled]="currentPage() >= totalPages() - 1" aria-label="Siguiente página" class="inline-flex items-center rounded-lg border border-surface-200 bg-surface-0 px-3 py-1.5 text-sm font-medium text-surface-700 shadow-sm hover:bg-surface-50 disabled:opacity-50 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:hover:bg-surface-700">
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

        <p-dialog [(visible)]="userDialog" [style]="{ width: '450px' }" [breakpoints]="{'960px':'75vw','640px':'100vw'}" [header]="dialogHeader" [modal]="true">
            <ng-template #content>
                <div class="flex flex-col gap-6">
                    <div>
                        <label for="email" class="block font-bold mb-3">Email</label>
                        <input type="email" pInputText id="email" [(ngModel)]="user.email" required autofocus fluid />
                        @if (submitted && !user.email) {
                            <small class="text-red-500">El email es obligatorio.</small>
                        }
                    </div>

                    <div>
                        <label for="full_name" class="block font-bold mb-3">Nombre Completo</label>
                        <input type="text" pInputText id="full_name" [(ngModel)]="user.full_name" required fluid />
                        @if (submitted && !user.full_name) {
                            <small class="text-red-500">El nombre es obligatorio.</small>
                        }
                    </div>

                    <div>
                        <label for="role" class="block font-bold mb-3">Rol</label>
                        <p-select [(ngModel)]="user.role" inputId="role" [options]="roleOptions()" appendTo="body" optionLabel="label" optionValue="value" placeholder="Seleccionar rol" fluid />
                    </div>

                    @if (requiresTenant(user.role)) {
                        <div>
                            <label for="tenant" class="block font-bold mb-3">Tenant</label>
                            <p-select [(ngModel)]="user.tenant" inputId="tenant" [options]="tenantOptions()" appendTo="body" optionLabel="name" optionValue="id" placeholder="Seleccionar tenant" fluid />
                            @if (submitted && requiresTenant(user.role) && !user.tenant) {
                                <small class="text-red-500">El tenant es obligatorio para este rol.</small>
                            }
                        </div>
                    }

                    @if (!user.id) {
                        <div>
                            <label for="password" class="block font-bold mb-3">Contraseña</label>
                            <input type="password" pInputText id="password" [(ngModel)]="user.password" required fluid />
                            @if (submitted && !user.password && !user.id) {
                                <small class="text-red-500">La contraseña es obligatoria para nuevos usuarios.</small>
                            }
                            @if (submitted && !!user.password && !isValidPassword(user.password)) {
                                <small class="text-red-500">
                                    La contraseña debe tener al menos 8 caracteres.
                                </small>
                            }
                            @if (!submitted || !user.password) {
                                <small class="text-surface-500 dark:text-surface-400 block mt-2">
                                    Mínimo 8 caracteres.
                                </small>
                            }
                        </div>
                    }

                    <div class="flex items-center gap-2">
                        <input type="checkbox" id="is_active" [(ngModel)]="user.is_active" />
                        <label for="is_active">Activo</label>
                    </div>
                </div>
            </ng-template>

            <ng-template #footer>
                <p-button label="Cancelar" icon="pi pi-times" text (click)="hideDialog()" />
                <p-button label="Guardar" icon="pi pi-check" (click)="saveUser()" [loading]="saving()" />
            </ng-template>
        </p-dialog>

        <p-dialog
            [(visible)]="limitDialog"
            [modal]="true"
            [style]="{ width: '32rem' }"
            header="Límite del plan alcanzado"
            [draggable]="false"
            [resizable]="false"
        >
            <div class="space-y-3">
                <div class="flex items-start gap-3">
                    <i class="pi pi-lock text-amber-500 text-xl mt-1"></i>
                    <div>
                        <div class="font-semibold text-surface-900 dark:text-surface-0">{{ limitDialogTitle }}</div>
                        <p class="mt-2 text-sm text-surface-500 dark:text-surface-400 m-0">{{ limitDialogMessage }}</p>
                        <div *ngIf="limitDialogRecommendation" class="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-100">
                            <div class="font-semibold">Plan recomendado: {{ limitDialogRecommendation.nextPlanName }}</div>
                            <p class="mt-1 mb-0">{{ limitDialogRecommendation.reason }}</p>
                            <p class="mt-1 mb-0 opacity-90">{{ limitDialogRecommendation.detail }}</p>
                        </div>
                    </div>
                </div>
            </div>
            <ng-template #footer>
                <p-button label="Entendido" icon="pi pi-check" (click)="limitDialog = false" />
            </ng-template>
        </p-dialog>

        <p-confirmdialog [style]="{ width: '450px' }" />
        <p-toast />
    `,
    providers: [MessageService, ConfirmationService]
})
export class UsersManagement implements OnInit {
    private readonly errorLogger = inject(AdminErrorLogService);

    userDialog: boolean = false;
    users = signal<User[]>([]);
    tenantOptions = signal<any[]>([]);
    roleOptions = signal<any[]>([]);
    user!: User;
    selectedUsersSet = signal<Set<number>>(new Set());
    selectedTenantFilter: number | null = null;
    limitDialog = false;
    limitDialogTitle = 'Límite del plan alcanzado';
    limitDialogMessage = '';
    limitDialogRecommendation: ReturnType<PlanAccessService['getUpgradeRecommendation']> = null;
    submitted: boolean = false;
    loading = signal(false);
    saving = signal(false);
    isSuperAdminView = signal(false);
    sortField = signal<string>('date_joined');
    sortOrder = signal<'asc' | 'desc'>('desc');
    currentPage = signal(0);
    pageSize = signal(10);
    globalFilter = signal('');

    sortedUsers = computed(() => {
        const all = this.users();
        const field = this.sortField();
        const order = this.sortOrder();
        const filter = this.globalFilter().toLowerCase();
        let filtered = all;
        if (filter) {
            filtered = all.filter(u =>
                (u.email?.toLowerCase() || '').includes(filter) ||
                (u.full_name?.toLowerCase() || '').includes(filter) ||
                (u.role?.toLowerCase() || '').includes(filter) ||
                (u.tenant_name?.toLowerCase() || '').includes(filter)
            );
        }
        const sorted = [...filtered].sort((a, b) => {
            const aVal = String(a[field as keyof User] ?? '');
            const bVal = String(b[field as keyof User] ?? '');
            return order === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
        });
        const start = this.currentPage() * this.pageSize();
        return sorted.slice(start, start + this.pageSize());
    });

    totalRecords = computed(() => {
        const all = this.users();
        const filter = this.globalFilter().toLowerCase();
        if (!filter) return all.length;
        return all.filter(u =>
            (u.email?.toLowerCase() || '').includes(filter) ||
            (u.full_name?.toLowerCase() || '').includes(filter) ||
            (u.role?.toLowerCase() || '').includes(filter) ||
            (u.tenant_name?.toLowerCase() || '').includes(filter)
        ).length;
    });

    totalPages = computed(() => Math.max(1, Math.ceil(this.totalRecords() / this.pageSize())));
    firstRecord = computed(() => this.currentPage() * this.pageSize());
    lastRecord = computed(() => Math.min(this.firstRecord() + this.pageSize(), this.totalRecords()));

    allSelected = computed(() => {
        const displayed = this.sortedUsers();
        const set = this.selectedUsersSet();
        return displayed.length > 0 && displayed.every(u => u.id && set.has(u.id));
    });

    get selectedUsers(): User[] {
        const set = this.selectedUsersSet();
        return this.users().filter(u => u.id && set.has(u.id));
    }

    constructor(
        private destroyRef: DestroyRef,
        private authService: AuthService,
        private tenantService: TenantService,
        private roleService: RoleService,
        private planAccessService: PlanAccessService,
        private messageService: MessageService,
        private confirmationService: ConfirmationService
    ) {}

    ngOnInit() {
        const currentUser = this.authService.getCurrentUser();
        this.isSuperAdminView.set(this.isSuperAdmin(currentUser?.role));

        if (!this.isSuperAdminView()) {
            this.loadUsers();
        } else {
            this.users.set([]);
        }

        this.loadTenants();
        this.loadRoles();
    }

    loadUsers() {
        if (this.isSuperAdminView() && !this.selectedTenantFilter) {
            this.users.set([]);
            this.loading.set(false);
            return;
        }

        this.loading.set(true);
        const params = this.isSuperAdminView() && this.selectedTenantFilter ? { tenant: this.selectedTenantFilter } : undefined;
        this.authService.getUsers(params).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (data: any) => {
                this.users.set(this.normalizeUsers(data));
                this.loading.set(false);
            },
            error: (error) => this.handleLoadUsersError(error)
        });
    }

    loadTenants() {
        const currentUser = this.authService.getCurrentUser();
        
        if (this.isSuperAdmin(currentUser?.role)) {
            // SuperAdmin puede ver todos los tenants
            this.tenantService.getTenants().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
                next: (data: any) => {
                    const tenants = Array.isArray(data) ? data : data.results || [];
                    const options = tenants.map((t: any) => ({ name: t.name, id: t.id }));
                    this.tenantOptions.set(options);
                },
                error: (error) => this.handleLoadTenantsError(error)
            });
        } else {
            // Para Client-Admin, obtener tenant desde safeGetItem
            const tenantData = safeGetItem('tenant');
            if (tenantData) {
                try {
                    const tenant = JSON.parse(tenantData);
                    const options = [{ name: tenant.name, id: tenant.id }];
                    this.tenantOptions.set(options);
                } catch (error) {
                    
                    this.tenantOptions.set([]);
                }
            } else {
                this.tenantOptions.set([]);
            }
        }
    }

    loadRoles() {
        this.roleService.getRoles().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (roles: any) => {
                const rolesArray = Array.isArray(roles) ? roles : roles.results || [];
                const options = rolesArray
                    .filter((r: any) => r.scope === 'TENANT')
                    .map((r: any) => ({ label: r.description || r.name, value: r.name }));
                this.roleOptions.set(options.length > 0 ? options : this.getDefaultRoleOptions());
            },
            error: (error) => {
                this.roleOptions.set(this.getDefaultRoleOptions());
            }
        });
    }

    filterByTenant() {
        const currentUser = this.authService.getCurrentUser();
        
        if (this.isSuperAdmin(currentUser?.role)) {
            this.loadUsers();
        } else {
            // Client-Admin siempre ve solo sus usuarios
            this.loadUsers();
        }
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

    isSelected(user: User): boolean {
        return user.id ? this.selectedUsersSet().has(user.id) : false;
    }

    toggleSelection(user: User) {
        if (!user.id) return;
        const set = new Set(this.selectedUsersSet());
        if (set.has(user.id)) {
            set.delete(user.id);
        } else {
            set.add(user.id);
        }
        this.selectedUsersSet.set(set);
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

    getRoleBadgeClass(role: string | undefined): string {
        const r = role || '';
        return UIHelpers.getRoleSeverity(r) === 'info' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' :
               UIHelpers.getRoleSeverity(r) === 'success' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' :
               UIHelpers.getRoleSeverity(r) === 'warn' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' :
               'bg-surface-100 text-surface-700 dark:bg-surface-800 dark:text-surface-300';
    }

    getStatusBadgeClass(isActive: boolean | undefined): string {
        return isActive
            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
            : 'bg-surface-100 text-surface-500 dark:bg-surface-800 dark:text-surface-400';
    }

    openNew() {
        if (!this.isSuperAdminView()) {
            const status = this.planAccessService.getUserLimitStatus(this.getCurrentUserCountForCurrentTenant());
            if (status.reached) {
                this.showUserLimitDialog(this.planAccessService.getUserLimitMessage(status));
                return;
            }
        }

        this.user = {
            is_active: true,
            role: 'Client-Staff',
            tenant: this.isSuperAdminView() ? (this.selectedTenantFilter || undefined) : this.getDefaultTenantId()
        };
        this.submitted = false;
        this.userDialog = true;
    }

    editUser(user: User) {
        this.user = { ...user };
        this.userDialog = true;
    }

    toggleSelectAll(event: Event) {
        const checked = (event.target as HTMLInputElement).checked;
        const set = new Set(this.selectedUsersSet());
        if (checked) {
            this.sortedUsers().forEach(u => { if (u.id) set.add(u.id); });
        } else {
            this.sortedUsers().forEach(u => { if (u.id) set.delete(u.id); });
        }
        this.selectedUsersSet.set(set);
    }

    deleteSelectedUsers() {
        const selected = this.selectedUsers;
        if (!selected.length) return;

        this.confirmationService.confirm({
            message: '¿Estás seguro de eliminar los usuarios seleccionados?',
            header: 'Confirmar',
            icon: 'pi pi-exclamation-triangle',
            accept: () => this.performBulkDelete()
        });
    }

    private performBulkDelete(): void {
        const userIds = this.selectedUsers.map(u => u.id!).filter(id => id);
        this.authService.bulkDeleteUsers(userIds).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: () => {
                this.loadUsers();
                this.selectedUsersSet.set(new Set());
                this.showSuccessMessage('Usuarios eliminados');
            },
            error: (error) => this.showErrorMessage('Error al eliminar usuarios', error)
        });
    }

    deleteUser(user: User) {
        if (!user.id) return;

        this.confirmationService.confirm({
            message: `¿Estás seguro de eliminar a ${user.email || 'este usuario'}?`,
            header: 'Confirmar',
            icon: 'pi pi-exclamation-triangle',
            accept: () => this.performUserDelete(user.id!)
        });
    }

    private performUserDelete(userId: number): void {
        this.authService.deleteUser(userId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: () => {
                this.loadUsers();
                this.showSuccessMessage('Usuario eliminado');
            },
            error: (error) => this.showErrorMessage('Error al eliminar usuario', error)
        });
    }

    hideDialog() {
        this.userDialog = false;
        this.submitted = false;
    }

    get dialogHeader(): string {
        return this.user?.id ? 'Editar Usuario' : 'Nuevo Usuario';
    }

    saveUser() {
        this.submitted = true;
        if (!this.isUserFormValid()) return;

        this.saving.set(true);

        if (this.user.id) {
            this.updateUser();
        } else if (this.userNeedsTenant()) {
            this.checkUserLimits();
        } else {
            this.createUser();
        }
    }

    checkUserLimits() {
        if (!this.user.tenant) {
            this.createUser();
            return;
        }

        // Usar datos del tenant desde safeGetItem si está disponible
        const tenantData = safeGetItem('tenant');
        if (tenantData && this.user.tenant) {
            try {
                const tenant = JSON.parse(tenantData);
                if (tenant.id === this.user.tenant) {
                    this.validateUserLimits(tenant);
                    return;
                }
            } catch (error) {
                
            }
        }

        // Fallback a API call
        this.tenantService.getTenantById(this.user.tenant).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (tenant: any) => this.validateUserLimits(tenant),
            error: () => {
                this.showErrorMessage('No se pudo verificar los límites del plan');
                this.saving.set(false);
            }
        });
    }

    private validateUserLimits(tenant: any): void {
        const currentUsers = this.getCurrentUserCount();
        const maxUsers = tenant.subscription_plan?.max_users || 0;

        if (this.isUserLimitExceeded(currentUsers, maxUsers)) {
            this.showUserLimitError(maxUsers);
            this.saving.set(false);
            return;
        }

        this.createUser();
    }

    private getCurrentUserCount(): number {
        return this.users().filter((u) => u.tenant === this.user.tenant && u.is_active).length;
    }

    private getCurrentUserCountForCurrentTenant(): number {
        const tenantData = safeGetItem('tenant');
        if (!tenantData) {
            return 0;
        }

        try {
            const tenant = JSON.parse(tenantData);
            return this.users().filter((u) => u.tenant === tenant.id && u.is_active).length;
        } catch {
            return 0;
        }
    }

    createUser() {
        const userData = {
            email: this.user.email!,
            full_name: this.user.full_name!,
            role: this.toBackendRole(this.user.role),
            tenant: this.user.tenant || undefined,
            is_active: this.user.is_active ?? true,
            password: this.user.password!
        };

        this.authService.createUser(userData).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (newUser) => {
                this.users.set([...this.users(), newUser]);
                this.showSuccessMessage('Usuario creado');
                this.closeDialog();
            },
            error: (error) => {
                this.showErrorMessage('Error al crear usuario', error);
                this.saving.set(false);
            }
        });
    }

    private isUserLimitExceeded(currentUsers: number, maxUsers: number): boolean {
        return maxUsers > 0 && currentUsers >= maxUsers;
    }

    private showUserLimitError(maxUsers: number): void {
        const sanitizedMaxUsers = Math.max(0, Math.floor(maxUsers));
        this.showUserLimitDialog(`El tenant ha alcanzado el límite de ${sanitizedMaxUsers} usuarios activos.`);
    }

    private showUserLimitDialog(message: string): void {
        this.limitDialogTitle = 'No se puede crear el usuario';
        this.limitDialogMessage = message;
        this.limitDialogRecommendation = this.planAccessService.getUpgradeRecommendation('users', message);
        this.limitDialog = true;
    }

    private showSuccessMessage(detail: string): void {
        this.messageService.add({
            severity: 'success',
            summary: 'Éxito',
            detail,
            life: 3000
        });
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

    private isUserFormValid(): boolean {
        return (
            !!this.user.email?.trim() &&
            !!this.user.full_name?.trim() &&
            (!!this.user.id || this.isValidPassword(this.user.password)) &&
            (!this.userNeedsTenant() || !!this.user.tenant)
        );
    }

    private userNeedsTenant(): boolean {
        return this.requiresTenant(this.user.role);
    }

    requiresTenant(role?: string): boolean {
        const key = roleKey(role);
        return !!key && key !== 'SUPER_ADMIN';
    }

    private isSuperAdmin(role?: string): boolean {
        return roleKey(role) === 'SUPER_ADMIN';
    }

    private updateUser(): void {
        const updateData: any = {
            email: this.user.email,
            full_name: this.user.full_name,
            role: this.toBackendRole(this.user.role),
            tenant: this.user.tenant || undefined,
            is_active: this.user.is_active ?? true
        };

        // No incluir password en updates
        // Solo incluir phone si existe
        if (this.user.phone) {
            updateData.phone = this.user.phone;
        }

        this.authService.updateUser(this.user.id!, updateData).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (updatedUser) => {
                this.updateUserInList(updatedUser);
                this.showSuccessMessage('Usuario actualizado');
                this.closeDialog();
            },
            error: (error) => {
                
                this.showErrorMessage('Error al actualizar usuario', error);
                this.saving.set(false);
            }
        });
    }

    private updateUserInList(updatedUser: User): void {
        const users = [...this.users()];
        const index = users.findIndex((u) => u.id === this.user.id);
        if (index !== -1) {
            users[index] = updatedUser;
            this.users.set(users);
        }
    }

    private closeDialog(): void {
        this.userDialog = false;
        this.saving.set(false);
    }

    private handleLoadUsersError(error: any): void {
        this.logError('Failed to load users', error);
        this.users.set([]);
        this.loading.set(false);
    }

    private handleLoadTenantsError(error: any): void {
        this.logError('Failed to load tenants', error);
        this.tenantOptions.set([]);
    }

    private handleFilterError(error: any): void {
        this.logError('Failed to filter users', error);
        this.users.set([]);
    }

    private sanitizeErrorMessage(error: any, fallback: string): string {
        const apiError = error?.error;
        const directMessage = apiError?.message || apiError?.error || error?.message;

        if (typeof directMessage === 'string' && directMessage.trim()) {
            return directMessage.substring(0, 200);
        }

        if (apiError && typeof apiError === 'object') {
            const parts = Object.entries(apiError)
                .flatMap(([field, value]) => {
                    if (Array.isArray(value)) {
                        return value.map((item) => `${field}: ${String(item)}`);
                    }
                    if (typeof value === 'string') {
                        return [`${field}: ${value}`];
                    }
                    return [];
                })
                .filter(Boolean);

            if (parts.length > 0) {
                return parts.join(' | ').substring(0, 200);
            }
        }

        return fallback;
    }

    private logError(context: string, error: any): void {
        this.errorLogger.log('UsersManagement', context, error);
    }

    private toBackendRole(role?: string): string | undefined {
        const key = roleKey(role);
        const map: Record<string, string> = {
            SUPER_ADMIN: 'SuperAdmin',
            CLIENT_ADMIN: 'Client-Admin',
            CLIENT_STAFF: 'Client-Staff',
            ESTILISTA: 'Estilista',
            CAJERA: 'Cajera',
            MANAGER: 'Manager',
            UTILITY: 'Utility'
        };

        return map[key] || role;
    }

    private normalizeUsers(data: any): User[] {
        const users = Array.isArray(data) ? data : data?.results || [];
        const filteredUsers = users.filter((u: any) => u?.role && u.role !== 'SuperAdmin' && u.role !== 'SUPER_ADMIN');
        return filteredUsers.map((u: any) => ({
            ...u,
            tenant_name: u.tenant?.name || u.tenant_name || 'N/A'
        }));
    }

    private getDefaultTenantId(): number | undefined {
        const options = this.tenantOptions();
        if (!Array.isArray(options) || options.length === 0) return undefined;
        const candidate = Number(options[0]?.id);
        return Number.isNaN(candidate) ? undefined : candidate;
    }

    private getDefaultRoleOptions(): Array<{ label: string; value: string }> {
        return [
            { label: 'Administrador de Peluqueria', value: 'Client-Admin' },
            { label: 'Empleado', value: 'Client-Staff' },
            { label: 'Estilista', value: 'Estilista' },
            { label: 'Cajera', value: 'Cajera' },
            { label: 'Manager', value: 'Manager' },
            { label: 'Utility', value: 'Utility' }
        ];
    }

     isValidPassword(password?: string | null): boolean {
        return !!password && password.trim().length >= 8;
    }

    UIHelpers = UIHelpers;
}
