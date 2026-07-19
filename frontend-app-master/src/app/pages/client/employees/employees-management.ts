import { Component, DestroyRef, OnInit, inject, signal, computed, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { CheckboxModule } from 'primeng/checkbox';
import { ToastModule } from 'primeng/toast';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { CardModule } from 'primeng/card';
import { TabsModule } from 'primeng/tabs';
import { InputNumberModule } from 'primeng/inputnumber';
import { SelectModule } from 'primeng/select';
import { MultiSelectModule } from 'primeng/multiselect';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { MenuModule } from 'primeng/menu';
import { Menu } from 'primeng/menu';
import { MessageService } from 'primeng/api';
import { ConfirmationService } from 'primeng/api';
import { MenuItem } from 'primeng/api';
import { EmployeeService, Employee, UpdateEmployeeRequest } from '../../../core/services/employee/employee.service';
import { ServiceService } from '../../../core/services/service/service.service';
import { AuthService, User } from '../../../core/services/auth/auth.service';
import { BranchService, Branch } from '../../../core/services/branch/branch.service';
import { environment } from '../../../../environments/environment';
import { firstValueFrom } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { UserDto, CreateUserDto, UpdateUserDto } from '../../../core/dto/user.dto';
import { EmployeeDto, EmployeeWithUserDto, CreateEmployeeDto, UpdateEmployeeDto } from '../../../core/dto/employee.dto';
import { PayrollConfigDto, PaymentStatsDto, PaymentReceiptDto } from '../../../core/dto/payroll.dto';
import { LoanDto, LoanSummaryDto, CreateLoanDto } from '../../../core/dto/loan.dto';
import { EMPLOYEE_CONFIG } from '../../../core/config/employee.config';
import { SettingsService } from '../../../core/services/settings/settings.service';
import { PlanAccessService } from '../../../core/services/plan-access.service';
import { AppCurrencyPipe } from '../../../core/pipes/app-currency.pipe';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { I18nPipe } from '../../../core/pipes/i18n.pipe';
import { TooltipModule } from 'primeng/tooltip';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { AuronPaginationComponent } from '../../../shared/components/auron-pagination/auron-pagination.component';
import { AuBtn, AuSkeleton } from '../../../shared/components';
import {
  getRoleDisplayLabel,
  isServiceAssignableRole as isServiceAssignableBusinessRole,
  resolveBusinessRole
} from '../../../core/utils/role-normalizer';

// Interface temporal para PaymentDto hasta que se agregue al archivo payroll.dto
interface PaymentDto {
  id: number;
  employee_id: number;
  employee_name: string;
  period_display: string;
  gross_amount: number;
  net_amount: number;
  total_deductions: number;
  payment_method: string;
  payment_reference?: string;
  paid_at: string;
}

@Component({
  selector: 'app-employees-management',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    EmptyStateComponent,
    AuronPaginationComponent,
    AuBtn,
    ButtonModule,
    DialogModule,
    InputTextModule,
    CheckboxModule,
    ToastModule,
    ConfirmDialogModule,
    CardModule,
    TabsModule,
    InputNumberModule,
    SelectModule,
    MultiSelectModule,
    AppCurrencyPipe,
    TableModule,
    TagModule,
    MenuModule,
    I18nPipe,
    TooltipModule,
    AuSkeleton
  ],
  providers: [MessageService, ConfirmationService],
  styles: [`
    /* ===== ROSTER HEADER ===== */
    .employees-roster-header {
      display: flex;
      flex-direction: column;
      gap: 0;
      overflow: hidden;
      border-radius: 1.75rem;
      border: 1px solid var(--surface-border);
      background: var(--surface-card);
      margin-bottom: 1.5rem;
    }
    .employees-roster-header__top {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 1rem;
      padding: 1.5rem 1.75rem 1.25rem;
      flex-wrap: wrap;
    }
    .employees-roster-header__title {
      margin: 0;
      font-size: 1.6rem;
      font-weight: 700;
      line-height: 1.1;
      letter-spacing: -0.02em;
      color: var(--text-color);
    }
    .employees-roster-header__desc {
      margin: 0.35rem 0 0;
      font-size: 0.9rem;
      color: var(--text-color-secondary);
      max-width: 36rem;
    }
    .employees-roster-header__add-btn { flex-shrink: 0; }

    /* ===== ROSTER STRIP ===== */
    .employees-roster-strip {
      display: flex;
      align-items: flex-start;
      gap: 1.25rem;
      padding: 1rem 1.75rem 1.25rem;
      overflow-x: auto;
      border-top: 1px solid var(--surface-border);
      border-bottom: 1px solid var(--surface-border);
      background: color-mix(in srgb, var(--surface-ground) 60%, var(--surface-card) 40%);
      scrollbar-width: none;
    }
    .employees-roster-strip::-webkit-scrollbar { display: none; }
    .employees-roster-avatar {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.3rem;
      flex-shrink: 0;
      position: relative;
      width: 4rem;
      cursor: default;
    }
    .employees-roster-avatar__circle {
      width: 3.5rem;
      height: 3.5rem;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1rem;
      font-weight: 700;
      color: #fff;
      letter-spacing: 0.02em;
    }
    .employees-roster-avatar__name {
      font-size: 0.72rem;
      font-weight: 600;
      color: var(--text-color);
      text-align: center;
      width: 4rem;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .employees-roster-avatar__role {
      font-size: 0.65rem;
      color: var(--text-color-secondary);
      text-align: center;
      width: 4rem;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .employees-roster-avatar__status {
      position: absolute;
      top: 0.1rem;
      right: 0.35rem;
      width: 0.75rem;
      height: 0.75rem;
      border-radius: 50%;
      border: 2px solid var(--surface-card);
      background: var(--surface-400);
    }
    .employees-roster-avatar__status.is-active { background: #10b981; }
    .employees-roster-empty {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      color: var(--text-color-secondary);
      font-size: 0.85rem;
      padding: 0.5rem 0;
    }

    /* ===== STATS STRIP ===== */
    .employees-roster-stats {
      display: flex;
      align-items: center;
      gap: 2rem;
      padding: 0.9rem 1.75rem;
      flex-wrap: wrap;
    }
    .employees-roster-stat { display: flex; flex-direction: column; gap: 0.1rem; }
    .employees-roster-stat__value {
      font-size: 1.35rem;
      font-weight: 800;
      line-height: 1;
      color: var(--text-color);
    }
    .employees-roster-stat__label {
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: var(--text-color-secondary);
    }
    .employees-roster-stat--ok .employees-roster-stat__value { color: #10b981; }
    .employees-roster-stat--blue .employees-roster-stat__value { color: var(--brand); }
    .employees-roster-stat__hint {
      margin-left: auto;
      font-size: 0.8rem;
      color: var(--text-color-secondary);
      max-width: 28rem;
      text-align: right;
    }

    /* ===== EMPTY STATE ===== */
    .employees-empty {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.75rem;
      padding: 3rem 2rem;
      text-align: center;
    }
    .employees-empty__avatar-placeholder {
      width: 4rem;
      height: 4rem;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(26,86,219,0.08);
      color: var(--brand);
      font-size: 1.5rem;
    }
    .employees-empty__title {
      font-size: 1rem;
      font-weight: 600;
      color: var(--text-color);
    }
    .employees-empty__desc {
      margin: 0;
      font-size: 0.85rem;
      color: var(--text-color-secondary);
      max-width: 24rem;
    }

    @media (max-width: 640px) {
      .employees-roster-stats { gap: 1rem; }
      .employees-roster-stat__hint { display: none; }
      .employees-roster-header__top { padding: 1rem 1.25rem 0.9rem; }
      .employees-roster-strip { padding: 0.9rem 1.25rem 1rem; }
    }
  `],
  template: `
    <div class="space-y-6">
      <section class="employees-roster-header">
        <div class="employees-roster-header__top">
          <div>
            <h1 class="employees-roster-header__title display-3">{{ 'employees.title' | t }}</h1>
            <p class="employees-roster-header__desc">{{ 'employees.subtitle' | t }}</p>
          </div>
          <button pButton [label]="'employees.btn.add' | t" icon="pi pi-plus"
                  (click)="abrirDialogo()"
                  class="employees-roster-header__add-btn"
                  [disabled]="planAccessService.getEmployeeLimitStatus(usuariosActivos()).reached"
                  [pTooltip]="'employees.limit_dialog.title' | t">
          </button>
        </div>

        <!-- Team roster: avatares en fila -->
        <div class="employees-roster-strip">
          @for (emp of getActiveEmployees(); track emp.id) {
            <div class="employees-roster-avatar" [title]="emp.user.full_name">
              <div class="employees-roster-avatar__circle"
                   [style.background]="getAvatarColor(emp.user.full_name)">
                {{ getInitials(emp.user.full_name) }}
              </div>
              <span class="employees-roster-avatar__status" [class.is-active]="emp.is_active"></span>
              <span class="employees-roster-avatar__name">{{ getFirstName(emp.user.full_name) }}</span>
              <span class="employees-roster-avatar__role">{{ getRoleDisplayName(emp.user.role, emp.user.business_role, emp.user.business_role_display) }}</span>
            </div>
          }
          @if (getActiveEmployees().length === 0 && !cargando()) {
            <div class="employees-roster-empty">
              <i class="pi pi-users"></i>
              <span>{{ 'employees.no_employees' | t }}</span>
            </div>
          }
          @if (cargando()) {
            @for (i of [1,2,3,4]; track i) {
              <div class="employees-roster-avatar">
                <au-skeleton variant="avatar" width="3.5rem" height="3.5rem" />
                <au-skeleton width="52px" height="10px" class="mt-2" />
              </div>
            }
          }
        </div>

        <!-- Stats strip -->
        <div class="employees-roster-stats">
          <div class="employees-roster-stat">
            <span class="employees-roster-stat__value">{{ empleados().length }}</span>
            <span class="employees-roster-stat__label">{{ 'employees.summary.total' | t }}</span>
          </div>
          <div class="employees-roster-stat employees-roster-stat--ok">
            <span class="employees-roster-stat__value">{{ getActiveEmployeesCount() }}</span>
            <span class="employees-roster-stat__label">{{ 'employees.summary.active' | t }}</span>
          </div>
          <div class="employees-roster-stat employees-roster-stat--blue">
            <span class="employees-roster-stat__value">{{ getServiceAssignableCount() }}</span>
            <span class="employees-roster-stat__label">{{ 'employees.summary.assignable' | t }}</span>
          </div>
          <span class="employees-roster-stat__hint">{{ 'employees.narrative_hint' | t }}</span>
        </div>
      </section>

      <section class="overflow-hidden rounded-[1.75rem] border border-surface-200 bg-white shadow-sm dark:border-surface-700 dark:bg-surface-900">
        <div class="px-6 py-5">
          <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <span class="text-sm font-medium text-surface-600 dark:text-surface-400">{{ empleados().length }} {{ 'menu.employees' | t }}</span>
            <div class="flex flex-wrap items-center gap-3">
              <label class="flex items-center gap-2 text-sm text-surface-500 cursor-pointer select-none">
                <input type="checkbox" [checked]="showInactive()" (change)="showInactive.set(!showInactive())" class="h-4 w-4 rounded border-surface-300 text-primary focus:ring-primary dark:border-surface-600" />
                {{ 'employees.show_inactive' | t }}
              </label>
              <div class="relative w-full lg:w-72">
                <i class="pi pi-search absolute left-3 top-1/2 -translate-y-1/2 text-sm text-surface-400"></i>
                <input type="text" (input)="onGlobalFilter($event)" (keyup.enter)="onGlobalFilter($event)" [placeholder]="'employees.search_placeholder' | t" class="w-full rounded-lg border border-surface-200 bg-surface-0 py-2 pl-9 pr-3 text-sm text-surface-700 placeholder-surface-400 shadow-sm focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:placeholder-surface-500" />
              </div>
              <button pButton [label]="'employees.btn.add' | t" icon="pi pi-plus" (click)="abrirDialogo()" class="p-button-success" [disabled]="planAccessService.getEmployeeLimitStatus(usuariosActivos()).reached" [pTooltip]="'employees.limit_dialog.title' | t"></button>
            </div>
          </div>
        </div>

        <div class="flow-root">
          <div class="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
            <div class="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
              <table class="min-w-full divide-y divide-surface-200 dark:divide-surface-700">
                <thead>
                  <tr>
                    <th scope="col" style="width:3rem">
                      <input type="checkbox" [checked]="allSelected()" (change)="toggleSelectAll($event)" class="h-4 w-4 rounded border-surface-300 text-primary focus:ring-primary dark:border-surface-600" />
                    </th>
                    <th scope="col" class="text-left text-sm font-semibold text-surface-950 dark:text-surface-0">
                      <button type="button" (click)="toggleSort('user.full_name')" class="group inline-flex items-center">
                        {{ 'employees.table.employee' | t }}
                        <span class="ml-2 flex-none rounded-sm" [class.bg-blue-100]="sortField() === 'user.full_name'" [class.text-blue-700]="sortField() === 'user.full_name'" [class.dark:bg-blue-900\/50]="sortField() === 'user.full_name'" [class.dark:text-blue-400]="sortField() === 'user.full_name'" [class.invisible]="sortField() !== 'user.full_name'" [class.text-surface-500]="sortField() !== 'user.full_name'" [class.group-hover:visible]="sortField() !== 'user.full_name'">
                          <i class="pi" [class.pi-sort-up]="sortField() === 'user.full_name' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'user.full_name' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'user.full_name'"></i>
                        </span>
                      </button>
                    </th>
                    <th scope="col" class="text-left text-sm font-semibold text-surface-950 dark:text-surface-0">{{ 'employees.table.details' | t }}</th>
                    <th *ngIf="canAccessMultiLocation()" scope="col" class="text-left text-sm font-semibold text-surface-950 dark:text-surface-0">{{ 'appointments.branch' | t }}</th>
                    <th scope="col" class="text-left text-sm font-semibold text-surface-950 dark:text-surface-0">
                      <button type="button" (click)="toggleSort('is_active')" class="group inline-flex items-center">
                        {{ 'employees.table.status' | t }}
                        <span class="ml-2 flex-none rounded-sm" [class.bg-blue-100]="sortField() === 'is_active'" [class.text-blue-700]="sortField() === 'is_active'" [class.dark:bg-blue-900\/50]="sortField() === 'is_active'" [class.dark:text-blue-400]="sortField() === 'is_active'" [class.invisible]="sortField() !== 'is_active'" [class.text-surface-500]="sortField() !== 'is_active'" [class.group-hover:visible]="sortField() !== 'is_active'">
                          <i class="pi" [class.pi-sort-up]="sortField() === 'is_active' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'is_active' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'is_active'"></i>
                        </span>
                      </button>
                    </th>
                    <th scope="col" class="text-right text-sm font-semibold text-surface-950 dark:text-surface-0">
                      <span class="sr-only">{{ 'employees.table.actions' | t }}</span>
                    </th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-surface-200 dark:divide-surface-700">
                  @for (emp of sortedEmployees(); track emp.id) {
                    <tr class="hover:bg-surface-50 dark:hover:bg-surface-800/50">
                      <td style="width:3rem">
                        <input type="checkbox" [checked]="isSelected(emp)" (change)="toggleSelection(emp)" class="h-4 w-4 rounded border-surface-300 text-primary focus:ring-primary dark:border-surface-600" />
                      </td>
                      <!-- Employee: name + role badge inline + email below -->
                      <td>
                        <div class="flex flex-col">
                          <div class="flex items-center gap-2">
                            <span class="font-semibold text-surface-900 dark:text-white">{{ emp.user.full_name }}</span>
                            <span [class]="getRoleBadgeClass(emp)">{{ getRoleDisplayName(emp.user.role, emp.user.business_role, emp.user.business_role_display) }}</span>
                          </div>
                          <span class="text-xs text-surface-500 dark:text-surface-400">{{ emp.user.email }}</span>
                        </div>
                      </td>
                      <!-- Details: specialty + services count + phone -->
                      <td>
                        <div class="flex items-center gap-2">
                          @if (emp.profession) {
                            <span class="inline-flex items-center gap-1 rounded-full bg-[rgba(26,86,219,0.08)] px-2 py-0.5 text-xs font-medium text-[var(--brand)] dark:bg-[rgba(26,86,219,0.15)] dark:text-[var(--brand-400)]">
                              <i class="pi pi-briefcase text-[10px]"></i>
                              {{ getProfessionLabel(emp.profession) }}
                            </span>
                          }
                          @if (isServiceAssignableRole(emp.user.role, emp.user.business_role)) {
                            <span [class]="(emp.services_count || 0) > 0 ? 'inline-flex items-center rounded-full bg-[rgba(26,86,219,0.10)] px-2 py-0.5 text-xs font-medium text-[var(--brand)] dark:bg-[rgba(26,86,219,0.18)] dark:text-[var(--brand-400)]' : 'inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'">
                              {{ (emp.services_count || 0) }} {{ ((emp.services_count || 0) === 1 ? 'pos.servicio' : 'menu.services') | t }}
                            </span>
                          }
                          <span class="text-xs text-surface-400 dark:text-surface-500">{{ emp.phone || '-' }}</span>
                        </div>
                      </td>
                      <!-- Branch -->
                      <td *ngIf="canAccessMultiLocation()">
                        <span class="text-sm text-surface-700 dark:text-surface-200">{{ getBranchName(emp.branch) }}</span>
                      </td>
                      <!-- Status + hire date -->
                      <td>
                        <div class="flex flex-col items-start gap-0.5">
                          <span [class]="'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ' + (emp.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300')">
                            {{ (emp.is_active ? 'employees.status_active' : 'employees.status_inactive') | t }}
                          </span>
                          <span class="text-xs text-surface-400 dark:text-surface-500">{{ emp.hire_date | date:'dd/MM/yyyy' }}</span>
                        </div>
                      </td>
                      <!-- Actions: edit + dropdown -->
                      <td class="text-right">
                        <div class="flex items-center justify-end gap-1">
                          <button type="button" (click)="editarEmpleado(emp)" class="rounded-lg p-1.5 text-blue-700 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/30" [title]="'common.edit' | t">
                            <i class="pi pi-pencil"></i>
                          </button>
                          <button type="button" #actionBtn (click)="openActionMenu($event, emp)" class="rounded-lg p-1.5 text-surface-500 hover:bg-surface-100 dark:text-surface-400 dark:hover:bg-surface-700/50" [title]="'common.more_actions' | t">
                            <i class="pi pi-ellipsis-v"></i>
                          </button>
                        </div>
                      </td>
                    </tr>
                  } @empty {
                    <tr>
                      <td [attr.colspan]="canAccessMultiLocation() ? 7 : 6">
                        @if (cargando()) {
                          <div class="employees-empty p-8 text-center">
                            <i class="pi pi-spin pi-spinner employees-empty__icon"></i>
                            <span>{{ 'employees.loading' | t }}</span>
                          </div>
                        } @else {
                          <app-empty-state
                            title="Tu equipo está vacío"
                            description="Agrega el primer empleado para empezar a asignar citas y calcular comisiones."
                            [actionLabel]="planAccessService.getEmployeeLimitStatus(usuariosActivos()).reached ? undefined : 'employees.btn.add'"
                            (actionClicked)="abrirDialogo()">
                          </app-empty-state>
                        }
                      </td>
                    </tr>
                  }
                </tbody>
              </table>

              <p-menu #actionMenu [model]="actionMenuItems" [popup]="true"></p-menu>
              <auron-pagination
                [currentPage]="currentPage()"
                [totalPages]="totalPages()"
                [pageSize]="pageSize()"
                [totalRecords]="totalRecords()"
                [firstRecord]="firstRecord()"
                [lastRecord]="lastRecord()"
                [showingLabel]="getShowingRecordsText()"
                [pageLabel]="getPageOfText()"
                [pageSizeOptions]="[10, 20, 30]"
                (pageSizeChange)="setPageSize($event)"
                (pageChange)="setPage($event)"
              ></auron-pagination>
            </div>
          </div>
        </div>
      </section>

      <p-dialog [header]="(empleadoSeleccionado ? 'employees.edit' : 'employees.new') | t"
                [(visible)]="mostrarDialogo" [modal]="true" [style]="{width: '620px'}"
                [breakpoints]="{'960px':'75vw','640px':'100vw'}"
                styleClass="shadow-2xl"
                [closable]="!guardando()" [closeOnEscape]="!guardando()">
        <form [formGroup]="formulario" (ngSubmit)="guardarEmpleado()" class="grid gap-5 p-1">
          <div class="rounded-2xl bg-surface-950 p-4 text-white">
            <div class="text-[11px] uppercase tracking-[0.24em] text-surface-400">{{ 'employees.table.employee' | t }}</div>
            <div class="mt-2 text-xl font-black">{{ (empleadoSeleccionado ? 'employees.edit' : 'employees.new') | t }}</div>
            <div class="mt-2 text-sm text-surface-300">{{ 'clients.form_fullname_hint' | t }}</div>
          </div>

          <div>
            <label class="block font-medium mb-1">{{ 'auth.register.owner_name' | t }}</label>
            <input pInputText formControlName="full_name" class="w-full"
                   [class.ng-invalid]="formulario.get('full_name')?.invalid && formulario.get('full_name')?.touched">
          </div>

          <div>
            <label class="block font-medium mb-1">{{ 'employees.email' | t }}</label>
            <input pInputText formControlName="email" type="email" class="w-full"
                   [class.ng-invalid]="formulario.get('email')?.invalid && formulario.get('email')?.touched">
          </div>

          <div *ngIf="!empleadoSeleccionado">
            <label class="block font-medium mb-1">{{ 'auth.password' | t }} *</label>
            <input pInputText formControlName="password" type="password" class="w-full"
                   [class.ng-invalid]="formulario.get('password')?.invalid && formulario.get('password')?.touched">
          </div>

          <div>
            <label class="block font-medium mb-1">{{ 'employees.role' | t }}</label>
            <select formControlName="business_role" class="w-full rounded border border-surface-300 bg-white p-2 text-surface-900 dark:border-surface-600 dark:bg-surface-800 dark:text-surface-100">
              <option *ngFor="let option of rolesOptions()" [value]="option.value">{{option.label}}</option>
            </select>
          </div>

          <div>
            <label class="block font-medium mb-1">{{ 'employees.table.profession' | t }}</label>
            <p-select formControlName="profession" [options]="PROFESSION_OPTIONS" optionLabel="label" optionValue="value" [placeholder]="'employees.profession.placeholder' | t" class="w-full" [showClear]="true"></p-select>
          </div>

          <div>
            <label class="block font-medium mb-1">{{ 'employees.table.phone' | t }}</label>
            <input pInputText formControlName="phone" class="w-full">
          </div>

          <div>
            <label class="block font-medium mb-1">{{ 'employees.hire_date_label' | t }}</label>
            <input type="date" formControlName="hire_date" class="w-full rounded border border-surface-300 bg-white p-2 text-surface-900 dark:border-surface-600 dark:bg-surface-800 dark:text-surface-100">
          </div>

          <div *ngIf="canAccessMultiLocation() && branchService.branches().length > 0">
            <label class="block font-medium mb-1">{{ 'appointments.branch' | t }}</label>
            <p-select formControlName="branch" [options]="branchOptionsForForm()" optionLabel="label" optionValue="value" [placeholder]="'appointments.sucursal' | t" class="w-full" [showClear]="true"></p-select>
          </div>

          <div *ngIf="isServiceAssignableRole(undefined, formulario.get('business_role')?.value)">
            <label class="block font-medium mb-1">{{ 'employees.services_can_perform' | t }}</label>
            <p-multiSelect
              formControlName="service_ids"
              [options]="servicesOptions"
              appendTo="body"
              optionLabel="label"
              optionValue="value"
              [placeholder]="'appointments.seleccionar_servicio' | t"
              class="w-full"
              display="chip"
              [filter]="true"
            ></p-multiSelect>
            <small class="block mt-1 text-surface-500 dark:text-surface-400">
              {{ 'employees.services_can_perform_hint' | t }}
            </small>
          </div>

          <div *ngIf="!isServiceAssignableRole(undefined, formulario.get('business_role')?.value)" class="rounded-lg border border-dashed border-surface-300 dark:border-surface-600 p-3 text-sm text-surface-500 dark:text-surface-400">
            {{ 'employees.no_appointments_role_hint' | t }}
          </div>

          <div class="flex items-center">
            <p-checkbox formControlName="is_active" [binary]="true" inputId="activo"></p-checkbox>
            <label for="activo" class="ml-2 font-medium">{{ 'employees.active_checkbox' | t }}</label>
          </div>

          <div class="flex justify-end gap-2 mt-2">
            <button au-btn variant="ghost"
                    (click)="cerrarDialogo()" [disabled]="guardando()">{{ 'common.cancel' | t }}</button>
            <button au-btn variant="primary"
                    type="submit" [icon]="'pi pi-check'" [loading]="guardando()"
                    [disabled]="formulario.invalid">{{ (empleadoSeleccionado ? 'employees.btn.update' : 'employees.btn.create') | t }}</button>
          </div>
        </form>
      </p-dialog>

      <p-dialog
        [header]="'employees.limit_dialog.title' | t"
        [(visible)]="mostrarDialogoLimitePlan"
        [modal]="true"
        [style]="{width: '32rem'}"
        [breakpoints]="{'960px':'75vw','640px':'100vw'}"
        [draggable]="false"
        [resizable]="false">
        <div class="flex items-start gap-3">
          <i class="pi pi-lock text-amber-500 text-xl mt-1"></i>
          <div>
            <div class="font-semibold text-surface-900 dark:text-white">{{ tituloDialogoLimitePlan }}</div>
            <p class="mt-2 text-sm text-surface-600 dark:text-surface-300">{{ mensajeDialogoLimitePlan }}</p>
            <div *ngIf="recomendacionUpgradePlan" class="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-100">
              <div class="font-semibold">{{ ('employees.limit_dialog.recommended_plan' | t).replace('{plan}', recomendacionUpgradePlan.nextPlanName) }}</div>
              <p class="mt-1 mb-0">{{ recomendacionUpgradePlan.reason }}</p>
              <p class="mt-1 mb-0 opacity-90">{{ recomendacionUpgradePlan.detail }}</p>
            </div>
          </div>
        </div>
        <ng-template pTemplate="footer">
          <div class="flex justify-end gap-2">
            <button au-btn variant="ghost" (click)="mostrarDialogoLimitePlan = false" [icon]="'pi pi-check'">{{ 'appointments.alert.entendido' | t }}</button>
            <button
              *ngIf="recomendacionUpgradePlan"
              au-btn variant="primary"
              [icon]="'pi pi-arrow-up-right'"
              (click)="irAActualizarPlan()">{{ 'employees.limit_dialog.upgrade_btn' | t }}</button>
          </div>
        </ng-template>
      </p-dialog>

      <!-- Diálogo de Configuración de Nómina -->
      <p-dialog [header]="'employees.payroll_dialog.title' | t"
                [(visible)]="mostrarConfigNomina" [modal]="true" [style]="{ width: '92vw', maxWidth: '680px' }"
                styleClass="shadow-2xl"
                [closable]="true">
        <div class="p-4" *ngIf="empleadoDetalle">
          <div [formGroup]="formularioNomina" class="grid gap-4">
            <div class="rounded-2xl bg-surface-950 p-4 text-white">
              <div class="text-[11px] uppercase tracking-[0.24em] text-surface-400">{{ 'menu.payroll' | t }}</div>
              <div class="mt-2 text-xl font-black">{{ getSelectedEmployeeDisplayName() }}</div>
              <div class="mt-2 text-sm text-surface-300">{{ 'employees.payroll_dialog.subtitle' | t }}</div>
            </div>
            <div>
              <label class="block font-medium mb-1">{{ 'employees.payroll_dialog.payment_type' | t }}</label>
              <select formControlName="salary_type" class="w-full rounded border border-surface-300 bg-white p-2 text-surface-900 dark:border-surface-600 dark:bg-surface-800 dark:text-surface-100">
                <option value="fixed">{{ 'payroll.fixed' | t }}</option>
                <option value="commission">{{ 'payroll.commission' | t }}</option>
                <option value="mixed">{{ 'payroll.mixed' | t }}</option>
              </select>
            </div>
            <div>
              <label class="block font-medium mb-1">{{ 'employees.payroll_dialog.payment_frequency' | t }}</label>
              <select formControlName="payment_frequency" class="w-full rounded border border-surface-300 bg-white p-2 text-surface-900 dark:border-surface-600 dark:bg-surface-800 dark:text-surface-100">
                <option value="biweekly">{{ 'payroll.biweekly' | t }}</option>
                <option value="monthly">{{ 'payroll.monthly' | t }}</option>
                <option value="weekly">{{ 'payroll.weekly' | t }}</option>
              </select>
            </div>
            <div>
              <label class="block font-medium mb-1">{{ 'employees.payroll_dialog.commission_pct' | t }}</label>
              <input type="number" formControlName="commission_percentage" min="0" max="100"
                     class="w-full rounded border border-surface-300 bg-white p-2 text-surface-900 dark:border-surface-600 dark:bg-surface-800 dark:text-surface-100">
            </div>
            <div>
              <label class="block font-medium mb-1">{{ ('employees.payroll_dialog.monthly_salary' | t).replace('{currency}', currencySymbol()) }}</label>
              <input type="number" formControlName="contractual_monthly_salary" min="0"
                     class="w-full rounded border border-surface-300 bg-white p-2 text-surface-900 dark:border-surface-600 dark:bg-surface-800 dark:text-surface-100">
            </div>
            <div>
              <label class="block font-medium mb-2">{{ 'employees.payroll_dialog.legal_deductions' | t }}</label>
              <div class="flex gap-4">
                <div class="flex items-center">
                  <p-checkbox formControlName="apply_afp" [binary]="true" inputId="afp"></p-checkbox>
                  <label for="afp" class="ml-2">AFP (2.87%)</label>
                </div>
                <div class="flex items-center">
                  <p-checkbox formControlName="apply_sfs" [binary]="true" inputId="sfs"></p-checkbox>
                  <label for="sfs" class="ml-2">SFS (3.04%)</label>
                </div>
                <div class="flex items-center">
                  <p-checkbox formControlName="apply_isr" [binary]="true" inputId="isr"></p-checkbox>
                  <label for="isr" class="ml-2">ISR</label>
                </div>
              </div>
            </div>
            <div class="flex justify-end gap-2 mt-4">
              <button au-btn variant="ghost"
                      (click)="cerrarConfigNomina()">{{ 'common.cancel' | t }}</button>
              <button au-btn variant="primary" [icon]="'pi pi-save'"
                      [loading]="guardandoNomina()" (click)="guardarConfigNomina()">{{ 'employees.payroll_dialog.save_btn' | t }}</button>
            </div>
          </div>
        </div>
      </p-dialog>

      <!-- Diálogo de Préstamos -->
      <p-dialog [header]="('employees.loans_dialog.title' | t) + ' - ' + (empleadoDetalle?.user?.full_name || '')"
                [(visible)]="mostrarPrestamos" [modal]="true" [style]="{width: '90vw', maxWidth: '1000px'}"
                [breakpoints]="{'960px':'75vw','640px':'100vw'}"
                styleClass="shadow-2xl"
                [closable]="true">
        <div class="p-4" *ngIf="empleadoDetalle">

          <!-- Resumen de Préstamos -->
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6" *ngIf="!cargandoResumenPrestamos()">
            <p-card>
              <div class="text-center">
                <div class="text-2xl font-bold text-surface-700 dark:text-surface-300">{{resumenPrestamos()?.active_loans || 0}}</div>
                <div class="text-sm text-surface-600 dark:text-surface-400">{{ 'employees.loans_dialog.active_loans' | t }}</div>
              </div>
            </p-card>
            <p-card>
              <div class="text-center">
                <div class="text-2xl font-bold text-[var(--brand)]">
                  {{ (resumenPrestamos()?.total_amount || 0) | appCurrency:'1.2-2' }}
                </div>
                <div class="text-sm text-surface-600 dark:text-surface-400">{{ 'employees.loans_dialog.total_loaned' | t }}</div>
              </div>
            </p-card>
            <p-card>
              <div class="text-center">
                <div class="text-2xl font-bold text-[var(--brand)]">
                  {{ (resumenPrestamos()?.remaining_balance || 0) | appCurrency:'1.2-2' }}
                </div>
                <div class="text-sm text-surface-600 dark:text-surface-400">{{ 'employees.loans_dialog.pending_balance' | t }}</div>
              </div>
            </p-card>
            <p-card>
              <div class="text-center">
                <div class="text-2xl font-bold text-[var(--brand)]">
                  {{ (resumenPrestamos()?.next_deduction || 0) | appCurrency:'1.2-2' }}
                </div>
                <div class="text-sm text-surface-600 dark:text-surface-400">{{ 'employees.loans_dialog.next_deduction' | t }}</div>
              </div>
            </p-card>
          </div>

          <!-- Skeleton para resumen -->
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6" *ngIf="cargandoResumenPrestamos()">
            <p-card><au-skeleton height="4rem"></au-skeleton></p-card>
            <p-card><au-skeleton height="4rem"></au-skeleton></p-card>
            <p-card><au-skeleton height="4rem"></au-skeleton></p-card>
            <p-card><au-skeleton height="4rem"></au-skeleton></p-card>
          </div>

          <!-- Botón Nuevo Préstamo -->
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-semibold">{{ 'employees.loans_dialog.list_title' | t }}</h3>
            <button au-btn variant="primary" [icon]="'pi pi-plus'"
                    (click)="abrirNuevoPrestamo()">{{ 'employees.loans_dialog.new_loan_btn' | t }}</button>
          </div>

          <!-- Tabla de Préstamos -->
          <p-table [value]="prestamos()" [loading]="cargandoPrestamos()" responsiveLayout="scroll"
                   [paginator]="true" [rows]="10" [showCurrentPageReport]="true"
                   [currentPageReportTemplate]="('clients.showing_records' | t).replace('{first}', '{first}').replace('{last}', '{last}').replace('{total}', '{totalRecords}')">
            <ng-template pTemplate="header">
              <tr>
                <th>{{ 'employees.loans_dialog.table.request_date' | t }}</th>
                <th>{{ 'employees.loans_dialog.table.type' | t }}</th>
                <th>{{ 'employees.loans_dialog.table.amount' | t }}</th>
                <th>{{ 'employees.loans_dialog.table.installments' | t }}</th>
                <th>{{ 'employees.loans_dialog.table.monthly_payment' | t }}</th>
                <th>{{ 'employees.loans_dialog.table.remaining_balance' | t }}</th>
                <th>{{ 'employees.loans_dialog.table.status' | t }}</th>
                <th>{{ 'employees.loans_dialog.table.reason' | t }}</th>
              </tr>
            </ng-template>
            <ng-template pTemplate="body" let-loan>
              <tr>
                <td>{{loan.request_date | date:'dd/MM/yyyy'}}</td>
                <td>
                  <p-tag [value]="getLoanTypeLabel(loan.loan_type)" severity="info"></p-tag>
                </td>
                <td>
                  <span class="font-medium text-blue-600">
                    {{ loan.amount | appCurrency:'1.2-2' }}
                  </span>
                </td>
                <td>{{loan.installments}}</td>
                <td>
                  <span class="font-medium">
                    {{ loan.monthly_payment | appCurrency:'1.2-2' }}
                  </span>
                </td>
                <td>
                  <span class="font-bold" [class]="loan.remaining_balance > 0 ? 'text-orange-600' : 'text-green-600'">
                    {{ loan.remaining_balance | appCurrency:'1.2-2' }}
                  </span>
                </td>
                <td>
                  <p-tag [value]="getLoanStatusLabel(loan.status)"
                         [severity]="getLoanStatusSeverity(loan.status)"></p-tag>
                </td>
                <td>{{loan.reason || 'N/A'}}</td>
              </tr>
            </ng-template>
            <ng-template pTemplate="emptymessage">
              <tr>
                <td colspan="8" class="text-center py-8">
                  <div class="text-surface-500 dark:text-surface-400">
                    <i class="pi pi-info-circle text-3xl mb-2"></i>
                    <div>{{ 'employees.loans_dialog.empty' | t }}</div>
                  </div>
                </td>
              </tr>
            </ng-template>
          </p-table>
        </div>
      </p-dialog>

      <!-- Diálogo Nuevo Préstamo -->
      <p-dialog [header]="('employees.new_loan_dialog.title' | t) + ' - ' + (empleadoDetalle?.user?.full_name || '')"
                [(visible)]="mostrarNuevoPrestamo" [modal]="true" [style]="{ width: '92vw', maxWidth: '560px' }"
                [breakpoints]="{'960px':'75vw','640px':'100vw'}"
                styleClass="shadow-2xl"
                [closable]="!guardandoPrestamo()" [closeOnEscape]="!guardandoPrestamo()">
        <div [formGroup]="formularioPrestamo" class="grid gap-4">
          <div class="rounded-2xl bg-surface-950 p-4 text-white">
            <div class="text-[11px] uppercase tracking-[0.24em] text-surface-400">{{ 'employees.new_loan_dialog.finance' | t }}</div>
            <div class="mt-2 text-xl font-black">{{ 'employees.new_loan_dialog.title' | t }}</div>
            <div class="mt-2 text-sm text-surface-300">{{ 'employees.new_loan_dialog.subtitle' | t }}</div>
          </div>
          <div>
            <label class="block font-medium mb-1">{{ 'employees.new_loan_dialog.loan_type' | t }}</label>
            <p-select formControlName="loan_type" [options]="loanTypeOptions()" appendTo="body"
                        optionLabel="label" optionValue="value" class="w-full"
                        [placeholder]="'clients.form_gender_placeholder' | t"></p-select>
          </div>

          <div>
            <label class="block font-medium mb-1">{{ ('employees.new_loan_dialog.amount' | t).replace('{currency}', currencySymbol()) }}</label>
            <p-inputNumber formControlName="amount" mode="currency" [currency]="currencyCode()"
                           [locale]="currencyLocale()" class="w-full" [min]="100" [max]="50000"></p-inputNumber>
          </div>

          <div>
            <label class="block font-medium mb-1">{{ 'employees.new_loan_dialog.installments' | t }}</label>
            <p-inputNumber formControlName="installments" class="w-full"
                           [min]="1" [max]="24" [showButtons]="true"></p-inputNumber>
          </div>

          <div>
            <label class="block font-medium mb-1">{{ 'employees.new_loan_dialog.reason' | t }}</label>
            <input pInputText formControlName="reason" class="w-full"
                   [placeholder]="'employees.new_loan_dialog.reason' | t">
          </div>

          <!-- Resumen del préstamo -->
          <div class="rounded bg-surface-50 p-3 dark:bg-surface-800/70" *ngIf="formularioPrestamo.get('amount')?.value && formularioPrestamo.get('installments')?.value">
            <h4 class="font-medium mb-2">{{ 'employees.new_loan_dialog.summary.title' | t }}</h4>
            <div class="text-sm space-y-1">
              <div class="flex justify-between">
                <span>{{ 'employees.new_loan_dialog.summary.amount' | t }}</span>
                <span class="font-medium">{{ formularioPrestamo.get('amount')?.value | appCurrency:'1.2-2' }}</span>
              </div>
              <div class="flex justify-between">
                <span>{{ 'employees.new_loan_dialog.summary.installments' | t }}</span>
                <span class="font-medium">{{formularioPrestamo.get('installments')?.value}}</span>
              </div>
              <div class="flex justify-between border-t pt-1">
                <span>{{ 'employees.new_loan_dialog.summary.payment' | t }}</span>
                <span class="font-bold text-green-600">
                  {{ calcularPagoMensual() | appCurrency:'1.2-2' }}
                </span>
              </div>
            </div>
          </div>

          <div class="flex justify-end gap-2 mt-4">
            <button au-btn variant="ghost"
                    (click)="cerrarNuevoPrestamo()" [disabled]="guardandoPrestamo()">{{ 'common.cancel' | t }}</button>
            <button au-btn variant="primary" [icon]="'pi pi-check'"
                    [loading]="guardandoPrestamo()" [disabled]="formularioPrestamo.invalid"
                    (click)="crearPrestamo()">{{ 'employees.new_loan_dialog.create_btn' | t }}</button>
          </div>
        </div>
      </p-dialog>

      <!-- Diálogo de Historial de Pagos -->
      <p-dialog [header]="('employees.payment_history_dialog.title' | t) + ' - ' + (empleadoDetalle?.user?.full_name || '')"
                [(visible)]="mostrarHistorial" [modal]="true" [style]="{width: '90vw', maxWidth: '1200px'}"
                [breakpoints]="{'960px':'75vw','640px':'100vw'}"
                styleClass="shadow-2xl"
                [closable]="true">
        <div class="p-4" *ngIf="empleadoDetalle">

          <!-- Resumen de Estadísticas -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6" *ngIf="!cargandoStats()">
            <p-card>
              <div class="text-center">
                <div class="text-2xl font-bold text-surface-700 dark:text-surface-300">{{paymentStats()?.all_time?.total_payments || 0}}</div>
                <div class="text-sm text-surface-600 dark:text-surface-400">{{ 'employees.payment_history_dialog.total_payments' | t }}</div>
              </div>
            </p-card>
            <p-card>
              <div class="text-center">
                <div class="text-2xl font-bold text-[var(--brand)]">
                  {{ (paymentStats()?.all_time?.total_net || 0) | appCurrency:'1.2-2' }}
                </div>
                <div class="text-sm text-surface-600 dark:text-surface-400">{{ 'employees.payment_history_dialog.total_paid' | t }}</div>
              </div>
            </p-card>
            <p-card>
              <div class="text-center">
                <div class="text-2xl font-bold text-[var(--brand)]">
                  {{ (paymentStats()?.all_time?.average_payment || 0) | appCurrency:'1.2-2' }}
                </div>
                <div class="text-sm text-surface-600 dark:text-surface-400">{{ 'employees.payment_history_dialog.average_payment' | t }}</div>
              </div>
            </p-card>
          </div>

          <!-- Skeleton para estadísticas -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6" *ngIf="cargandoStats()">
            <p-card>
              <au-skeleton height="4rem"></au-skeleton>
            </p-card>
            <p-card>
              <au-skeleton height="4rem"></au-skeleton>
            </p-card>
            <p-card>
              <au-skeleton height="4rem"></au-skeleton>
            </p-card>
          </div>

          <!-- Último Pago -->
          <div class="mb-4" *ngIf="paymentStats()?.last_payment">
            <p-card>
              <div class="flex justify-between items-center">
                <div>
                  <div class="font-semibold text-surface-700 dark:text-surface-200">{{ 'employees.payment_history_dialog.last_payment' | t }}</div>
                  <div class="text-sm text-surface-500 dark:text-surface-400">
                    {{paymentStats()?.last_payment?.date | date:'dd/MM/yyyy'}} -
                    {{paymentStats()?.last_payment?.method}}
                  </div>
                </div>
                <div class="text-xl font-bold text-green-600">
                  {{ paymentStats()?.last_payment?.amount | appCurrency:'1.2-2' }}
                </div>
              </div>
            </p-card>
          </div>

          <!-- Tabla de Historial -->
          <div class="mt-4">
            <h3 class="text-lg font-semibold mb-4">{{ 'pos.historial' | t }}</h3>
            <p-table [value]="historialPagos()" [loading]="cargandoHistorial()" responsiveLayout="scroll"
                     [paginator]="true" [rows]="10" [showCurrentPageReport]="true"
                     [currentPageReportTemplate]="('clients.showing_records' | t).replace('{first}', '{first}').replace('{last}', '{last}').replace('{total}', '{totalRecords}')">
              <ng-template pTemplate="header">
                <tr>
                  <th>{{ 'appointments.date' | t }}</th>
                  <th>{{ 'employees.receipt_dialog.period' | t }}</th>
                  <th>{{ 'employees.receipt_dialog.gross_amount' | t }}</th>
                  <th>{{ 'employees.receipt_dialog.deductions' | t }}</th>
                  <th>{{ 'employees.receipt_dialog.net_amount' | t }}</th>
                  <th>{{ 'pos.payment_method' | t }}</th>
                  <th>{{ 'employees.receipt_dialog.reference' | t }}</th>
                  <th>{{ 'employees.table.actions' | t }}</th>
                </tr>
              </ng-template>
              <ng-template pTemplate="body" let-payment>
                <tr>
                  <td>{{payment.paid_at | date:'dd/MM/yyyy HH:mm'}}</td>
                  <td>
                    <span class="font-medium">{{payment.period_display}}</span>
                  </td>
                  <td>
                    <span class="font-medium text-blue-600">
                      {{ payment.gross_amount | appCurrency:'1.2-2' }}
                    </span>
                  </td>
                  <td>
                    <span class="text-red-600">
                      {{ payment.total_deductions | appCurrency:'1.2-2' }}
                    </span>
                  </td>
                  <td>
                    <span class="font-bold text-green-600">
                      {{ payment.net_amount | appCurrency:'1.2-2' }}
                    </span>
                  </td>
                  <td>
                    <p-tag [value]="payment.payment_method" severity="info"></p-tag>
                  </td>
                  <td>{{payment.payment_reference || 'N/A'}}</td>
                  <td>
                    <button pButton icon="pi pi-file-pdf" class="p-button-text p-button-sm"
                            (click)="verReciboPago(payment)" [pTooltip]="'employees.receipt_dialog.title' | t"></button>
                  </td>
                </tr>
              </ng-template>
              <ng-template pTemplate="emptymessage">
                <tr>
                  <td colspan="8" class="text-center py-8">
                    <div class="text-surface-500 dark:text-surface-400">
                      <i class="pi pi-info-circle text-3xl mb-2"></i>
                      <div>{{ 'employees.payment_history_dialog.empty' | t }}</div>
                    </div>
                  </td>
                </tr>
              </ng-template>
            </p-table>
          </div>
        </div>
      </p-dialog>

      <!-- Diálogo de Recibo de Pago -->
      <p-dialog [header]="'employees.receipt_dialog.title' | t" [(visible)]="mostrarRecibo" [modal]="true"
                [style]="{ width: '95vw', maxWidth: '860px' }" [breakpoints]="{'960px':'75vw','640px':'100vw'}" [closable]="true" styleClass="shadow-2xl">
        <div class="recibo-container rounded-xl border border-surface-200 dark:border-surface-700 bg-white dark:bg-surface-900 text-surface-900 dark:text-surface-100 p-4" *ngIf="reciboActual()">
          <!-- Header del recibo -->
          <div class="text-center mb-6 border-b border-surface-200 dark:border-surface-700 pb-4">
            <h2 class="text-2xl font-bold text-surface-900 dark:text-surface-100">{{reciboActual()?.company?.name}}</h2>
            <p class="text-surface-600 dark:text-surface-300">{{reciboActual()?.company?.address}}</p>
            <p class="text-surface-600 dark:text-surface-300">{{reciboActual()?.company?.phone}}</p>
            <h3 class="text-xl font-semibold mt-4 text-[var(--brand)] dark:text-[var(--brand-400)]">{{ 'employees.receipt_dialog.subtitle' | t }}</h3>
          </div>

          <!-- Información del empleado y período -->
          <div class="grid grid-cols-2 gap-6 mb-6">
            <div>
              <h4 class="font-semibold text-surface-800 dark:text-surface-200 mb-2">{{ 'employees.receipt_dialog.employee' | t }}</h4>
              <p class="font-medium">{{reciboActual()?.employee?.name}}</p>
              <p class="text-sm text-surface-600 dark:text-surface-300">{{reciboActual()?.employee?.email}}</p>
            </div>
            <div>
              <h4 class="font-semibold text-surface-800 dark:text-surface-200 mb-2">{{ 'employees.receipt_dialog.period' | t }}</h4>
              <p class="font-medium">{{reciboActual()?.period?.display}}</p>
              <p class="text-sm text-surface-600 dark:text-surface-300">
                {{reciboActual()?.period?.start_date | date:'dd/MM/yyyy'}} -
                {{reciboActual()?.period?.end_date | date:'dd/MM/yyyy'}}
              </p>
            </div>
          </div>

          <!-- Detalle de montos -->
          <div class="border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-800 rounded-lg p-4 mb-6">
            <h4 class="font-semibold text-surface-800 dark:text-surface-200 mb-4">{{ 'employees.receipt_dialog.payment_detail' | t }}</h4>

            <div class="space-y-2">
              <div class="flex justify-between">
                <span>{{ 'employees.receipt_dialog.gross_amount' | t }}</span>
                <span class="font-medium">
                  {{ reciboActual()?.amounts?.gross_amount | appCurrency:'1.2-2' }}
                </span>
              </div>

              <div class="border-t pt-2">
                <p class="font-medium text-surface-700 dark:text-surface-200 mb-2">{{ 'employees.receipt_dialog.deductions' | t }}</p>
                <div class="ml-4 space-y-1 text-sm">
                  <div class="flex justify-between" *ngIf="reciboActual()?.amounts?.deductions?.afp && (reciboActual()?.amounts?.deductions?.afp ?? 0) > 0">
                    <span>AFP (2.87%):</span>
                    <span>-{{ reciboActual()?.amounts?.deductions?.afp | appCurrency:'1.2-2' }}</span>
                  </div>
                  <div class="flex justify-between" *ngIf="reciboActual()?.amounts?.deductions?.sfs && (reciboActual()?.amounts?.deductions?.sfs ?? 0) > 0">
                    <span>SFS (3.04%):</span>
                    <span>-{{ reciboActual()?.amounts?.deductions?.sfs | appCurrency:'1.2-2' }}</span>
                  </div>
                  <div class="flex justify-between" *ngIf="reciboActual()?.amounts?.deductions?.isr && (reciboActual()?.amounts?.deductions?.isr ?? 0) > 0">
                    <span>ISR:</span>
                    <span>-{{ reciboActual()?.amounts?.deductions?.isr | appCurrency:'1.2-2' }}</span>
                  </div>
                  <div class="flex justify-between" *ngIf="reciboActual()?.amounts?.deductions?.loans && (reciboActual()?.amounts?.deductions?.loans ?? 0) > 0">
                    <span>Préstamos:</span>
                    <span>-{{ reciboActual()?.amounts?.deductions?.loans | appCurrency:'1.2-2' }}</span>
                  </div>
                </div>
                <div class="flex justify-between font-medium border-t pt-1 mt-2">
                  <span>{{ 'employees.receipt_dialog.total_deductions' | t }}</span>
                  <span>-{{ reciboActual()?.amounts?.deductions?.total | appCurrency:'1.2-2' }}</span>
                </div>
              </div>

              <div class="border-t pt-2 flex justify-between text-lg font-bold text-green-700 dark:text-emerald-400">
                <span>{{ 'employees.receipt_dialog.net_amount' | t }}</span>
                <span>{{ reciboActual()?.amounts?.net_amount | appCurrency:'1.2-2' }}</span>
              </div>
            </div>
          </div>

          <!-- Información del pago -->
          <div class="grid grid-cols-2 gap-6 mb-6">
            <div>
              <h4 class="font-semibold text-surface-800 dark:text-surface-200 mb-2">{{ 'employees.receipt_dialog.payment_info' | t }}</h4>
              <p><strong>{{ 'employees.receipt_dialog.method' | t }}</strong> {{reciboActual()?.payment_info?.method}}</p>
              <p><strong>{{ 'employees.receipt_dialog.reference' | t }}</strong> {{reciboActual()?.payment_info?.reference}}</p>
            </div>
            <div>
              <h4 class="font-semibold text-surface-800 dark:text-surface-200 mb-2">{{ 'employees.receipt_dialog.date_responsible' | t }}</h4>
              <p><strong>{{ 'employees.receipt_dialog.date' | t }}</strong> {{reciboActual()?.payment_info?.paid_at | date:'dd/MM/yyyy HH:mm'}}</p>
              <p><strong>{{ 'employees.receipt_dialog.paid_by' | t }}</strong> {{reciboActual()?.payment_info?.paid_by}}</p>
            </div>
          </div>

          <!-- Footer -->
          <div class="text-center text-sm text-surface-600 dark:text-surface-300 border-t border-surface-200 dark:border-surface-700 pt-4">
            <p>{{ ('employees.receipt_dialog.receipt_id' | t).replace('{id}', reciboActual()?.payment_id || '') }}</p>
            <p>{{ 'employees.receipt_dialog.comprobante_hint' | t }}</p>
          </div>
        </div>

        <div class="flex justify-end gap-2 mt-4">
          <button au-btn variant="secondary" [icon]="'pi pi-print'"
                  (click)="imprimirRecibo()">{{ 'pos.imprimir' | t }}</button>
          <button au-btn variant="primary" (click)="cerrarRecibo()">{{ 'pos.cerrar' | t }}</button>
        </div>
      </p-dialog>
    </div>

    <p-confirmDialog></p-confirmDialog>
    <p-toast></p-toast>
  `
})
export class EmployeesManagement implements OnInit {
  private settingsService = inject(SettingsService);
  private employeeService = inject(EmployeeService);
  private serviceService = inject(ServiceService);
  private authService = inject(AuthService);
  private router = inject(Router);
  protected planAccessService = inject(PlanAccessService);
  private messageService = inject(MessageService);
  private confirmationService = inject(ConfirmationService);
  private fb = inject(FormBuilder);
  private destroyRef = inject(DestroyRef);
  protected localeService = inject(LocaleService);
  protected branchService = inject(BranchService);

  t(key: string): string {
    return this.localeService.t(key as any);
  }

  // ===== ROSTER HELPERS =====
  getActiveEmployees(): EmployeeWithUserDto[] {
    return this.empleados().filter(e => e.is_active);
  }

  getInitials(fullName: string): string {
    if (!fullName) return '?';
    const parts = fullName.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
    return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
  }

  getFirstName(fullName: string): string {
    if (!fullName) return '';
    return fullName.trim().split(/\s+/)[0];
  }

  getAvatarColor(fullName: string): string {
    const colors = [
      'var(--brand)', '#0e9f6e', '#d61f69', '#6c2bd9',
      '#057a55', '#c27803', '#1c64f2', '#9061f9'
    ];
    let hash = 0;
    for (let i = 0; i < (fullName || '').length; i++) {
      hash = fullName.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
  }
  // ===========================

  empleados = signal<EmployeeWithUserDto[]>([]);
  usuariosActivos = signal(0);
  cargando = signal(false);
  guardando = signal(false);
  mostrarDialogo = false;
  mostrarDialogoLimitePlan = false;
  tituloDialogoLimitePlan = 'Límite del plan alcanzado';
  mensajeDialogoLimitePlan = '';
  recomendacionUpgradePlan: ReturnType<PlanAccessService['getUpgradeRecommendation']> = null;
  empleadoSeleccionado: EmployeeWithUserDto | null = null;
  fechaMaxima = new Date();

  // Nuevas propiedades para configuración de nómina
  mostrarConfigNomina = false;
  empleadoDetalle: EmployeeWithUserDto | null = null;
  guardandoNomina = signal(false);

  // Propiedades para historial de pagos
  mostrarHistorial = false;
  cargandoHistorial = signal(false);
  cargandoStats = signal(false);
  historialPagos = signal<PaymentDto[]>([]);
  paymentStats = signal<PaymentStatsDto | null>(null);
  mostrarRecibo = false;
  reciboActual = signal<PaymentReceiptDto | null>(null);

  // Propiedades para préstamos
  mostrarPrestamos = false;
  cargandoPrestamos = signal(false);
  cargandoResumenPrestamos = signal(false);
  prestamos = signal<LoanDto[]>([]);
  resumenPrestamos = signal<LoanSummaryDto | null>(null);
  mostrarNuevoPrestamo = false;
  guardandoPrestamo = signal(false);
  currencyCode = computed(() => this.settingsService.settings().currency || 'DOP');
  currencyLocale = computed(() => this.settingsService.getCurrencyLocale());
  currencySymbol = computed(() => this.settingsService.getCurrencySymbol() || 'RD$');

  // Sorting, pagination & selection signals
  sortField = signal<string>('user.full_name');
  sortOrder = signal<'asc' | 'desc'>('asc');
  currentPage = signal(0);
  pageSize = signal(10);
  globalFilter = signal('');
  selectedEmployeesSet = signal<Set<number>>(new Set());
  showInactive = signal(false);

  sortedEmployees = computed(() => {
    const all = this.empleados();
    const field = this.sortField();
    const order = this.sortOrder();
    const filter = this.globalFilter().toLowerCase();
    const activeBranchId = this.branchService.activeBranchId();
    const showInactive = this.showInactive();
    let filtered = all;
    if (!showInactive) {
      filtered = filtered.filter(e => e.is_active);
    }
    if (activeBranchId && this._canAccessMultiLocation) {
      filtered = filtered.filter(e => e.branch === activeBranchId);
    }
    if (filter) {
      filtered = filtered.filter(e =>
        (e.user.full_name?.toLowerCase() || '').includes(filter) ||
        (e.user.email?.toLowerCase() || '').includes(filter) ||
        (this.getRoleDisplayName(e.user.role, e.user.business_role, e.user.business_role_display)?.toLowerCase() || '').includes(filter)
      );
    }
    const sorted = [...filtered].sort((a, b) => {
      let aVal: string, bVal: string;
      switch (field) {
        case 'user.full_name':
          aVal = (a.user.full_name || '').toLowerCase();
          bVal = (b.user.full_name || '').toLowerCase();
          break;
        case 'user.email':
          aVal = (a.user.email || '').toLowerCase();
          bVal = (b.user.email || '').toLowerCase();
          break;
        case 'role':
          aVal = (this.getRoleDisplayName(a.user.role, a.user.business_role, a.user.business_role_display) || '').toLowerCase();
          bVal = (this.getRoleDisplayName(b.user.role, b.user.business_role, b.user.business_role_display) || '').toLowerCase();
          break;
        case 'is_active':
          aVal = String(a.is_active ?? '');
          bVal = String(b.is_active ?? '');
          break;
        default:
          aVal = String((a as any)[field] ?? '');
          bVal = String((b as any)[field] ?? '');
      }
      return order === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });
    const start = this.currentPage() * this.pageSize();
    return sorted.slice(start, start + this.pageSize());
  });

  totalRecords = computed(() => {
    const all = this.empleados();
    const filter = this.globalFilter().toLowerCase();
    const activeBranchId = this.branchService.activeBranchId();
    const showInactive = this.showInactive();
    let filtered = all;
    if (!showInactive) {
      filtered = filtered.filter(e => e.is_active);
    }
    if (activeBranchId && this._canAccessMultiLocation) {
      filtered = filtered.filter(e => e.branch === activeBranchId);
    }
    if (!filter) return filtered.length;
    return filtered.filter(e =>
      (e.user.full_name?.toLowerCase() || '').includes(filter) ||
      (e.user.email?.toLowerCase() || '').includes(filter) ||
      (this.getRoleDisplayName(e.user.role, e.user.business_role, e.user.business_role_display)?.toLowerCase() || '').includes(filter)
    ).length;
  });

  totalPages = computed(() => Math.max(1, Math.ceil(this.totalRecords() / this.pageSize())));
  firstRecord = computed(() => this.currentPage() * this.pageSize());
  lastRecord = computed(() => Math.min(this.firstRecord() + this.pageSize(), this.totalRecords()));

  allSelected = computed(() => {
    const displayed = this.sortedEmployees();
    const set = this.selectedEmployeesSet();
    return displayed.length > 0 && displayed.every(e => e.id && set.has(e.id));
  });

  get selectedEmployees(): EmployeeWithUserDto[] {
    const set = this.selectedEmployeesSet();
    return this.empleados().filter(e => e.id && set.has(e.id));
  }

  getActiveEmployeesCount(): number {
    return this.empleados().filter((emp) => emp.is_active).length;
  }

  getInactiveEmployeesCount(): number {
    return this.empleados().filter((emp) => !emp.is_active).length;
  }

  getServiceAssignableCount(): number {
    return this.empleados().filter((emp) => this.isServiceAssignableRole(emp.user.role, emp.user.business_role)).length;
  }

  getShowingRecordsText(): string {
    return this.t('clients.showing_records')
      .replace('{first}', String(this.firstRecord() + 1))
      .replace('{last}', String(this.lastRecord()))
      .replace('{total}', String(this.totalRecords()));
  }

  getPageOfText(): string {
    return this.t('common.page_of')
      .replace('{page}', String(this.currentPage() + 1))
      .replace('{total}', String(this.totalPages()));
  }

  private syncActiveUsersCountFromEmployees(employees: EmployeeWithUserDto[]): void {
    this.usuariosActivos.set(employees.filter((emp) => emp.is_active).length);
  }

  getEmployeesNarrative(): string {
    const total = this.empleados().length;
    const active = this.getActiveEmployeesCount();
    const assignable = this.getServiceAssignableCount();

    if (!total) {
      return this.t('employees.narrative_empty');
    }

    return this.t('employees.narrative_active')
      .replace('{active}', String(active))
      .replace('{total}', String(total))
      .replace('{assignable}', String(assignable));
  }

  getSelectedEmployeeDisplayName(): string {
    return this.empleadoDetalle?.user?.full_name || this.t('employees.roles.professional');
  }

  // ── Sorting, pagination & selection methods ──

  toggleSort(field: string) {
    if (this.sortField() === field) {
      this.sortOrder.set(this.sortOrder() === 'asc' ? 'desc' : 'asc');
    } else {
      this.sortField.set(field);
      this.sortOrder.set('asc');
    }
    this.currentPage.set(0);
  }

  isSelected(emp: EmployeeWithUserDto): boolean {
    return emp.id ? this.selectedEmployeesSet().has(emp.id) : false;
  }

  toggleSelection(emp: EmployeeWithUserDto) {
    if (!emp.id) return;
    const set = new Set(this.selectedEmployeesSet());
    if (set.has(emp.id)) {
      set.delete(emp.id);
    } else {
      set.add(emp.id);
    }
    this.selectedEmployeesSet.set(set);
  }

  toggleSelectAll(event: Event) {
    const checked = (event.target as HTMLInputElement).checked;
    const set = new Set(this.selectedEmployeesSet());
    if (checked) {
      this.sortedEmployees().forEach(e => { if (e.id) set.add(e.id); });
    } else {
      this.sortedEmployees().forEach(e => { if (e.id) set.delete(e.id); });
    }
    this.selectedEmployeesSet.set(set);
  }

  onGlobalFilter(event: Event) {
    this.currentPage.set(0);
    this.globalFilter.set((event.target as HTMLInputElement).value);
  }

  changePageSize(event: Event) {
    this.pageSize.set(Number((event.target as HTMLSelectElement).value));
    this.currentPage.set(0);
  }

  setPageSize(size: number) {
    this.pageSize.set(size);
    this.currentPage.set(0);
  }

  setPage(page: number) {
    if (page >= 0 && page < this.totalPages()) {
      this.currentPage.set(page);
    }
  }

  prevPage() {
    if (this.currentPage() > 0) this.currentPage.update(p => p - 1);
  }

  nextPage() {
    if (this.currentPage() < this.totalPages() - 1) this.currentPage.update(p => p + 1);
  }

  getRoleBadgeClass(emp: EmployeeWithUserDto): string {
    const role = this.getRoleDisplayName(emp.user.role, emp.user.business_role, emp.user.business_role_display);
    const classes: { [key: string]: string } = {
      'Profesional': 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
      'Recepcion / Caja': 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
      'Gerente': 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
      'Propietario': 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    };
    return classes[role] || 'bg-surface-100 text-surface-700 dark:bg-surface-800 dark:text-surface-300';
  }

  rolesOptions = computed(() => [
    { label: this.t('employees.roles.owner'), value: 'owner' },
    { label: this.t('employees.roles.manager'), value: 'manager' },
    { label: this.t('employees.roles.frontdesk_cashier'), value: 'frontdesk_cashier' },
    { label: this.t('employees.roles.professional'), value: 'professional' }
  ]);

  PROFESSION_OPTIONS = EMPLOYEE_CONFIG.PROFESSIONS;

  salaryTypeOptions = computed(() => [
    { label: this.t('payroll.fixed'), value: 'fixed' },
    { label: this.t('payroll.commission'), value: 'commission' },
    { label: this.t('payroll.mixed'), value: 'mixed' }
  ]);

  frequencyOptions = computed(() => [
    { label: this.t('payroll.biweekly'), value: 'biweekly' },
    { label: this.t('payroll.monthly'), value: 'monthly' },
    { label: this.t('payroll.weekly'), value: 'weekly' }
  ]);

  loanTypeOptions = computed(() => [
    { label: this.t('employees.loan_type.advance'), value: 'advance' },
    { label: this.t('employees.loan_type.personal'), value: 'personal_loan' },
    { label: this.t('employees.loan_type.emergency'), value: 'emergency' }
  ]);

  formulario: FormGroup = this.fb.group({
    full_name: ['', [Validators.required]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    business_role: ['professional', [Validators.required]],
    profession: [''],
    phone: [''],
    hire_date: [new Date()],
    service_ids: [[]],
    is_active: [true],
    branch: [null as number | null]
  });

  @ViewChild('actionMenu') actionMenu!: Menu;
  actionMenuItems: MenuItem[] = [];
  selectedEmp: EmployeeWithUserDto | null = null;

  openActionMenu(event: Event, emp: EmployeeWithUserDto) {
    this.selectedEmp = emp;
    this.actionMenuItems = [
      {
        label: this.t('employees.payroll_dialog.title'),
        icon: 'pi pi-wallet',
        command: () => this.verConfiguracionNomina(emp)
      },
      {
        label: this.t('employees.loans_dialog.title'),
        icon: 'pi pi-credit-card',
        command: () => this.verPrestamos(emp)
      },
      {
        label: this.t('employees.payment_history_dialog.title'),
        icon: 'pi pi-history',
        command: () => this.verHistorialPagos(emp)
      },
      { separator: true },
      {
        label: this.t('common.delete'),
        icon: 'pi pi-trash',
        command: () => this.confirmarEliminar(emp)
      }
    ];
    this.actionMenu.toggle(event);
  }

  _canAccessMultiLocation = false;
  canAccessMultiLocation(): boolean {
    return this._canAccessMultiLocation;
  }

  branchOptionsForForm = computed(() => {
    return this.branchService.branches().map(b => ({ label: b.name, value: b.id }));
  });

  getBranchName(branchId: number | null | undefined): string {
    if (!branchId) return '-';
    const branch = this.branchService.branches().find(b => b.id === branchId);
    return branch ? branch.name : '-';
  }

  servicesOptions: Array<{ label: string; value: number }> = [];

  formularioNomina: FormGroup = this.fb.group({
    salary_type: ['commission'],
    payment_frequency: ['biweekly'],
    commission_percentage: [40],
    commission_payment_mode: ['PER_PERIOD'],
    contractual_monthly_salary: [0],
    apply_afp: [false],
    apply_sfs: [false],
    apply_isr: [false]
  });

  formularioPrestamo: FormGroup = this.fb.group({
    loan_type: ['', [Validators.required]],
    amount: [null, [Validators.required, Validators.min(100)]],
    installments: [null, [Validators.required, Validators.min(1), Validators.max(24)]],
    reason: ['']
  });

  // Adaptador: Backend → Frontend DTO
  private mapBackendToEmployeeWithUser(empleadoBackend: any, usuarioBackend: any): EmployeeWithUserDto {
    return {
      id: empleadoBackend?.id || 0,
      user_id: usuarioBackend.id,
      user: {
        id: usuarioBackend.id,
        email: usuarioBackend.email,
        full_name: usuarioBackend.full_name,
        role: usuarioBackend.role,
        business_role: usuarioBackend.business_role,
        business_role_display: usuarioBackend.business_role_display,
        is_active: usuarioBackend.is_active,
        tenant: usuarioBackend.tenant,
        created_at: usuarioBackend.created_at,
        updated_at: usuarioBackend.updated_at
      },
      profession: empleadoBackend?.profession || '',
      profession_display: empleadoBackend?.profession_display || '',
      phone: empleadoBackend?.phone || '',
      hire_date: empleadoBackend?.hire_date || '',
      branch: empleadoBackend?.branch || null,
      is_active: empleadoBackend?.is_active ?? true,
      service_ids: empleadoBackend?.service_ids || [],
      services_count: empleadoBackend?.services_count || 0,
      created_at: empleadoBackend?.created_at || '',
      display_name: `${usuarioBackend.full_name || usuarioBackend.email || 'Sin nombre'} (${this.getRoleDisplayName(usuarioBackend.role, usuarioBackend.business_role, usuarioBackend.business_role_display)})`
    };
  }

  ngOnInit() {
    this._canAccessMultiLocation = this.planAccessService.canAccessFeature('multi_location');
    this.cargarDatos();
    this.cargarServicios();
    this.cargarConfiguracionDefecto();
    if (this._canAccessMultiLocation) {
      this.branchService.loadBranches().subscribe();
    }
    this.formularioNomina.get('salary_type')?.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((salaryType) => {
      this.syncPayrollFieldsByType(salaryType);
    });
    this.syncPayrollFieldsByType(this.formularioNomina.get('salary_type')?.value);
  }

  async cargarServicios() {
    try {
      const response = await firstValueFrom(this.serviceService.getActiveServices());
      const services = (response as any)?.results || response || [];
      this.servicesOptions = services.map((service: any) => ({
        label: `${service.name} - ${this.formatearMoneda(service.price)}`,
        value: service.id
      }));
    } catch {
      this.servicesOptions = [];
    }
  }

  formatearMoneda(valor: number | string | null | undefined): string {
    const amount = Number(valor) || 0;
    return new Intl.NumberFormat(this.currencyLocale(), {
      style: 'currency',
      currency: this.currencyCode()
    }).format(amount);
  }

  async cargarConfiguracionDefecto() {
    try {
      const config = await firstValueFrom(this.settingsService.getBarbershopSettings());
      this.formularioNomina.patchValue({
        commission_percentage: (config as any)?.default_commission_rate || 40,
        contractual_monthly_salary: (config as any)?.default_fixed_salary || 0
      });
    } catch {}
  }

  async cargarDatos() {
    this.cargando.set(true);
    try {
      const params: any = {};
      const activeBranchId = this.branchService.activeBranchId();
      if (activeBranchId) {
        params.branch_id = activeBranchId;
      }
      // Usar solo el endpoint de empleados que ya incluye datos del usuario
      const empleadosRes = await firstValueFrom(this.employeeService.getEmployees(params));
      const empleados = (empleadosRes as any)?.results || [];

      // Mapear directamente desde la respuesta de empleados
      const empleadosFusionados: EmployeeWithUserDto[] = empleados.map((emp: any) => {
        return {
          id: emp.id,
          user_id: emp.user?.id ?? 0,
          user: {
            id: emp.user?.id ?? 0,
            email: emp.user.email,
            full_name: emp.user.full_name,
            role: emp.user.role,
            business_role: emp.user.business_role,
            business_role_display: emp.user.business_role_display,
            is_active: emp.is_active,
            tenant: 0,
            created_at: emp.created_at,
            updated_at: emp.updated_at
          },
          profession: emp.profession || '',
          profession_display: emp.profession_display || '',
          phone: emp.phone || '',
          hire_date: emp.hire_date || '',
          branch: emp.branch || null,
          is_active: emp.is_active,
          service_ids: emp.service_ids || [],
          services_count: emp.services_count || 0,
          created_at: emp.created_at,
          display_name: `${emp.user.full_name || emp.user.email || 'Sin nombre'} (${this.getRoleDisplayName(emp.user.role, emp.user.business_role, emp.user.business_role_display)})`
        };
      });

      this.empleados.set(empleadosFusionados);

      this.syncActiveUsersCountFromEmployees(empleadosFusionados);
    } catch (error) {
      if (!environment.production) {
        
      }
      let detail = this.t('employees.error.load');
      const backendError = (error as any)?.error;
      if (typeof backendError?.detail === 'string' && backendError.detail.trim()) {
        detail = backendError.detail;
      } else if (typeof backendError?.error === 'string' && backendError.error.trim()) {
        detail = backendError.error;
      } else if ((error as any)?.status === 403) {
        detail = this.t('employees.error.no_permission');
      }
      this.messageService.add({
        severity: 'error',
        summary: 'Error',
        detail
      });
    } finally {
      this.cargando.set(false);
    }
  }

  async abrirDialogo() {
    await this.sincronizarEmpleadosAntesDeCrear();

      const limitStatus = this.planAccessService.getEmployeeLimitStatus(this.usuariosActivos());
      if (limitStatus.reached) {
        this.abrirDialogoLimitePlan(
          this.t('employees.error.no_permission_save'),
          this.planAccessService.getEmployeeLimitMessage(limitStatus)
      );
      return;
    }

    this.empleadoSeleccionado = null;
    this.formulario.reset({
      full_name: '',
      email: '',
      password: '',
      business_role: 'professional',
      profession: '',
      phone: '',
      hire_date: new Date(),
      service_ids: [],
      is_active: true,
      branch: this.branchService.activeBranchId()
    });
    this.formulario.get('password')?.setValidators([Validators.required, Validators.minLength(8)]);
    this.mostrarDialogo = true;
  }

  editarEmpleado(emp: EmployeeWithUserDto) {
    this.empleadoSeleccionado = emp;
    this.formulario.patchValue({
      full_name: emp.user.full_name,
      email: emp.user.email,
      business_role: resolveBusinessRole(emp.user.role, emp.user.business_role) || 'professional',
      profession: emp.profession,
      phone: emp.phone,
      hire_date: emp.hire_date ? new Date(emp.hire_date) : new Date(),
      service_ids: emp.service_ids || [],
      is_active: emp.is_active,
      branch: emp.branch || null
    });
    this.formulario.get('password')?.clearValidators();
    this.formulario.get('password')?.updateValueAndValidity();
    this.mostrarDialogo = true;
  }

  async guardarEmpleado() {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    if (!this.empleadoSeleccionado) {
      const employeeLimitStatus = this.planAccessService.getEmployeeLimitStatus(this.usuariosActivos());
      if (employeeLimitStatus.reached) {
        const message = this.planAccessService.getEmployeeLimitMessage(employeeLimitStatus);
        this.messageService.add({
          severity: 'error',
          summary: 'Error',
          detail: message
        });
        this.abrirDialogoLimitePlan('No se puede crear el empleado', message);
        return;
      }
    }

    const formData = this.formulario.value;

    // Validar email duplicado en el mismo tenant
    const emailNormalized = formData.email?.trim().toLowerCase();
    if (emailNormalized) {
      const emailExists = this.empleados().some(emp => {
        if (this.empleadoSeleccionado && emp.user_id === this.empleadoSeleccionado.user_id) return false;
        return emp.user?.email?.toLowerCase() === emailNormalized;
      });
      if (emailExists) {
        this.messageService.add({
          severity: 'error',
          summary: 'Error',
          detail: 'Ya existe un empleado con este email en este negocio.'
        });
        this.guardando.set(false);
        return;
      }
    }
    const serviceIds = this.isServiceAssignableRole(undefined, formData.business_role) ? (formData.service_ids || []) : [];

    try {
      if (this.empleadoSeleccionado) {
        // Actualizar usuario
        await firstValueFrom(this.authService.updateUser(this.empleadoSeleccionado.user_id, {
          full_name: formData.full_name,
          email: formData.email,
          business_role: formData.business_role,
          is_active: formData.is_active
        } as any));

        // Si tiene registro Employee (id > 0), actualizar; si no, omitir creación
        if (this.empleadoSeleccionado.id > 0) {
          const updateData = {
            profession: formData.profession || undefined,
            phone: formData.phone || undefined,
            hire_date: formData.hire_date ? new Date(formData.hire_date).toISOString().split('T')[0] : undefined,
            is_active: formData.is_active,
            branch: formData.branch || null
          };

          
          // Usar PATCH en lugar de PUT para evitar problemas con campos no permitidos
          await firstValueFrom(this.employeeService.patchEmployee(this.empleadoSeleccionado.id, updateData));
          await firstValueFrom(this.employeeService.assignServices(this.empleadoSeleccionado.id, serviceIds));
        }
        // NOTA: No se puede crear registro Employee vía POST /api/employees/ (endpoint deshabilitado)
        // Los datos de empleado se manejan solo a través del usuario

        this.messageService.add({
          severity: 'success',
          summary: this.t('common.success'),
          detail: this.t('employees.toast.save_success')
        });
      } else {
        // Crear usuario
        const newUser = await firstValueFrom(this.authService.createUser({
          email: formData.email,
          full_name: formData.full_name,
          password: formData.password,
          business_role: formData.business_role,
          tenant: this.authService.getTenantId()
        } as any));
        
        const nuevoEmpleado = await this.esperarEmpleadoPorUsuario((newUser as any).id);
        
        if (nuevoEmpleado && nuevoEmpleado.id > 0) {
          const updateData = {
            profession: formData.profession || undefined,
            phone: formData.phone || undefined,
            hire_date: formData.hire_date ? new Date(formData.hire_date).toISOString().split('T')[0] : undefined,
            is_active: formData.is_active,
            branch: formData.branch || null
          };
          await firstValueFrom(this.employeeService.patchEmployee(nuevoEmpleado.id, updateData));
          await firstValueFrom(this.employeeService.assignServices(nuevoEmpleado.id, serviceIds));
        }

        this.messageService.add({
          severity: 'success',
          summary: this.t('common.success'),
          detail: this.t('employees.toast.save_success')
        });
      }

      this.cerrarDialogo();
      await this.cargarDatos();
    } catch (error: any) {
      if (!environment.production) {
        console.debug('Error creando/actualizando empleado:', error);
      }

      const isUpdate = !!this.empleadoSeleccionado;
      let errorMessage = isUpdate
        ? this.t('employees.error.no_permission')
        : 'Error al guardar el empleado. Revisa los datos e intenta de nuevo.';
      const planLimitMessage = this.buildPlanLimitErrorMessage(error);
      const planLimitContext = this.getPlanLimitContext(error);

      // Detectar límite de usuarios
      if (planLimitMessage) {
        errorMessage = planLimitMessage;
      } else if (error?.error?.current !== undefined && error?.error?.limit !== undefined) {
        errorMessage = this.t('employees.error.limit_reached').replace('{current}', String(error.error.current)).replace('{limit}', String(error.error.limit));
      } else if (error?.error?.error && error.error.error.includes('User limit reached')) {
        errorMessage = this.t('employees.error.limit_reached').replace(' ({current}/{limit})', '');
      } else if (error?.error?.error && String(error.error.error).toLowerCase().includes('employee limit')) {
        const limitStatus = this.planAccessService.getEmployeeLimitStatus(this.usuariosActivos());
        errorMessage = limitStatus.reached
          ? this.planAccessService.getEmployeeLimitMessage(limitStatus)
          : this.t('employees.error.limit_reached').replace(' ({current}/{limit})', '');
      } else if (error?.error?.detail) {
        errorMessage = error.error.detail;
      } else if (error?.error?.error) {
        errorMessage = error.error.error;
      } else if (error.status === 403) {
        errorMessage = isUpdate
          ? 'No tienes permisos para actualizar este empleado.'
          : 'No tienes permisos para crear usuarios. Verifica tu plan de suscripción.';
      } else if (error?.error?.message) {
        errorMessage = error.error.message;
      } else if (error?.error && typeof error.error === 'object' && !Array.isArray(error.error)) {
        const fieldErrors = Object.values(error.error).flat().filter(Boolean);
        if (fieldErrors.length > 0) {
          errorMessage = fieldErrors.join('. ');
        }
      } else if (Array.isArray(error?.error)) {
        const msgs = error.error.filter(Boolean);
        if (msgs.length > 0) {
          errorMessage = msgs.join('. ');
        }
      }

      this.messageService.add({
        severity: 'error',
        summary: 'Error',
        detail: errorMessage
      });

      if (!isUpdate && this.isPlanLimitMessage(errorMessage)) {
        this.abrirDialogoLimitePlan('No se puede crear el empleado', errorMessage, planLimitContext);
      }
    } finally {
      this.guardando.set(false);
    }
  }

  private abrirDialogoLimitePlan(titulo: string, mensaje: string, recommendationContext?: string) {
    this.tituloDialogoLimitePlan = titulo;
    this.mensajeDialogoLimitePlan = mensaje;
    this.recomendacionUpgradePlan = this.planAccessService.getUpgradeRecommendation('employees', recommendationContext || mensaje);
    this.mostrarDialogoLimitePlan = true;
  }

  irANomina() {
    this.router.navigate(['/client/payroll']);
  }

  irAActualizarPlan() {
    this.mostrarDialogoLimitePlan = false;
    this.router.navigate(['/client/payment'], {
      state: {
        recommendedPlanName: this.recomendacionUpgradePlan?.nextPlanName || null,
        source: 'employee-limit'
      }
    });
  }

  private async sincronizarEmpleadosAntesDeCrear(): Promise<void> {
    try {
      const params: any = {};
      const activeBranchId = this.branchService.activeBranchId();
      if (activeBranchId) {
        params.branch_id = activeBranchId;
      }
      const data = await firstValueFrom(this.employeeService.getEmployees(params));
      const responseEmployees = (Array.isArray((data as any)?.results) ? (data as any).results : (Array.isArray(data) ? data : [])) as EmployeeWithUserDto[];
      this.empleados.set(responseEmployees);
      this.syncActiveUsersCountFromEmployees(responseEmployees);
    } catch {
      // Si falla el refresh, usamos el estado local como fallback.
    }
  }

  private buildPlanLimitErrorMessage(error: any): string | null {
    const payload = error?.error;
    if (!payload || typeof payload !== 'object') {
      return null;
    }

    const rawError = this.normalizeBackendErrorValue(payload.error);
    const rawMessage = this.normalizeBackendErrorValue(payload.message);
    const rawCurrent = this.normalizeBackendErrorValue(payload.current);
    const rawLimit = this.normalizeBackendErrorValue(payload.limit);

    if (rawError.includes('Límite de empleados alcanzado')) {
      if (rawCurrent && rawLimit) {
        return `Límite de usuarios activos alcanzado (${rawCurrent}/${rawLimit}). Actualiza tu plan para agregar más personal.`;
      }
      return rawMessage || 'Límite de usuarios activos alcanzado. Actualiza tu plan para agregar más personal.';
    }

    if (rawError.includes('User limit reached')) {
      if (rawCurrent && rawLimit) {
        return `Límite de usuarios alcanzado (${rawCurrent}/${rawLimit}). Actualiza tu plan para agregar más usuarios.`;
      }
      return rawMessage || 'Límite de usuarios alcanzado. Actualiza tu plan para agregar más usuarios.';
    }

    return null;
  }

  private getPlanLimitContext(error: any): string {
    const payload = error?.error;
    if (!payload || typeof payload !== 'object') {
      return '';
    }

    const rawError = this.normalizeBackendErrorValue(payload.error);
    const rawMessage = this.normalizeBackendErrorValue(payload.message);

    return `${rawError} ${rawMessage}`.trim();
  }

  private normalizeBackendErrorValue(value: unknown): string {
    if (Array.isArray(value)) {
      return value.map((item) => this.normalizeBackendErrorValue(item)).filter(Boolean).join(' ');
    }

    if (value && typeof value === 'object') {
      const maybeString = (value as { string?: unknown }).string;
      if (typeof maybeString === 'string') {
        return maybeString;
      }
    }

    return typeof value === 'string' || typeof value === 'number' ? String(value) : '';
  }

  private isPlanLimitMessage(message: string): boolean {
    const normalized = String(message || '').toLowerCase();
    return normalized.includes('límite de usuarios alcanzado')
      || normalized.includes('límite de empleados alcanzado')
      || normalized.includes('actualiza tu plan');
  }

  confirmarEliminar(emp: EmployeeWithUserDto) {
    const nombreEmpleado = emp.user.full_name || emp.user.email || 'este empleado';
    this.confirmationService.confirm({
      message: this.t('employees.confirm.delete_msg').replace('{name}', nombreEmpleado),
      header: this.t('employees.confirm.delete_title'),
      icon: 'pi pi-exclamation-triangle',
      acceptLabel: this.t('clients.delete_confirm_accept'),
      rejectLabel: this.t('common.cancel'),
      accept: () => this.eliminarEmpleado(emp)
    });
  }

  async eliminarEmpleado(emp: EmployeeWithUserDto) {
    try {
      // Eliminar usuario (esto maneja automáticamente la relación con Employee)
      await firstValueFrom(this.authService.deleteUser(emp.user_id));
      
      // NOTA: No se llama DELETE /api/employees/ porque:
      // 1. El endpoint puede no existir o estar deshabilitado
      // 2. La eliminación del usuario maneja la cascada automáticamente

      this.empleados.update(lista => lista.filter(e => e.user_id !== emp.user_id));
      this.messageService.add({
        severity: 'success',
        summary: this.t('common.success'),
        detail: this.t('employees.toast.delete_success')
      });
    } catch (error: any) {
      if (!environment.production) {
        
      }

      // Si ya no existe en backend, considerar operación idempotente exitosa.
      if (error?.status === 404) {
        this.empleados.update(lista => lista.filter(e => e.user_id !== emp.user_id));
        this.messageService.add({
          severity: 'success',
          summary: this.t('common.success'),
          detail: this.t('employees.toast.delete_already')
        });
        return;
      }

      // Fallback: si el backend bloquea borrado físico por integridad/relaciones,
      // desactivar el usuario para no romper la operación.
      if (error?.status === 400 || error?.status === 409) {
        try {
          await firstValueFrom(this.authService.updateUser(emp.user_id, { is_active: false } as any));

          if (emp.id > 0) {
            await firstValueFrom(this.employeeService.patchEmployee(emp.id, { is_active: false } as any));
          }

          this.empleados.update(lista =>
            lista.map(e =>
              e.user_id === emp.user_id
                ? { ...e, is_active: false, user: { ...e.user, is_active: false } }
                : e
            )
          );

          this.messageService.add({
            severity: 'warn',
            summary: 'Empleado desactivado',
            detail: 'El empleado tiene citas o ventas asociadas y no puede eliminarse. Se ha desactivado para que no aparezca en el sistema.'
          });
          return;
        } catch {
          // Si también falla desactivar, mostrar error original
        }
      }

      const backendMessage =
        error?.error?.error ||
        error?.error?.detail ||
        error?.error?.message ||
        'No se pudo eliminar el empleado';

      this.messageService.add({
        severity: 'error',
        summary: 'Error',
        detail: backendMessage
      });
    }
  }

  getRoleDisplayName(role: string, businessRole?: string | null, businessRoleDisplay?: string | null): string {
    const raw = getRoleDisplayLabel(role, businessRole, businessRoleDisplay);
    if (raw === 'Propietario') return this.t('employees.roles.owner');
    if (raw === 'Gerente') return this.t('employees.roles.manager');
    if (raw === 'Recepcion / Caja') return this.t('employees.roles.frontdesk_cashier');
    if (raw === 'Profesional') return this.t('employees.roles.professional');
    return raw;
  }

  getRoleSeverity(role: string): 'success' | 'secondary' | 'info' | 'warn' | 'danger' {
    const severities: { [key: string]: 'success' | 'secondary' | 'info' | 'warn' | 'danger' } = {
      'Profesional': 'info',
      'Recepcion / Caja': 'success',
      'Gerente': 'warn',
      'Propietario': 'danger'
    };
    return severities[role] || 'secondary';
  }

  getProfessionLabel(value: string): string {
    const found = EMPLOYEE_CONFIG.PROFESSIONS.find(s => s.value === value);
    return found ? found.label : value;
  }

  getAssignedServicesPreview(emp: EmployeeWithUserDto): string {
    const ids = emp.service_ids || [];
    if (!ids.length) {
      return this.t('employees.no_appointments_role_hint');
    }

    const names = ids
      .map(id => this.servicesOptions.find(service => service.value === id)?.label?.split(' - $')[0])
      .filter((name): name is string => !!name);

    if (!names.length) {
      return `${ids.length} servicio(s) asignado(s)`;
    }

    const preview = names.slice(0, 2).join(', ');
    return names.length > 2 ? `${preview} y ${names.length - 2} más` : preview;
  }

  cerrarDialogo() {
    this.mostrarDialogo = false;
    this.empleadoSeleccionado = null;
    this.formulario.reset({ business_role: 'professional', profession: '', service_ids: [], is_active: true });
  }

  isServiceAssignableRole(role: string | null | undefined, businessRole?: string | null): boolean {
    return isServiceAssignableBusinessRole(role, businessRole);
  }

  // Nuevos métodos para configuración de nómina
  async verConfiguracionNomina(emp: EmployeeWithUserDto) {
    this.empleadoDetalle = emp;
    this.mostrarConfigNomina = true;

    // Cargar configuración de nómina
    await this.cargarConfigNomina();
  }

  async cargarConfigNomina() {
    if (!this.empleadoDetalle?.id) return;

    try {
      const config = await firstValueFrom(this.employeeService.getPayrollConfig(this.empleadoDetalle.id)) as any;
      if (config) {
        // Mapear nombres del backend a nombres del formulario
        this.formularioNomina.patchValue({
          salary_type: config.payment_type || 'commission',
          contractual_monthly_salary: config.fixed_salary || 0,
          commission_percentage: config.commission_rate || 40
        });
        this.syncPayrollFieldsByType(config.payment_type || 'commission');
      }
    } catch (error) {
      if (!environment.production) {
        
      }
    }
  }

  async guardarConfigNomina() {
    if (!this.empleadoDetalle?.id || this.formularioNomina.invalid) return;

    this.guardandoNomina.set(true);
    try {
      // Mapear nombres del formulario a nombres del backend
      const backendData = {
        payment_type: this.formularioNomina.get('salary_type')?.value,
        fixed_salary: this.formularioNomina.get('contractual_monthly_salary')?.value || 0,
        commission_rate: this.formularioNomina.get('commission_percentage')?.value || 0
      };

      await firstValueFrom(this.employeeService.updatePayrollConfig(this.empleadoDetalle.id, backendData));

      // Recargar datos de empleados para reflejar cambios inmediatamente
      await this.cargarDatos();

      // Cerrar diálogo automáticamente tras éxito
      this.cerrarConfigNomina();

      this.messageService.add({
        severity: 'success',
        summary: this.t('common.success'),
        detail: this.t('employees.toast.payroll_success')
      });
    } catch (error) {
      this.messageService.add({
        severity: 'error',
        summary: this.t('common.error'),
        detail: this.t('employees.error.save_payroll')
      });
    } finally {
      this.guardandoNomina.set(false);
    }
  }

  cerrarConfigNomina() {
    this.mostrarConfigNomina = false;
    this.empleadoDetalle = null;
  }

  private syncPayrollFieldsByType(salaryType: string | null | undefined) {
    const commissionControl = this.formularioNomina.get('commission_percentage');
    const salaryControl = this.formularioNomina.get('contractual_monthly_salary');

    if (!commissionControl || !salaryControl) {
      return;
    }

    if (salaryType === 'fixed') {
      commissionControl.disable({ emitEvent: false });
      salaryControl.enable({ emitEvent: false });
      return;
    }

    if (salaryType === 'commission') {
      salaryControl.disable({ emitEvent: false });
      commissionControl.enable({ emitEvent: false });
      return;
    }

    commissionControl.enable({ emitEvent: false });
    salaryControl.enable({ emitEvent: false });
  }

  // Métodos para historial de pagos
  async verHistorialPagos(emp: EmployeeWithUserDto) {
    this.empleadoDetalle = emp;
    this.mostrarHistorial = true;

    // Cargar datos solo cuando se abre el diálogo
    await Promise.all([
      this.cargarHistorialPagos(),
      this.cargarEstadisticasPagos()
    ]);
  }

  async cargarHistorialPagos() {
    if (!this.empleadoDetalle?.id) return;

    this.cargandoHistorial.set(true);
    try {
      const response = await firstValueFrom(this.employeeService.getPaymentHistory(this.empleadoDetalle.id)) as any;
      this.historialPagos.set(response.payments || []);
    } catch (error) {
      if (!environment.production) {
        
      }
      this.messageService.add({
        severity: 'error',
        summary: this.t('common.error'),
        detail: this.t('employees.error.load_payments')
      });
    } finally {
      this.cargandoHistorial.set(false);
    }
  }

  async cargarEstadisticasPagos() {
    if (!this.empleadoDetalle?.id) return;

    this.cargandoStats.set(true);
    try {
      const response = await firstValueFrom(this.employeeService.getPaymentStats(this.empleadoDetalle.id)) as any;
      this.paymentStats.set(response);
    } catch (error) {
      if (!environment.production) {
        
      }
    } finally {
      this.cargandoStats.set(false);
    }
  }

  cerrarHistorial() {
    this.mostrarHistorial = false;
    this.empleadoDetalle = null;
    this.historialPagos.set([]);
    this.paymentStats.set(null);
  }

  async verReciboPago(payment: PaymentDto) {
    if (!payment?.id) {
      this.messageService.add({
        severity: 'error',
        summary: this.t('common.error'),
        detail: this.t('employees.error.invalid_payment_id')
      });
      return;
    }

    try {
      const response = await firstValueFrom(this.employeeService.getPaymentReceipt(payment.id.toString())) as PaymentReceiptDto;
      this.reciboActual.set(response);
      this.mostrarRecibo = true;
    } catch (error) {
      if (!environment.production) {
        
      }
      this.messageService.add({
        severity: 'error',
        summary: this.t('common.error'),
        detail: this.t('employees.error.load_receipt')
      });
    }
  }

  cerrarRecibo() {
    this.mostrarRecibo = false;
    this.reciboActual.set(null);
  }

  imprimirRecibo() {
    window.print();
  }

  // Métodos para préstamos
  async verPrestamos(emp: EmployeeWithUserDto) {
    this.empleadoDetalle = emp;
    this.mostrarPrestamos = true;

    // Cargar datos de préstamos
    await Promise.all([
      this.cargarPrestamos(),
      this.cargarResumenPrestamos()
    ]);
  }

  async cargarPrestamos() {
    if (!this.empleadoDetalle?.id) return;

    this.cargandoPrestamos.set(true);
    try {
      const response = await firstValueFrom(this.employeeService.getLoans(this.empleadoDetalle.id)) as any;
      this.prestamos.set(response.loans || []);
    } catch (error) {
      if (!environment.production) {
        
      }
      this.messageService.add({
        severity: 'error',
        summary: this.t('common.error'),
        detail: this.t('employees.error.load_loans')
      });
    } finally {
      this.cargandoPrestamos.set(false);
    }
  }

  async cargarResumenPrestamos() {
    if (!this.empleadoDetalle?.id) return;

    this.cargandoResumenPrestamos.set(true);
    try {
      const response = await firstValueFrom(this.employeeService.getLoansSummary(this.empleadoDetalle.id)) as any;
      this.resumenPrestamos.set(response);
    } catch (error) {
      if (!environment.production) {
        
      }
    } finally {
      this.cargandoResumenPrestamos.set(false);
    }
  }

  cerrarPrestamos() {
    this.mostrarPrestamos = false;
    this.empleadoDetalle = null;
    this.prestamos.set([]);
    this.resumenPrestamos.set(null);
  }

  abrirNuevoPrestamo() {
    this.formularioPrestamo.reset({
      loan_type: '',
      amount: null,
      installments: null,
      reason: ''
    });
    this.mostrarNuevoPrestamo = true;
  }

  cerrarNuevoPrestamo() {
    this.mostrarNuevoPrestamo = false;
    this.formularioPrestamo.reset();
  }

  calcularPagoMensual(): number {
    const amount = this.formularioPrestamo.get('amount')?.value;
    const installments = this.formularioPrestamo.get('installments')?.value;

    if (!amount || !installments || amount <= 0 || installments <= 0) {
      return 0;
    }

    return amount / installments;
  }

  async crearPrestamo() {
    if (this.formularioPrestamo.invalid || !this.empleadoDetalle?.id) {
      this.formularioPrestamo.markAllAsTouched();
      return;
    }

    this.guardandoPrestamo.set(true);
    try {
      const loanData: CreateLoanDto = {
        loan_type: this.formularioPrestamo.get('loan_type')?.value,
        amount: this.formularioPrestamo.get('amount')?.value,
        installments: this.formularioPrestamo.get('installments')?.value,
        reason: this.formularioPrestamo.get('reason')?.value || ''
      };

      await firstValueFrom(this.employeeService.createLoan(this.empleadoDetalle.id, loanData));

      this.messageService.add({
        severity: 'success',
        summary: this.t('common.success'),
        detail: this.t('employees.toast.loan_success')
      });

      this.cerrarNuevoPrestamo();

      // Recargar datos de préstamos
      await Promise.all([
        this.cargarPrestamos(),
        this.cargarResumenPrestamos()
      ]);
    } catch (error: any) {
      if (!environment.production) {
        
      }
      this.messageService.add({
        severity: 'error',
        summary: 'Error',
        detail: error?.error?.message || 'No se pudo crear el préstamo'
      });
    } finally {
      this.guardandoPrestamo.set(false);
    }
  }

  getLoanTypeLabel(type: string): string {
    const labels: { [key: string]: string } = {
      'advance': this.t('employees.loan_type.advance'),
      'personal_loan': this.t('employees.loan_type.personal'),
      'emergency': this.t('employees.loan_type.emergency')
    };
    return labels[type] || type;
  }

  getLoanStatusLabel(status: string): string {
    const labels: { [key: string]: string } = {
      'active': this.t('employees.loan_status.active'),
      'paid': this.t('employees.loan_status.paid'),
      'cancelled': this.t('employees.loan_status.cancelled')
    };
    return labels[status] || status;
  }

  getLoanStatusSeverity(status: string): 'success' | 'info' | 'warn' | 'danger' {
    const severities: { [key: string]: 'success' | 'info' | 'warn' | 'danger' } = {
      'active': 'info',
      'paid': 'success',
      'cancelled': 'danger'
    };
    return severities[status] || 'info';
  }

  private async esperarEmpleadoPorUsuario(userId: number, maxAttempts = 6, delayMs = 250): Promise<EmployeeWithUserDto | null> {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        const employee = await firstValueFrom(this.employeeService.getEmployeeByUserId(userId)) as any;
        if (employee?.id) {
          return employee as EmployeeWithUserDto;
        }
      } catch (error: any) {
        if (error?.status !== 404) {
          throw error;
        }
      }

      if (attempt < maxAttempts - 1) {
        await this.delay(delayMs);
      }
    }

    return null;
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
