import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { I18nPipe } from '../../../core/pipes/i18n.pipe';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { CommonModule } from '@angular/common';
import { AbstractControl, FormBuilder, FormGroup, FormsModule, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { MessageService, ConfirmationService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { TextareaModule } from 'primeng/textarea';
import { SelectModule } from 'primeng/select';
import { DatePickerModule } from 'primeng/datepicker';
import { CheckboxModule } from 'primeng/checkbox';
import { ToastModule } from 'primeng/toast';
import { ConfirmDialogModule } from 'primeng/confirmdialog';

import { firstValueFrom } from 'rxjs';
import { ClientService, Client } from '../../../core/services/client/client.service';
import { BranchService } from '../../../core/services/branch/branch.service';
import { PlanAccessService } from '../../../core/services/plan-access.service';
import { environment } from '../../../../environments/environment';
import { ClientDto, CreateClientDto, UpdateClientDto } from '../../../core/dto/client.dto';
import { AuronPaginationComponent } from '../../../shared/components/auron-pagination/auron-pagination.component';
import { AuronEmptyStateComponent } from '../../../shared/components/auron-empty-state/auron-empty-state.component';
import { AuronEyebrowComponent } from '../../../shared/components/auron-eyebrow/auron-eyebrow.component';
import { AuBtn, AuSkeleton } from '../../../shared/components';

@Component({
    selector: 'app-clients-management',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        ReactiveFormsModule,
        AuronPaginationComponent,
        AuronEmptyStateComponent,
        AuronEyebrowComponent,
        AuBtn,
        ButtonModule,
        DialogModule,
        InputTextModule,
        TextareaModule,
        SelectModule,
        DatePickerModule,
        CheckboxModule,
        ToastModule,
        ConfirmDialogModule,
        I18nPipe,
        AuSkeleton
    ],
    providers: [MessageService, ConfirmationService],
    changeDetection: ChangeDetectionStrategy.OnPush,
    template: `
        <div class="clients-shell">
            <section class="overflow-hidden rounded-[2rem] border border-surface-200/70 bg-surface-0 shadow-[var(--shadow-elevated)] dark:border-surface-800 dark:bg-surface-900">
                <div class="relative overflow-hidden px-8 py-8 lg:px-10">
                    <div class="hero-gradient"></div>
                    <div class="relative space-y-7">
                        <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                            <div>
                                <auron-eyebrow class="mb-4 block" icon="pi pi-users" label="Radar de relaciones"></auron-eyebrow>
                                <h1 class="display-3 text-surface-950 dark:text-surface-0">Clientes y seguimiento</h1>
                                <p class="mt-3 max-w-3xl text-base leading-7 text-surface-600 dark:text-surface-300">
                                    Vista operativa para mantener contacto, detectar clientes activos y sostener la recurrencia del salón.
                                </p>
                            </div>
                            <button au-btn variant="primary" icon="pi pi-plus" (click)="abrirDialogo()" class="self-start">{{ 'clients.new_client' | t }}</button>
                        </div>

                        <div class="grid gap-3 md:grid-cols-3">
                            <div class="rounded-2xl border border-surface-200 bg-white/70 px-4 py-3 dark:border-surface-700 dark:bg-surface-800/70">
                                <div class="text-[11px] font-semibold uppercase tracking-[0.22em] text-surface-500 dark:text-surface-400">Total CRM</div>
                                <div class="mt-2 text-2xl font-semibold text-surface-950 dark:text-white">{{ clientes().length }}</div>
                            </div>
                            <div class="rounded-2xl border border-emerald-200 bg-emerald-50/70 px-4 py-3 dark:border-emerald-900/60 dark:bg-emerald-900/10">
                                <div class="text-[11px] font-semibold uppercase tracking-[0.22em] text-emerald-700 dark:text-emerald-300">Activos</div>
                                <div class="mt-2 text-2xl font-semibold text-emerald-800 dark:text-emerald-200">{{ getActiveClientsCount() }}</div>
                            </div>
                            <div class="rounded-2xl border border-[var(--brand)]/20 bg-[rgba(26,86,219,0.06)] px-4 py-3 dark:border-[var(--brand)]/30 dark:bg-[rgba(26,86,219,0.08)]">
                                <div class="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--brand)] dark:text-[var(--brand-400)]">Con contacto</div>
                                <div class="mt-2 text-2xl font-semibold text-surface-950 dark:text-white">{{ getContactableClientsCount() }}</div>
                            </div>
                        </div>

                        <div class="grid gap-4 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.4fr)]">
                            <div class="rounded-2xl border border-surface-200 bg-surface-50/80 p-4 dark:border-surface-700 dark:bg-surface-800/60">
                                <div class="text-xs font-semibold uppercase tracking-[0.2em] text-surface-500 dark:text-surface-400">Cliente destacado</div>
                                <div class="mt-3 text-xl font-semibold text-surface-950 dark:text-white">{{ getFeaturedClient()?.full_name || 'Sin clientes aún' }}</div>
                                <p class="mt-2 text-sm leading-6 text-surface-600 dark:text-surface-300">{{ getClientsNarrative() }}</p>
                            </div>
                            <div class="rounded-2xl border border-surface-200 bg-white/70 p-4 dark:border-surface-700 dark:bg-surface-800/70">
                                <div class="mb-3 flex items-center justify-between gap-3">
                                    <div class="text-xs font-semibold uppercase tracking-[0.2em] text-surface-500 dark:text-surface-400">Actividad reciente en clientes</div>
                                    <span class="text-xs text-surface-400">CRM Auron</span>
                                </div>
                                <div class="grid gap-2 md:grid-cols-3">
                                    <div *ngFor="let client of getRecentClients()" class="rounded-xl bg-surface-0 px-3 py-3 text-sm dark:bg-surface-900">
                                        <div class="font-semibold text-surface-900 dark:text-white">{{ client.full_name }}</div>
                                        <div class="mt-1 text-xs text-surface-500 dark:text-surface-400">{{ getClientContactLabel(client) }}</div>
                                    </div>
                                    <div *ngIf="getRecentClients().length === 0" class="rounded-xl bg-surface-0 px-3 py-3 text-sm text-surface-500 dark:bg-surface-900 dark:text-surface-400">
                                        Registra el primer cliente para activar el radar.
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <div class="overflow-hidden rounded-[1.75rem] border border-surface-200 bg-white shadow-sm dark:border-surface-700 dark:bg-surface-900">
              <div class="px-6 py-5">
                <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <span class="text-sm font-medium text-surface-600 dark:text-surface-400">{{ getActiveClientsText() }}</span>
                  <div class="relative w-full lg:w-72">
                    <i class="pi pi-search absolute left-3 top-1/2 -translate-y-1/2 text-sm text-surface-400"></i>
                    <input type="text" (input)="onGlobalFilter($event)" (keyup.enter)="onGlobalFilter($event)" [placeholder]="'clients.search_placeholder' | t" class="w-full rounded-lg border border-surface-200 bg-surface-0 py-2 pl-9 pr-3 text-sm text-surface-700 placeholder-surface-400 shadow-sm focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:placeholder-surface-500" />
                  </div>
                </div>
              </div>

              <div class="flow-root">
                <div class="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
                  <div class="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
                    <table class="min-w-full divide-y divide-surface-200 dark:divide-surface-700">
                      <thead>
                        <tr>
                          <th scope="col" class="py-3.5 pr-3 pl-4 text-left text-sm font-semibold text-surface-950 dark:text-surface-0 sm:pl-0" style="width:3rem">
                            <input type="checkbox" [checked]="allSelected()" (change)="toggleSelectAll($event)" class="h-4 w-4 rounded border-surface-300 text-primary focus:ring-primary dark:border-surface-600" />
                          </th>
                          <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">
                            <button type="button" (click)="toggleSort('full_name')" class="group inline-flex items-center">
                              {{ 'clients.th_client' | t }}
                              <span class="ml-2 flex-none rounded-sm" [class.bg-blue-100]="sortField() === 'full_name'" [class.text-blue-700]="sortField() === 'full_name'" [class.dark:bg-blue-900\/50]="sortField() === 'full_name'" [class.dark:text-blue-400]="sortField() === 'full_name'" [class.invisible]="sortField() !== 'full_name'" [class.text-surface-500]="sortField() !== 'full_name'" [class.group-hover:visible]="sortField() !== 'full_name'">
                                <i class="pi" [class.pi-sort-up]="sortField() === 'full_name' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'full_name' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'full_name'"></i>
                              </span>
                            </button>
                          </th>
                          <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">{{ 'clients.th_contact' | t }}</th>
                          <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">{{ 'clients.th_birthday' | t }}</th>
                          <th *ngIf="canAccessMultiLocation" scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">{{ 'appointments.branch' | t }}</th>
                          <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">{{ 'clients.th_points' | t }}</th>
                          <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-950 dark:text-surface-0">
                            <button type="button" (click)="toggleSort('is_active')" class="group inline-flex items-center">
                              {{ 'clients.th_status' | t }}
                              <span class="ml-2 flex-none rounded-sm" [class.bg-blue-100]="sortField() === 'is_active'" [class.text-blue-700]="sortField() === 'is_active'" [class.dark:bg-blue-900\/50]="sortField() === 'is_active'" [class.dark:text-blue-400]="sortField() === 'is_active'" [class.invisible]="sortField() !== 'is_active'" [class.text-surface-500]="sortField() !== 'is_active'" [class.group-hover:visible]="sortField() !== 'is_active'">
                                <i class="pi" [class.pi-sort-up]="sortField() === 'is_active' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'is_active' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'is_active'"></i>
                              </span>
                            </button>
                          </th>
                          <th scope="col" class="py-3.5 pl-3 pr-0 text-right text-sm font-semibold text-surface-950 dark:text-surface-0">
                            <span class="sr-only">Acciones</span>
                          </th>
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-surface-200 dark:divide-surface-700">
                        @if (cargando()) {
                          @for (i of [1,2,3,4,5]; track i) {
                            <tr class="hover:bg-surface-50 dark:hover:bg-surface-800/50">
                              <td class="py-4 pr-3 pl-4 text-sm whitespace-nowrap sm:pl-0" style="width:3rem">
                                <au-skeleton width="1rem" height="1rem" />
                              </td>
                              <td class="px-3 py-4 text-sm whitespace-nowrap">
                                <div class="flex flex-col gap-1">
                                  <au-skeleton width="140px" height="16px" />
                                  <au-skeleton width="80px" height="10px" />
                                </div>
                              </td>
                              <td class="px-3 py-4 text-sm whitespace-nowrap">
                                <div class="flex flex-col gap-1">
                                  <au-skeleton width="160px" height="14px" />
                                  <au-skeleton width="120px" height="14px" />
                                </div>
                              </td>
                              <td class="px-3 py-4 text-sm whitespace-nowrap">
                                <au-skeleton width="90px" height="16px" />
                              </td>
                              <td *ngIf="canAccessMultiLocation" class="px-3 py-4 text-sm whitespace-nowrap">
                                <au-skeleton width="70px" height="16px" />
                              </td>
                              <td class="px-3 py-4 text-sm whitespace-nowrap">
                                <au-skeleton width="30px" height="16px" />
                              </td>
                              <td class="px-3 py-4 text-sm whitespace-nowrap">
                                <au-skeleton width="70px" height="22px" />
                              </td>
                              <td class="py-4 pl-3 pr-0 text-right text-sm whitespace-nowrap">
                                <div class="flex items-center justify-end gap-1">
                                  <au-skeleton width="28px" height="28px" />
                                  <au-skeleton width="28px" height="28px" />
                                </div>
                              </td>
                            </tr>
                          }
                        } @else {
                          @for (cliente of sortedClients(); track cliente.id) {
                            <tr class="hover:bg-surface-50 dark:hover:bg-surface-800/50">
                              <td class="py-4 pr-3 pl-4 text-sm whitespace-nowrap sm:pl-0" style="width:3rem">
                                <input type="checkbox" [checked]="isSelected(cliente)" (change)="toggleSelection(cliente)" class="h-4 w-4 rounded border-surface-300 text-primary focus:ring-primary dark:border-surface-600" />
                              </td>
                              <td class="px-3 py-4 text-sm whitespace-nowrap">
                                <div class="flex flex-col">
                                  <span class="font-semibold text-surface-900 dark:text-white">{{ cliente.full_name }}</span>
                                  @if (cliente.notes) {
                                    <span class="text-xs italic text-surface-500 dark:text-surface-400">{{ cliente.notes }}</span>
                                  }
                                </div>
                              </td>
                              <td class="px-3 py-4 text-sm whitespace-nowrap text-surface-700 dark:text-surface-200">
                                <div class="flex flex-col gap-0.5">
                                  @if (cliente.email) {
                                    <span class="inline-flex items-center gap-1"><i class="pi pi-envelope text-[10px] text-surface-400"></i> {{ cliente.email }}</span>
                                  }
                                  @if (cliente.phone) {
                                    <span class="inline-flex items-center gap-1"><i class="pi pi-phone text-[10px] text-surface-400"></i> {{ cliente.phone }}</span>
                                  }
                                  @if (!cliente.email && !cliente.phone) {
                                    <span class="text-surface-400">—</span>
                                  }
                                </div>
                              </td>
                              <td class="px-3 py-4 text-sm whitespace-nowrap">
                                <div class="inline-flex items-center gap-1.5">
                                  <span>{{ formatearFecha(cliente) }}</span>
                                  @if (esCumpleanosHoy(cliente)) {
                                    <i class="pi pi-gift text-yellow-500" title="Cumpleaños hoy"></i>
                                  } @else if (esCumpleanosEsteMes(cliente)) {
                                    <i class="pi pi-calendar text-blue-500" title="Cumpleaños este mes"></i>
                                  }
                                </div>
                              </td>
                              <td *ngIf="canAccessMultiLocation" class="px-3 py-4 text-sm whitespace-nowrap text-surface-700 dark:text-surface-200">
                                {{ getBranchName(cliente.branch) }}
                              </td>
                              <td class="px-3 py-4 text-sm whitespace-nowrap text-surface-400">—</td>
                              <td class="px-3 py-4 text-sm whitespace-nowrap">
                                <span [class]="'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ' + (cliente.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300')">
                                  {{ cliente.is_active ? ('clients.status_active' | t) : ('clients.status_inactive' | t) }}
                                </span>
                              </td>
                              <td class="py-4 pl-3 pr-0 text-right text-sm whitespace-nowrap">
                                <div class="flex items-center justify-end gap-1">
                                  <button type="button" (click)="editarCliente(cliente)" class="rounded-lg p-1.5 text-blue-700 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/30" title="Editar">
                                    <i class="pi pi-pencil"></i>
                                  </button>
                                  <button type="button" (click)="confirmarEliminar(cliente)" class="rounded-lg p-1.5 text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/30" title="Eliminar">
                                    <i class="pi pi-trash"></i>
                                  </button>
                                </div>
                              </td>
                            </tr>
                          } @empty {
                            <tr>
                              <td [attr.colspan]="canAccessMultiLocation ? 8 : 7">
                                <auron-empty-state
                                  icon="pi pi-users"
                                  title="Sin clientes aún"
                                  description="Aún no tienes clientes registrados. Cuando alguien agende, aparecerá aquí."
                                  ctaLabel="Agregar cliente"
                                  variant="contextual"
                                  (ctaAction)="abrirDialogo()">
                                </auron-empty-state>
                              </td>
                            </tr>
                          }
                        }
                      </tbody>
                    </table>
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
            </div>

            <p-dialog [header]="clienteSeleccionado ? t('clients.edit_client') : t('clients.new_client')"
                      [(visible)]="mostrarDialogo" [modal]="true" [style]="{width: '92vw', maxWidth: '560px'}"
                      [breakpoints]="{'960px':'75vw','640px':'100vw'}"
                      [closable]="!guardando()" [closeOnEscape]="!guardando()">
                <form [formGroup]="formulario" (ngSubmit)="guardarCliente()" class="grid gap-4">
                    <div>
                        <label class="block font-medium mb-1">{{ 'clients.form_fullname' | t }}</label>
                        <small class="mb-2 block text-surface-500 dark:text-surface-400">{{ 'clients.form_fullname_hint' | t }}</small>
                        <input pInputText formControlName="full_name" class="w-full"
                               [class.ng-invalid]="formulario.get('full_name')?.invalid && formulario.get('full_name')?.touched">
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block font-medium mb-1">{{ 'clients.form_email' | t }}</label>
                            <input pInputText formControlName="email" type="email" class="w-full"
                                   [class.ng-invalid]="formulario.get('email')?.invalid && formulario.get('email')?.touched">
                            <small *ngIf="formulario.get('email')?.invalid && formulario.get('email')?.touched" class="text-red-500 block mt-1">{{ 'clients.form_email_invalid' | t }}</small>
                        </div>
                        <div>
                            <label class="block font-medium mb-1">{{ 'clients.form_phone' | t }}</label>
                            <input pInputText formControlName="phone" class="w-full">
                        </div>
                    </div>
                    <small *ngIf="formulario.errors?.['contactRequired'] && (formulario.get('email')?.touched || formulario.get('phone')?.touched)" class="text-red-500 block -mt-2">{{ 'clients.form_contact_required' | t }}</small>
                    <div>
                        <label class="block font-medium mb-1">{{ 'clients.form_address' | t }}</label>
                        <input pInputText formControlName="address" class="w-full">
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block font-medium mb-1">{{ 'clients.form_birthday' | t }}</label>
                            <p-datepicker formControlName="birthday" dateFormat="dd/mm/yy" appendTo="body" class="w-full" [showClear]="true" [maxDate]="todayDate"></p-datepicker>
                        </div>
                        <div>
                            <label class="block font-medium mb-1">{{ 'clients.form_gender' | t }}</label>
                            <p-select formControlName="gender" [options]="generoOptions" appendTo="body" optionLabel="label" optionValue="value" [placeholder]="'clients.form_gender_placeholder' | t" class="w-full"></p-select>
                        </div>
                    </div>
                    <div>
                        <label class="block font-medium mb-1">{{ 'clients.form_notes' | t }}</label>
                        <textarea pInputTextarea formControlName="notes" class="w-full" rows="2" [placeholder]="'clients.form_notes_placeholder' | t"></textarea>
                    </div>
                    <div *ngIf="canAccessMultiLocation && branchService.branches().length > 0">
                        <label class="block font-medium mb-1">{{ 'appointments.branch' | t }}</label>
                        <p-select formControlName="branch" [options]="branchService.branches()" appendTo="body" optionLabel="name" optionValue="id" [placeholder]="'common.select' | t" [showClear]="true" class="w-full"></p-select>
                    </div>
                    <div class="flex items-center gap-2">
                        <p-checkbox formControlName="is_active" [binary]="true" inputId="activo"></p-checkbox>
                        <label for="activo" class="font-medium">{{ 'clients.form_active' | t }}</label>
                    </div>
                    <div class="flex justify-end gap-2 mt-2">
                        <button au-btn variant="ghost" type="button" (click)="cerrarDialogo()" [disabled]="guardando()">{{ 'appointments.cancelar' | t }}</button>
                        <button au-btn variant="primary" type="submit" icon="pi pi-check" [loading]="guardando()" [disabled]="formulario.invalid">{{ clienteSeleccionado ? t('common.save') : t('clients.crear') }}</button>
                    </div>
                </form>
            </p-dialog>
        </div>

        <p-confirmDialog></p-confirmDialog>
        <p-toast></p-toast>


    `
})
export class ClientsManagement implements OnInit {
    private localeService = inject(LocaleService);
    private clientService = inject(ClientService);
    protected branchService = inject(BranchService);
    private planAccessService = inject(PlanAccessService);

    t(key: string): string {
        return this.localeService.t(key as any);
    }
    private messageService = inject(MessageService);
    private confirmationService = inject(ConfirmationService);
    private fb = inject(FormBuilder);

    canAccessMultiLocation = false;

    clientes = signal<ClientDto[]>([]);

    getActiveClientsText(): string {
        return this.t('clients.active_count')
            .replace('{active}', String(this.getActiveClientsCount()))
            .replace('{total}', String(this.clientes().length));
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
    cargando = signal(false);
    guardando = signal(false);
    mostrarDialogo = false;
    clienteSeleccionado: ClientDto | null = null;
    todayDate = new Date();

    // Sorting, pagination & selection signals
    sortField = signal<string>('full_name');
    sortOrder = signal<'asc' | 'desc'>('asc');
    currentPage = signal(0);
    pageSize = signal(10);
    globalFilter = signal('');
    selectedClientsSet = signal<Set<number>>(new Set());

    sortedClients = computed(() => {
        const all = this.clientes();
        const field = this.sortField();
        const order = this.sortOrder();
        const filter = this.globalFilter().toLowerCase();
        let filtered = all;
        if (filter) {
            filtered = all.filter(c =>
                (c.full_name?.toLowerCase() || '').includes(filter) ||
                (c.email?.toLowerCase() || '').includes(filter) ||
                (c.phone?.toLowerCase() || '').includes(filter)
            );
        }
        const sorted = [...filtered].sort((a, b) => {
            let aVal: string, bVal: string;
            switch (field) {
                case 'full_name':
                    aVal = (a.full_name || '').toLowerCase();
                    bVal = (b.full_name || '').toLowerCase();
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
        const all = this.clientes();
        const filter = this.globalFilter().toLowerCase();
        if (!filter) return all.length;
        return all.filter(c =>
            (c.full_name?.toLowerCase() || '').includes(filter) ||
            (c.email?.toLowerCase() || '').includes(filter) ||
            (c.phone?.toLowerCase() || '').includes(filter)
        ).length;
    });

    totalPages = computed(() => Math.max(1, Math.ceil(this.totalRecords() / this.pageSize())));
    firstRecord = computed(() => this.currentPage() * this.pageSize());
    lastRecord = computed(() => Math.min(this.firstRecord() + this.pageSize(), this.totalRecords()));

    allSelected = computed(() => {
        const displayed = this.sortedClients();
        const set = this.selectedClientsSet();
        return displayed.length > 0 && displayed.every(c => c.id && set.has(c.id));
    });

    get selectedClients(): ClientDto[] {
        const set = this.selectedClientsSet();
        return this.clientes().filter(c => c.id && set.has(c.id));
    }

    getActiveClientsCount(): number {
        return this.clientes().filter((client) => client.is_active).length;
    }

    getContactableClientsCount(): number {
        return this.clientes().filter((client) => !!client.email || !!client.phone).length;
    }

    getClientsNarrative(): string {
        const total = this.clientes().length;
        if (!total) {
            return 'Aún no hay clientes registrados en el CRM.';
        }

        return `${this.getActiveClientsCount()} de ${total} clientes siguen activos y ${this.getContactableClientsCount()} tienen un medio de contacto disponible para recordatorios o promociones.`;
    }

    getRecentClients(): ClientDto[] {
        return [...this.clientes()]
            .sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime())
            .slice(0, 3);
    }

    getFeaturedClient(): ClientDto | null {
        const contactable = this.clientes().find((client) => client.is_active && (!!client.phone || !!client.email));
        return contactable || this.clientes()[0] || null;
    }

    getClientContactLabel(client: ClientDto): string {
        if (client.phone) return client.phone;
        if (client.email) return client.email;
        return 'Sin contacto registrado';
    }

    // Utility function to normalize API responses
    private normalizeArray<T>(response: any): T[] {
        if (!response) return [];
        if (Array.isArray(response)) return response;
        if (response.results && Array.isArray(response.results)) return response.results;
        return [];
    }

    // Adaptador Backend → Frontend DTO
    private mapBackendToClientDto(backendClient: any): ClientDto {
        return {
            id: backendClient.id,
            full_name: backendClient.full_name,
            email: backendClient.email,
            phone: backendClient.phone,
            address: backendClient.address,
            birthday: backendClient.birthday,
            gender: backendClient.gender,
            notes: backendClient.notes,
            is_active: backendClient.is_active,
            branch: backendClient.branch ?? null,
            created_at: backendClient.created_at,
            updated_at: backendClient.updated_at
        };
    }

    get generoOptions() {
        return [
            { label: this.t('clients.form_gender_m'), value: 'M' },
            { label: this.t('clients.form_gender_f'), value: 'F' },
            { label: this.t('clients.form_gender_o'), value: 'O' }
        ];
    }

    formulario: FormGroup = this.fb.group({
        full_name: ['', [Validators.required, Validators.maxLength(100)]],
        email: ['', [Validators.email]],
        phone: [''],
        address: [''],
        birthday: [null],
        gender: [''],
        notes: [''],
        is_active: [true],
        branch: [null]
    }, { validators: this.contactRequiredValidator });

    ngOnInit() {
        this.canAccessMultiLocation = this.planAccessService.canAccessFeature('multi_location');
        if (this.canAccessMultiLocation) {
            this.branchService.loadBranches();
        }
        this.cargarClientes();
    }

    async cargarClientes() {
        if (this.cargando()) return;
        this.cargando.set(true);
        try {
            const params: any = {};
            if (this.canAccessMultiLocation && this.branchService.activeBranchId()) {
                params.branch = this.branchService.activeBranchId();
            }
            const response = await firstValueFrom(this.clientService.getClients(params));
            
            const clientes = this.normalizeArray<any>(response);
            const clientesNormalizados = clientes.map((cliente: any) => this.mapBackendToClientDto(cliente));
            
            this.clientes.set(clientesNormalizados);

        } catch (error) {
            if (!environment.production) {
                
            }
            this.messageService.add({
                severity: 'error',
                summary: this.t('common.error'),
                detail: this.t('clients.load_error')
            });
        } finally {
            this.cargando.set(false);
        }
    }

    abrirDialogo() {
        this.clienteSeleccionado = null;
        this.formulario.reset({
            full_name: '',
            email: '',
            phone: '',
            address: '',
            birthday: null,
            gender: '',
            notes: '',
            is_active: true,
            branch: this.canAccessMultiLocation ? this.branchService.activeBranchId() : null
        });
        this.mostrarDialogo = true;
    }

    editarCliente(cliente: ClientDto) {
        this.clienteSeleccionado = cliente;
        this.formulario.patchValue({
            full_name: cliente.full_name,
            email: cliente.email,
            phone: cliente.phone || '',
            address: cliente.address || '',
            birthday: this.parseDateOnly(cliente.birthday),
            gender: cliente.gender || '',
            notes: cliente.notes || '',
            is_active: cliente.is_active,
            branch: cliente.branch ?? null
        });
        this.mostrarDialogo = true;
    }

    async guardarCliente() {
        if (this.formulario.invalid) {
            this.formulario.markAllAsTouched();
            return;
        }

        this.guardando.set(true);
        try {
            const clienteData: CreateClientDto | UpdateClientDto = this.buildClientPayload();

            // Formatear fecha de nacimiento - el backend espera 'birthday'
            if (clienteData.birthday) {
                clienteData.birthday = this.formatDateOnly(clienteData.birthday as any);
            }

            if (this.clienteSeleccionado?.id) {
                await firstValueFrom(this.clientService.updateClient(this.clienteSeleccionado.id, clienteData));
                this.messageService.add({
                    severity: 'success',
                    summary: this.t('common.success'),
                    detail: this.t('clients.save_success')
                });
            } else {
                await firstValueFrom(this.clientService.createClient(clienteData));
                this.messageService.add({
                    severity: 'success',
                    summary: this.t('common.success'),
                    detail: this.t('clients.save_success')
                });
            }

            this.cerrarDialogo();
            this.cargarClientes();
        } catch (error: any) {
            if (!environment.production) {
                
            }
            this.messageService.add({
                severity: 'error',
                summary: this.t('common.error'),
                detail: this.getClientSaveErrorMessage(error)
            });
        } finally {
            this.guardando.set(false);
        }
    }

    private buildClientPayload(): CreateClientDto | UpdateClientDto {
        const rawValue = this.formulario.getRawValue();

        return {
            full_name: rawValue.full_name?.trim() || '',
            email: rawValue.email?.trim() || '',
            phone: rawValue.phone?.trim() || '',
            address: rawValue.address?.trim() || '',
            birthday: rawValue.birthday || undefined,
            gender: rawValue.gender || undefined,
            notes: rawValue.notes?.trim() || '',
            is_active: !!rawValue.is_active,
            branch: rawValue.branch ?? null
        };
    }

    getBranchName(branchId: number | null | undefined): string {
        if (!branchId || !this.canAccessMultiLocation) return '—';
        const branch = this.branchService.branches().find(b => b.id === branchId);
        return branch?.name || '—';
    }

    private getClientSaveErrorMessage(error: any): string {
        const payload = error?.error;

        if (!payload) {
            return this.t('clients.save_error');
        }

        if (typeof payload.detail === 'string' && payload.detail.trim()) {
            return payload.detail;
        }

        if (typeof payload === 'string' && payload.trim()) {
            return payload;
        }

        if (Array.isArray(payload)) {
            const joined = payload
                .map((item) => this.normalizeBackendErrorValue(item))
                .filter(Boolean)
                .join(' ');
            return joined || 'Error al guardar el cliente';
        }

        if (typeof payload === 'object') {
            const fieldErrors = Object.entries(payload)
                .map(([field, value]) => {
                    const normalized = this.normalizeBackendErrorValue(value);
                    if (!normalized) return '';
                    return field === 'non_field_errors' ? normalized : `${field}: ${normalized}`;
                })
                .filter(Boolean)
                .join(' | ');

            if (fieldErrors) {
                return fieldErrors;
            }
        }

        return this.t('clients.save_error');
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

    confirmarEliminar(cliente: ClientDto) {
        this.confirmationService.confirm({
            message: this.t('clients.delete_confirm_msg').replace('{name}', cliente.full_name), // ✅ Normalizado
            header: this.t('clients.delete_confirm_title'),
            icon: 'pi pi-exclamation-triangle',
            acceptLabel: this.t('clients.delete_confirm_accept'),
            rejectLabel: this.t('appointments.cancelar'),
            accept: () => this.eliminarCliente(cliente)
        });
    }

    async eliminarCliente(cliente: ClientDto) {
        try {
            await firstValueFrom(this.clientService.deleteClient(cliente.id));
            this.messageService.add({
                severity: 'success',
                summary: this.t('common.success'),
                detail: this.t('clients.delete_success')
            });
            this.cargarClientes();
        } catch (error: any) {
            if (!environment.production) {
                
            }
            this.messageService.add({
                severity: 'error',
                summary: this.t('common.error'),
                detail: error?.error?.detail || this.t('clients.delete_error')
            });
        }
    }

    formatearFecha(cliente: any): string {
        const fecha = this.parseDateOnly(cliente.birthday);
        if (!fecha) return this.t('clients.date_not_specified');
        try {
            return fecha.toLocaleDateString(this.localeService.getCurrentAppLocale());
        } catch {
            return this.t('clients.date_not_specified');
        }
    }

    getGenderSeverity(gender: string): 'success' | 'info' | 'warn' | 'secondary' {
        switch (gender) {
            case 'M': return 'info';
            case 'F': return 'success';
            case 'O': return 'warn';
            default: return 'secondary';
        }
    }

    cerrarDialogo() {
        this.mostrarDialogo = false;
        this.clienteSeleccionado = null;
        this.formulario.reset();
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

    isSelected(cliente: ClientDto): boolean {
        return cliente.id ? this.selectedClientsSet().has(cliente.id) : false;
    }

    toggleSelection(cliente: ClientDto) {
        if (!cliente.id) return;
        const set = new Set(this.selectedClientsSet());
        if (set.has(cliente.id)) {
            set.delete(cliente.id);
        } else {
            set.add(cliente.id);
        }
        this.selectedClientsSet.set(set);
    }

    toggleSelectAll(event: Event) {
        const checked = (event.target as HTMLInputElement).checked;
        const set = new Set(this.selectedClientsSet());
        if (checked) {
            this.sortedClients().forEach(c => { if (c.id) set.add(c.id); });
        } else {
            this.sortedClients().forEach(c => { if (c.id) set.delete(c.id); });
        }
        this.selectedClientsSet.set(set);
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

    private contactRequiredValidator(control: AbstractControl): ValidationErrors | null {
        const email = control.get('email')?.value?.toString().trim();
        const phone = control.get('phone')?.value?.toString().trim();

        return email || phone ? null : { contactRequired: true };
    }

    // Funciones para sistema de cumpleaños
    esCumpleanosHoy(cliente: any): boolean {
        const cumple = this.parseDateOnly(cliente.birthday);
        if (!cumple) return false;
        const hoy = new Date();
        return hoy.getDate() === cumple.getDate() && hoy.getMonth() === cumple.getMonth();
    }

    esCumpleanosEsteMes(cliente: any): boolean {
        const cumple = this.parseDateOnly(cliente.birthday);
        if (!cumple) return false;
        const hoy = new Date();
        return hoy.getMonth() === cumple.getMonth();
    }

    calcularEdad(cliente: any): number | null {
        const cumple = this.parseDateOnly(cliente.birthday);
        if (!cumple) return null;
        const hoy = new Date();
        let edad = hoy.getFullYear() - cumple.getFullYear();
        const mesActual = hoy.getMonth();
        const mesCumple = cumple.getMonth();
        
        if (mesActual < mesCumple || (mesActual === mesCumple && hoy.getDate() < cumple.getDate())) {
            edad--;
        }
        return edad;
    }

    private parseDateOnly(value: unknown): Date | null {
        if (!value) return null;
        if (value instanceof Date) return value;
        if (typeof value === 'string') {
            const parts = value.split('-');
            if (parts.length === 3) {
                const year = Number(parts[0]);
                const month = Number(parts[1]);
                const day = Number(parts[2]);
                if (Number.isFinite(year) && Number.isFinite(month) && Number.isFinite(day)) {
                    return new Date(year, month - 1, day);
                }
            }
            const parsed = new Date(value);
            return Number.isNaN(parsed.getTime()) ? null : parsed;
        }
        return null;
    }

    private formatDateOnly(value: Date | string): string {
        const date = value instanceof Date ? value : this.parseDateOnly(value);
        if (!date) return '';
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
}
