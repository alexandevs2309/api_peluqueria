import { Component, DestroyRef, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MessageService } from 'primeng/api';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { ButtonModule } from 'primeng/button';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ToastModule } from 'primeng/toast';
import { DialogModule } from 'primeng/dialog';
import { SelectModule } from 'primeng/select';
import { TextareaModule } from 'primeng/textarea';
import { TenantService } from '../../core/services/tenant/tenant.service';
import { ActivityLogService } from '../../core/services/activity-log/activity-log.service';
import { BillingService } from '../../core/services/billing.service';
import { SupportTicketService, SupportTicket } from '../../core/services/support/support-ticket.service';
import { getSubscriptionPlanLabel } from '../../core/utils/subscription-plan-label';

@Component({
    selector: 'app-admin-support',
    standalone: true,
    imports: [FormsModule, CardModule, InputTextModule, ButtonModule, TableModule, TagModule, ToastModule, DialogModule, SelectModule, TextareaModule, DatePipe],
    providers: [MessageService],
    template: `
        <p-toast></p-toast>

        <!-- Header -->
        <section class="mb-8 overflow-hidden rounded-[2rem] border border-surface-200/70 bg-surface-0 shadow-[0_24px_80px_-42px_rgba(15,23,42,0.45)] dark:border-surface-800 dark:bg-surface-900">
            <div class="relative overflow-hidden px-8 py-8 lg:px-10">
                <div class="hero-gradient"></div>
                <div class="relative grid gap-8 lg:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.9fr)]">
                    <div>
                        <div class="mb-4 inline-flex items-center gap-2 rounded-full border border-surface-200 bg-surface-50/90 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.24em] text-surface-600 dark:border-surface-700 dark:bg-surface-800/80 dark:text-surface-300">
                            <i class="pi pi-life-ring text-primary"></i>
                            Panel de Soporte
                        </div>
                        <h1 class="text-3xl font-semibold tracking-tight text-surface-950 dark:text-surface-0 lg:text-4xl">Soporte al Cliente</h1>
                        <p class="mt-3 max-w-2xl text-base leading-7 text-surface-600 dark:text-surface-300">
                            Gestiona los tickets de soporte de tus clientes y accede al diagnóstico técnico por tenant.
                        </p>
                    </div>
                    <div class="rounded-3xl border border-surface-200 bg-white/80 p-5 shadow-sm backdrop-blur dark:border-surface-700 dark:bg-surface-800/80">
                        <div class="text-xs font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">Resumen</div>
                        <div class="mt-4 grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
                            <div class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 dark:border-amber-900/60 dark:bg-amber-900/10">
                                <div class="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700 dark:text-amber-300">Abiertos</div>
                                <div class="mt-2 text-2xl font-semibold text-amber-900 dark:text-amber-100">{{ openTicketsCount() }}</div>
                            </div>
                            <div class="rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 dark:border-blue-900/60 dark:bg-blue-900/10">
                                <div class="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700 dark:text-blue-300">En Progreso</div>
                                <div class="mt-2 text-2xl font-semibold text-blue-900 dark:text-blue-100">{{ inProgressCount() }}</div>
                            </div>
                            <div class="rounded-2xl border border-surface-200 bg-surface-50 px-4 py-3 dark:border-surface-700 dark:bg-surface-800">
                                <div class="text-xs font-semibold uppercase tracking-[0.18em] text-surface-500 dark:text-surface-400">Tenants</div>
                                <div class="mt-2 text-2xl font-semibold text-surface-950 dark:text-surface-0">{{ tenants().length }}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Tabs -->
        <div class="flex gap-1 mb-6 bg-surface-100 dark:bg-surface-800 rounded-2xl p-1 w-fit">
            <button (click)="activeTab = 'tickets'" [class]="tabClass('tickets')">
                <i class="pi pi-ticket mr-2"></i>Tickets de Soporte
                @if (openTicketsCount() > 0) {
                    <span class="ml-2 inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-500 text-white text-[10px] font-bold">{{ openTicketsCount() }}</span>
                }
            </button>
            <button (click)="activeTab = 'diagnostico'; loadTenants()" [class]="tabClass('diagnostico')">
                <i class="pi pi-search-plus mr-2"></i>Diagnóstico Operativo
            </button>
        </div>

        <!-- TAB: TICKETS DE SOPORTE -->
        @if (activeTab === 'tickets') {
            <p-card>
                <ng-template #header>
                    <div class="flex items-center justify-between px-6 pt-5">
                        <span class="text-lg font-semibold text-surface-900 dark:text-surface-0">Todos los tickets</span>
                        <button pButton icon="pi pi-refresh" severity="secondary" [rounded]="true" [text]="true"
                                (click)="loadTickets()" [loading]="loadingTickets()"></button>
                    </div>
                </ng-template>
                <p-table [value]="tickets()" [paginator]="true" [rows]="15" [loading]="loadingTickets()"
                         [tableStyle]="{'min-width':'100%'}" sortField="created_at" [sortOrder]="-1">
                    <ng-template #header>
                        <tr>
                            <th pSortableColumn="subject">Asunto <p-sortIcon field="subject"/></th>
                            <th>Negocio</th>
                            <th>Contacto</th>
                            <th pSortableColumn="priority">Prioridad <p-sortIcon field="priority"/></th>
                            <th pSortableColumn="status">Estado <p-sortIcon field="status"/></th>
                            <th pSortableColumn="created_at">Fecha <p-sortIcon field="created_at"/></th>
                            <th>Acciones</th>
                        </tr>
                    </ng-template>
                    <ng-template #body let-ticket>
                        <tr class="cursor-pointer hover:bg-surface-50 dark:hover:bg-surface-800 transition-colors"
                            (click)="openTicketDetail(ticket)">
                            <td>
                                <div class="font-medium text-surface-900 dark:text-surface-0 max-w-[220px] truncate">{{ ticket.subject }}</div>
                            </td>
                            <td>
                                <div class="text-sm font-medium">{{ ticket.tenant_name || '—' }}</div>
                            </td>
                            <td>
                                <div class="text-sm text-surface-500">{{ ticket.created_by_name || ticket.created_by_email }}</div>
                                <div class="text-xs text-surface-400">{{ ticket.created_by_email }}</div>
                            </td>
                            <td>
                                <p-tag [value]="priorityLabel(ticket.priority)" [severity]="prioritySeverity(ticket.priority)" />
                            </td>
                            <td>
                                <p-tag [value]="statusLabel(ticket.status)" [severity]="statusSeverity(ticket.status)" />
                            </td>
                            <td>
                                <span class="text-sm text-surface-500">{{ ticket.created_at | date:'dd/MM/yy HH:mm' }}</span>
                            </td>
                            <td (click)="$event.stopPropagation()">
                                <div class="flex gap-1">
                                    <button pButton icon="pi pi-eye" severity="secondary" size="small" [text]="true" [rounded]="true"
                                            (click)="openTicketDetail(ticket)" title="Ver detalle"></button>
                                    @if (ticket.status !== 'closed' && ticket.status !== 'resolved') {
                                        <button pButton icon="pi pi-check-circle" severity="success" size="small" [text]="true" [rounded]="true"
                                                (click)="resolveTicket(ticket)" title="Marcar como Resuelto"></button>
                                    }
                                </div>
                            </td>
                        </tr>
                    </ng-template>
                    <ng-template #emptymessage>
                        <tr>
                            <td colspan="7">
                                <div class="text-center py-16">
                                    <i class="pi pi-ticket text-5xl text-surface-300 dark:text-surface-600 mb-4 block"></i>
                                    <p class="text-surface-500">No hay tickets de soporte todavía.</p>
                                </div>
                            </td>
                        </tr>
                    </ng-template>
                </p-table>
            </p-card>

            <!-- Ticket Detail Dialog -->
            @if (selectedTicket()) {
                <p-dialog [header]="'Ticket #' + selectedTicket()!.id" [(visible)]="showTicketDialog"
                          [modal]="true" [style]="{width:'640px'}" [breakpoints]="{'960px':'80vw','640px':'100vw'}"
                          (onHide)="selectedTicket.set(null)">
                    <div class="space-y-4">
                        <div class="flex flex-wrap gap-2">
                            <p-tag [value]="statusLabel(selectedTicket()!.status)" [severity]="statusSeverity(selectedTicket()!.status)" />
                            <p-tag [value]="priorityLabel(selectedTicket()!.priority)" [severity]="prioritySeverity(selectedTicket()!.priority)" />
                        </div>
                        <div class="grid grid-cols-2 gap-3 text-sm">
                            <div class="rounded-xl bg-surface-50 dark:bg-surface-800 p-3">
                                <div class="text-xs font-semibold uppercase tracking-wider text-surface-400 mb-1">Negocio</div>
                                <div class="font-medium">{{ selectedTicket()!.tenant_name || '—' }}</div>
                            </div>
                            <div class="rounded-xl bg-surface-50 dark:bg-surface-800 p-3">
                                <div class="text-xs font-semibold uppercase tracking-wider text-surface-400 mb-1">Creado por</div>
                                <div class="font-medium">{{ selectedTicket()!.created_by_name }}</div>
                                <div class="text-xs text-surface-400">{{ selectedTicket()!.created_by_email }}</div>
                            </div>
                        </div>
                        <div class="rounded-xl border border-surface-200 dark:border-surface-700 p-4">
                            <div class="text-xs font-semibold uppercase tracking-wider text-surface-400 mb-2">Descripción</div>
                            <p class="text-sm text-surface-700 dark:text-surface-300 whitespace-pre-wrap leading-relaxed">{{ selectedTicket()!.description }}</p>
                        </div>
                        <div class="text-xs text-surface-400">
                            Creado: {{ selectedTicket()!.created_at | date:'medium' }} &nbsp;·&nbsp;
                            Actualizado: {{ selectedTicket()!.updated_at | date:'medium' }}
                        </div>
                        <div class="border-t border-surface-200 dark:border-surface-700 pt-4">
                            <div class="text-xs font-semibold uppercase tracking-wider text-surface-400 mb-2">Cambiar Estado</div>
                            <div class="flex gap-2 flex-wrap">
                                @for (opt of statusOptions; track opt.value) {
                                    <button pButton [label]="opt.label" size="small"
                                            [severity]="selectedTicket()!.status === opt.value ? 'primary' : 'secondary'"
                                            [disabled]="selectedTicket()!.status === opt.value || savingStatus()"
                                            (click)="changeTicketStatus(selectedTicket()!, opt.value)"></button>
                                }
                            </div>
                        </div>

                        <!-- Admin Reply Section -->
                        @if (selectedTicket()!.admin_reply) {
                            <div class="rounded-xl border border-green-200 bg-green-50 dark:border-green-900/60 dark:bg-green-900/10 p-4">
                                <div class="text-xs font-semibold uppercase tracking-wider text-green-700 dark:text-green-300 mb-2">
                                    <i class="pi pi-check-circle mr-1"></i>Respuesta enviada
                                    @if (selectedTicket()!.replied_at) {
                                        <span class="font-normal text-green-500 ml-2">{{ selectedTicket()!.replied_at | date:'dd/MM/yy HH:mm' }}</span>
                                    }
                                </div>
                                <p class="text-sm text-green-800 dark:text-green-200 whitespace-pre-wrap leading-relaxed">{{ selectedTicket()!.admin_reply }}</p>
                            </div>
                        }
                        <div class="border-t border-surface-200 dark:border-surface-700 pt-4">
                            <div class="text-xs font-semibold uppercase tracking-wider text-surface-400 mb-2">
                                <i class="pi pi-send mr-1"></i>{{ selectedTicket()!.admin_reply ? 'Actualizar respuesta' : 'Escribir respuesta al cliente' }}
                            </div>
                            <textarea pTextarea [(ngModel)]="replyText" rows="4"
                                      placeholder="Escribe la solución o respuesta para el cliente..."
                                      class="w-full text-sm"></textarea>
                            <div class="flex justify-end mt-2">
                                <button pButton label="Enviar respuesta" icon="pi pi-send" severity="success"
                                        [loading]="savingReply()"
                                        [disabled]="!replyText.trim() || savingReply()"
                                        (click)="sendReply(selectedTicket()!)"></button>
                            </div>
                        </div>
                    </div>
                </p-dialog>
            }
        }

        <!-- TAB: DIAGNÓSTICO OPERATIVO -->
        @if (activeTab === 'diagnostico') {
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <p-card>
                    <div class="text-sm text-gray-500">Tenants</div>
                    <div class="text-2xl font-bold">{{ tenants().length }}</div>
                </p-card>
                <p-card>
                    <div class="text-sm text-gray-500">Activos</div>
                    <div class="text-2xl font-bold text-green-600">{{ activeCount() }}</div>
                </p-card>
                <p-card>
                    <div class="text-sm text-gray-500">Suspendidos</div>
                    <div class="text-2xl font-bold text-red-600">{{ suspendedCount() }}</div>
                </p-card>
                <p-card>
                    <div class="text-sm text-gray-500">Trials</div>
                    <div class="text-2xl font-bold text-amber-600">{{ trialCount() }}</div>
                </p-card>
            </div>

            <p-card header="Búsqueda de Tenant" styleClass="mb-6">
                <div class="flex gap-2 mb-4">
                    <input pInputText type="text" [(ngModel)]="searchTerm" (input)="applyFilter()"
                           placeholder="Buscar por nombre, subdominio, email o plan" class="w-full" />
                    <p-button icon="pi pi-refresh" label="Refrescar" (onClick)="loadTenants()" [loading]="loading()" />
                </div>
                <p-table [value]="filteredTenants()" [paginator]="true" [rows]="10"
                         [tableStyle]="{'min-width':'100%'}" [loading]="loading()">
                    <ng-template #header>
                        <tr>
                            <th>Tenant</th>
                            <th>Plan</th>
                            <th>Suscripción</th>
                            <th>Estado</th>
                            <th>Contacto</th>
                            <th>Acciones</th>
                        </tr>
                    </ng-template>
                    <ng-template #body let-tenant>
                        <tr>
                            <td>
                                <div class="font-semibold">{{ tenant.name }}</div>
                                <div class="text-xs text-gray-500">{{ tenant.subdomain || '-' }}</div>
                            </td>
                            <td>{{ getTenantPlanDisplayName(tenant) }}</td>
                            <td>
                                <p-tag [value]="tenant.subscription_status || 'trial'" [severity]="getSubscriptionSeverity(tenant.subscription_status)" />
                            </td>
                            <td>
                                <p-tag [value]="tenant.is_active ? 'Activo' : 'Inactivo'" [severity]="tenant.is_active ? 'success' : 'danger'" />
                            </td>
                            <td>{{ tenant.contact_email || tenant.owner_email || '-' }}</td>
                            <td>
                                <div class="flex gap-2">
                                    <p-button icon="pi pi-search" label="Inspeccionar" size="small" (onClick)="inspectTenant(tenant)" />
                                    <p-button icon="pi pi-arrow-right" label="Abrir" severity="secondary" size="small" (onClick)="openTenantDetail(tenant)" />
                                </div>
                            </td>
                        </tr>
                    </ng-template>
                    <ng-template #emptymessage>
                        <tr>
                            <td colspan="6" class="text-center text-sm text-gray-500 py-6">
                                No hay tenants que coincidan con la búsqueda.
                            </td>
                        </tr>
                    </ng-template>
                </p-table>
            </p-card>

            @if (selectedTenant()) {
                <p-card [header]="'Diagnóstico Rápido: ' + selectedTenant().name">
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                        <div class="p-3 rounded bg-gray-50 dark:bg-gray-800">
                            <div class="text-sm text-gray-500">Facturas vencidas</div>
                            <div class="text-xl font-bold text-red-600">{{ supportStats().overdue }}</div>
                        </div>
                        <div class="p-3 rounded bg-gray-50 dark:bg-gray-800">
                            <div class="text-sm text-gray-500">Pagos fallidos</div>
                            <div class="text-xl font-bold text-orange-600">{{ supportStats().failed }}</div>
                        </div>
                        <div class="p-3 rounded bg-gray-50 dark:bg-gray-800">
                            <div class="text-sm text-gray-500">Errores técnicos (20 logs)</div>
                            <div class="text-xl font-bold text-rose-600">{{ supportStats().errors }}</div>
                        </div>
                    </div>
                    <p-table [value]="recentLogs()" [tableStyle]="{'min-width':'100%'}">
                        <ng-template #header>
                            <tr>
                                <th>Fecha</th>
                                <th>Acción</th>
                                <th>Fuente</th>
                                <th>Descripción</th>
                            </tr>
                        </ng-template>
                        <ng-template #body let-log>
                            <tr>
                                <td>{{ log.timestamp | date:'dd/MM/yyyy HH:mm' }}</td>
                                <td><p-tag [value]="log.action" [severity]="getLogSeverity(log.action)" /></td>
                                <td>{{ log.source || '-' }}</td>
                                <td>{{ log.description || '-' }}</td>
                            </tr>
                        </ng-template>
                        <ng-template #emptymessage>
                            <tr>
                                <td colspan="4" class="text-center text-sm text-gray-500 py-6">
                                    No hay registros recientes para este tenant.
                                </td>
                            </tr>
                        </ng-template>
                    </p-table>
                </p-card>
            }
        }
    `,
    styles: [`
        :host { display: block; }
    `]
})
export class AdminSupport implements OnInit {
    activeTab: 'tickets' | 'diagnostico' = 'tickets';

    // Ticket management
    tickets = signal<SupportTicket[]>([]);
    loadingTickets = signal(false);
    savingStatus = signal(false);
    savingReply = signal(false);
    selectedTicket = signal<SupportTicket | null>(null);
    showTicketDialog = false;
    replyText = '';

    readonly statusOptions = [
        { label: 'Abierto', value: 'open' },
        { label: 'En Progreso', value: 'in_progress' },
        { label: 'Resuelto', value: 'resolved' },
        { label: 'Cerrado', value: 'closed' },
    ];

    // Diagnostic mode
    tenants = signal<any[]>([]);
    filteredTenants = signal<any[]>([]);
    selectedTenant = signal<any | null>(null);
    recentLogs = signal<any[]>([]);
    supportStats = signal({ overdue: 0, failed: 0, errors: 0 });
    loading = signal(false);
    searchTerm = '';

    constructor(
        private tenantService: TenantService,
        private activityLogService: ActivityLogService,
        private billingService: BillingService,
        private router: Router,
        private messageService: MessageService,
        private supportTicketService: SupportTicketService,
        private destroyRef: DestroyRef
    ) {}

    ngOnInit(): void {
        this.loadTickets();
    }

    // ─── Tickets ────────────────────────────────────────────────────────────────

    loadTickets(): void {
        this.loadingTickets.set(true);
        this.supportTicketService.getMyTickets()
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe({
                next: (data: any) => {
                    const list: SupportTicket[] = Array.isArray(data) ? data : data?.results || [];
                    this.tickets.set(list.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));
                },
                error: () => this.showError('No se pudieron cargar los tickets'),
                complete: () => this.loadingTickets.set(false),
            });
    }

    openTicketDetail(ticket: SupportTicket): void {
        this.selectedTicket.set({ ...ticket });
        this.replyText = ticket.admin_reply || '';
        this.showTicketDialog = true;
    }

    sendReply(ticket: SupportTicket): void {
        if (!this.replyText.trim() || this.savingReply()) return;
        this.savingReply.set(true);
        this.supportTicketService.replyTicket(ticket.id, this.replyText.trim())
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe({
                next: (updated) => {
                    this.savingReply.set(false);
                    this.selectedTicket.set(updated);
                    this.tickets.update(list => list.map(t => t.id === updated.id ? updated : t));
                    this.messageService.add({ severity: 'success', summary: '✅ Respuesta enviada', detail: 'El cliente recibirá un email con tu respuesta.', life: 5000 });
                },
                error: () => { this.savingReply.set(false); this.showError('No se pudo enviar la respuesta'); },
            });
    }

    changeTicketStatus(ticket: SupportTicket, newStatus: string): void {
        if (this.savingStatus()) return;
        this.savingStatus.set(true);

        if (newStatus === 'closed') {
            this.supportTicketService.closeTicket(ticket.id)
                .pipe(takeUntilDestroyed(this.destroyRef))
                .subscribe({
                    next: () => this.onStatusChanged(ticket, newStatus),
                    error: () => { this.showError('No se pudo cerrar el ticket'); this.savingStatus.set(false); },
                });
        } else {
            this.supportTicketService.updateTicketStatus(ticket.id, newStatus)
                .pipe(takeUntilDestroyed(this.destroyRef))
                .subscribe({
                    next: (updated) => this.onStatusChanged(updated, newStatus),
                    error: () => { this.showError('No se pudo actualizar el estado'); this.savingStatus.set(false); },
                });
        }
    }

    private onStatusChanged(ticket: any, newStatus: string): void {
        this.savingStatus.set(false);
        this.selectedTicket.set({ ...ticket, status: newStatus });
        this.tickets.update(list => list.map(t => t.id === ticket.id ? { ...t, status: newStatus as SupportTicket['status'] } : t));
        this.messageService.add({ severity: 'success', summary: 'Estado actualizado', detail: `Ticket marcado como "${this.statusLabel(newStatus)}"` });
    }

    resolveTicket(ticket: SupportTicket): void {
        this.changeTicketStatus(ticket, 'resolved');
    }

    openTicketsCount(): number {
        return this.tickets().filter(t => t.status === 'open').length;
    }

    inProgressCount(): number {
        return this.tickets().filter(t => t.status === 'in_progress').length;
    }

    // ─── Diagnostic mode ────────────────────────────────────────────────────────

    loadTenants(): void {
        if (this.tenants().length > 0 && !this.loading()) return;
        this.loading.set(true);
        this.tenantService.getTenants().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (data: any) => {
                const list = Array.isArray(data) ? data : data?.results || [];
                this.tenants.set(list);
                this.filteredTenants.set(list);
                this.loading.set(false);
            },
            error: () => {
                this.loading.set(false);
                this.showError('No se pudieron cargar los tenants');
            }
        });
    }

    applyFilter(): void {
        const query = (this.searchTerm || '').trim().toLowerCase();
        if (!query) { this.filteredTenants.set(this.tenants()); return; }
        this.filteredTenants.set(this.tenants().filter(t => {
            return [t?.name, t?.subdomain, t?.contact_email, t?.owner_email, this.getTenantPlanDisplayName(t)]
                .filter(Boolean).join(' ').toLowerCase().includes(query);
        }));
    }

    inspectTenant(tenant: any): void {
        this.selectedTenant.set(tenant);
        forkJoin({
            logs: this.activityLogService.getAuditLogs({ tenant: tenant.id, page_size: 20 }).pipe(catchError(() => of({ results: [] }))),
            invoices: this.billingService.getInvoices({ tenant: tenant.id, page_size: 500 }).pipe(catchError(() => of([]))),
        }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: ({ logs, invoices }) => {
                const logsArr = (logs as any)?.results || [];
                const invArr = Array.isArray(invoices) ? invoices : (invoices as any)?.results || [];
                this.recentLogs.set(logsArr);
                this.supportStats.set({
                    overdue: invArr.filter((i: any) => i?.status === 'pending' && i?.due_date && new Date(i.due_date) < new Date()).length,
                    failed: invArr.filter((i: any) => i?.status === 'failed').length,
                    errors: logsArr.filter((l: any) => String(l?.action || '').includes('ERROR')).length,
                });
            },
            error: () => this.showError('No se pudo cargar el diagnóstico del tenant'),
        });
    }

    openTenantDetail(tenant: any): void {
        if (tenant?.id) this.router.navigate(['/admin/tenants', tenant.id]);
    }

    getTenantPlanDisplayName(tenant: any): string {
        return getSubscriptionPlanLabel(tenant?.subscription_plan?.display_name, tenant?.subscription_plan?.name, tenant?.plan_type);
    }

    activeCount(): number { return this.tenants().filter(t => t?.is_active).length; }
    suspendedCount(): number { return this.tenants().filter(t => t?.subscription_status === 'suspended').length; }
    trialCount(): number { return this.tenants().filter(t => t?.subscription_status === 'trial').length; }

    // ─── Helpers ────────────────────────────────────────────────────────────────

    tabClass(tab: string): string {
        const base = 'px-5 py-2.5 rounded-xl text-sm font-semibold transition-all flex items-center';
        return tab === this.activeTab
            ? `${base} bg-surface-0 dark:bg-surface-700 shadow-sm text-surface-900 dark:text-surface-0`
            : `${base} text-surface-500 dark:text-surface-400 hover:text-surface-700 dark:hover:text-surface-200`;
    }

    statusLabel(s: string): string {
        return ({ open: 'Abierto', in_progress: 'En Progreso', resolved: 'Resuelto', closed: 'Cerrado' } as any)[s] || s;
    }

    statusSeverity(s: string): 'warn' | 'info' | 'success' | 'secondary' {
        return ({ open: 'warn', in_progress: 'info', resolved: 'success', closed: 'secondary' } as any)[s] || 'info';
    }

    priorityLabel(p: string): string {
        return ({ low: 'Baja', normal: 'Normal', high: 'Alta', urgent: 'Urgente' } as any)[p] || p;
    }

    prioritySeverity(p: string): 'success' | 'info' | 'warn' | 'danger' {
        return ({ low: 'success', normal: 'info', high: 'warn', urgent: 'danger' } as any)[p] || 'info';
    }

    getSubscriptionSeverity(status?: string): 'success' | 'info' | 'warn' | 'danger' | 'secondary' | 'contrast' {
        if (status === 'active') return 'success';
        if (status === 'trial') return 'info';
        if (status === 'suspended') return 'danger';
        return 'warn';
    }

    getLogSeverity(action?: string): 'success' | 'info' | 'warn' | 'danger' | 'secondary' | 'contrast' {
        return String(action || '').includes('ERROR') ? 'danger' : 'info';
    }

    private showError(detail: string): void {
        this.messageService.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    }
}
