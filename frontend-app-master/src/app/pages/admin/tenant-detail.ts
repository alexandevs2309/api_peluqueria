import { Component, DestroyRef, OnInit, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CurrencyPipe, DatePipe, JsonPipe } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { ToastModule } from 'primeng/toast';
import { DialogModule } from 'primeng/dialog';
import { TextareaModule } from 'primeng/textarea';
import { CardModule } from 'primeng/card';
import { SelectModule } from 'primeng/select';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { TenantService } from '../../core/services/tenant/tenant.service';
import { SubscriptionService } from '../../core/services/subscription/subscription.service';
import { ActivityLogService } from '../../core/services/activity-log/activity-log.service';
import { BillingService } from '../../core/services/billing.service';
import { AdminErrorLogService } from '../../core/services/admin-error-log.service';

interface DiagnosticFinding {
    severity: 'critical' | 'warning' | 'info';
    title: string;
    detail: string;
    action: string;
}

interface PlanChangeBlockInfo {
    title: string;
    message: string;
}

@Component({
    selector: 'app-tenant-detail',
    standalone: true,
    imports: [
        CurrencyPipe,
        FormsModule,
        ButtonModule,
        ToastModule,
        DialogModule,
        TextareaModule,
        CardModule,
        SelectModule,
        TableModule,
        TagModule,
        DatePipe,
        JsonPipe
    ],
    providers: [MessageService],
    template: `
        <p-toast></p-toast>

        <div class="flex items-center justify-between mb-6">
            <div>
                <h1 class="text-2xl font-bold m-0">Tenant Command Center</h1>
                <p class="text-gray-500 m-0">Operación, soporte y diagnóstico 360 del cliente</p>
            </div>
            <div class="flex gap-2">
                <p-button icon="pi pi-arrow-left" label="Volver" severity="secondary" (onClick)="goBack()" />
                <p-button icon="pi pi-refresh" label="Refrescar" (onClick)="loadTenantData()" [loading]="loading()" />
            </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-6 gap-4 mb-6">
            <p-card>
                <div class="text-sm text-gray-500">Estado</div>
                <p-tag [value]="tenant()?.is_active ? 'Activo' : 'Inactivo'" [severity]="tenant()?.is_active ? 'success' : 'danger'" />
            </p-card>
            <p-card>
                <div class="text-sm text-gray-500">Suscripción</div>
                <p-tag [value]="tenant()?.subscription_status || 'N/A'" [severity]="getSubscriptionSeverity(tenant()?.subscription_status)" />
            </p-card>
            <p-card>
                <div class="text-sm text-gray-500">Usuarios</div>
                <div class="text-2xl font-bold">{{ users().length }}</div>
            </p-card>
            <p-card>
                <div class="text-sm text-gray-500">Trial End</div>
                <div class="text-lg font-semibold">{{ tenant()?.trial_end_date ? (tenant()?.trial_end_date | date:'dd/MM/yyyy') : '-' }}</div>
            </p-card>
            <p-card>
                <div class="text-sm text-gray-500">Facturas totales</div>
                <div class="text-2xl font-bold text-blue-600">{{ totalInvoicesCount() }}</div>
            </p-card>
            <p-card>
                <div class="text-sm text-gray-500">Facturas pagadas</div>
                <div class="text-2xl font-bold text-green-600">{{ paidInvoicesCount() }}</div>
            </p-card>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <p-card header="Perfil del Tenant">
                <div class="space-y-2">
                    <div><strong>Nombre:</strong> {{ tenant()?.name || '-' }}</div>
                    <div><strong>Subdominio:</strong> {{ tenant()?.subdomain || '-' }}</div>
                    <div><strong>Contacto:</strong> {{ tenant()?.contact_email || '-' }}</div>
                    <div><strong>Plan actual:</strong> {{ getTenantPlanDisplayName() }}</div>
                    <div><strong>Límite comercial:</strong> Usuarios activos {{ formatLimit(tenant()?.max_users) }}</div>
                    <div><strong>Creado:</strong> {{ tenant()?.created_at ? (tenant()?.created_at | date:'dd/MM/yyyy HH:mm') : '-' }}</div>
                </div>
            </p-card>

            <p-card header="Acciones Operativas">
                <div class="flex flex-wrap gap-2 mb-4">
                    <p-button
                        [label]="tenant()?.is_active ? 'Desactivar Tenant' : 'Activar Tenant'"
                        [severity]="tenant()?.is_active ? 'danger' : 'success'"
                        icon="pi pi-power-off"
                        (onClick)="toggleActive()"
                    />
                    <p-button
                        [label]="tenant()?.subscription_status === 'suspended' ? 'Reanudar Suscripción' : 'Suspender Suscripción'"
                        [severity]="tenant()?.subscription_status === 'suspended' ? 'success' : 'warn'"
                        icon="pi pi-pause"
                        (onClick)="toggleSuspension()"
                    />
                </div>

                <div class="flex gap-2 items-end">
                    <div class="grow">
                        <label class="block text-sm mb-2">Cambiar plan del tenant</label>
                        <p-select
                            [(ngModel)]="selectedPlanId"
                            [options]="planOptions()"
                            optionLabel="displayName"
                            optionValue="id"
                            placeholder="Seleccionar plan"
                        />
                    </div>
                    <p-button label="Aplicar" icon="pi pi-check" (onClick)="applyPlanChange()" [disabled]="!canApplyPlanChange()" [loading]="saving()" />
                </div>

                @if (selectedPlanPreview(); as preview) {
                <div class="mt-4 p-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/40">
                    <div class="font-semibold mb-2">Impacto del cambio de plan</div>
                    <div class="text-sm space-y-2">
                        <div><strong>Nuevo plan:</strong> {{ preview.display_name || preview.name || '-' }}</div>
                        <div><strong>Precio:</strong> {{ preview.price | currency:'USD' }}</div>
                        <div><strong>Nuevo límite comercial:</strong> Usuarios activos {{ formatLimit(preview.max_users) }}</div>
                        <div><strong>Uso actual:</strong> Usuarios activos {{ currentUsersCount() }}</div>
                        <div><strong>Sucursales múltiples:</strong> {{ preview.allows_multiple_branches ? 'Sí' : 'No' }}</div>
                        @if (isSelectedPlanCurrent()) {
                            <div class="text-amber-700 dark:text-amber-300">Este tenant ya tiene asignado ese plan.</div>
                        }
                        @if (selectedPlanCreatesUserOverage()) {
                            <div class="text-red-700 dark:text-red-300">Advertencia: el tenant ya supera el límite de usuarios del plan seleccionado.</div>
                        }
                        <div class="text-slate-500 dark:text-slate-400">El cambio actualiza el plan del tenant y sus límites operativos inmediatamente.</div>
                    </div>
                </div>
                }
            </p-card>
        </div>

        <p-card header="Diagnóstico Asistido" styleClass="mb-6">
            @if (diagnostics().length > 0) {
                <div class="space-y-3">
                    @for (finding of diagnostics(); track finding.title) {
                        <div class="p-3 rounded border-l-4" [class]="getDiagnosticClass(finding.severity)">
                            <div class="font-semibold">{{ finding.title }}</div>
                            <div class="text-sm">{{ finding.detail }}</div>
                            <div class="text-xs mt-1 text-gray-600"><strong>Acción sugerida:</strong> {{ finding.action }}</div>
                        </div>
                    }
                </div>
            } @else {
                <div class="text-green-700">No se detectaron hallazgos críticos para este tenant.</div>
            }
        </p-card>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <p-card header="Usuarios del Tenant">
                <p-table [value]="users()" [tableStyle]="{ 'min-width': '100%' }" responsiveLayout="scroll">
                    <ng-template #header>
                        <tr>
                            <th>Email</th>
                            <th>Nombre</th>
                            <th>Rol</th>
                            <th>Estado</th>
                        </tr>
                    </ng-template>
                    <ng-template #body let-user>
                        <tr>
                            <td>{{ user.email }}</td>
                            <td>{{ user.full_name || '-' }}</td>
                            <td>{{ user.role || '-' }}</td>
                            <td>
                                <p-tag [value]="user.is_active ? 'Activo' : 'Inactivo'" [severity]="user.is_active ? 'success' : 'danger'" />
                            </td>
                        </tr>
                    </ng-template>
                </p-table>
            </p-card>

            <p-card header="Suscripción del Tenant">
                <div class="space-y-2">
                    <div><strong>Plan:</strong> {{ tenantSubscription()?.plan?.name || tenantSubscription()?.plan_name || '-' }}</div>
                    <div><strong>Estado:</strong> {{ tenantSubscription()?.status || tenant()?.subscription_status || '-' }}</div>
                    <div><strong>Inicio:</strong> {{ tenantSubscription()?.start_date ? (tenantSubscription()?.start_date | date:'dd/MM/yyyy') : '-' }}</div>
                    <div><strong>Fin:</strong> {{ tenantSubscription()?.end_date ? (tenantSubscription()?.end_date | date:'dd/MM/yyyy') : '-' }}</div>
                </div>
                @if (tenantStats()) {
                    <div class="mt-4">
                        <strong>Stats:</strong>
                        <pre class="text-xs bg-gray-50 dark:bg-gray-800 p-2 rounded mt-2 overflow-auto">{{ tenantStats() | json }}</pre>
                    </div>
                }
            </p-card>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <p-card header="Suscripciones de Usuarios">
                <p-table [value]="userSubscriptions()" [tableStyle]="{ 'min-width': '100%' }" responsiveLayout="scroll">
                    <ng-template #header>
                        <tr>
                            <th>Usuario</th>
                            <th>Plan</th>
                            <th>Estado</th>
                            <th>Inicio</th>
                            <th>Fin</th>
                            <th>Acciones</th>
                        </tr>
                    </ng-template>
                    <ng-template #body let-sub>
                        <tr>
                            <td>{{ sub.user?.email || sub.user_email || '-' }}</td>
                            <td>{{ sub.plan?.name || sub.plan_name || '-' }}</td>
                            <td>
                                <p-tag [value]="getUserSubscriptionStatusLabel(sub)" [severity]="getUserSubscriptionStatusSeverity(sub)" />
                            </td>
                            <td>{{ sub.start_date ? (sub.start_date | date:'dd/MM/yyyy') : '-' }}</td>
                            <td>{{ sub.end_date ? (sub.end_date | date:'dd/MM/yyyy') : '-' }}</td>
                            <td>
                                <div class="flex gap-2">
                                    <p-button
                                        [label]="getUserSubscriptionActionLabel(sub)"
                                        [severity]="sub.is_active ? 'danger' : (canToggleUserSubscription(sub) ? 'success' : 'secondary')"
                                        size="small"
                                        [disabled]="!canToggleUserSubscription(sub)"
                                        (onClick)="toggleUserSubscription(sub)"
                                    />
                                </div>
                            </td>
                        </tr>
                    </ng-template>
                </p-table>
            </p-card>

            <p-card header="Facturación y Cobros">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
                    <div class="p-2 rounded bg-amber-50 dark:bg-amber-900/10">
                        <div class="text-xs text-amber-700 dark:text-amber-300">Pendientes</div>
                        <div class="text-lg font-semibold">{{ pendingInvoicesCount() }}</div>
                    </div>
                    <div class="p-2 rounded bg-red-50 dark:bg-red-900/10">
                        <div class="text-xs text-red-700 dark:text-red-300">Vencidas</div>
                        <div class="text-lg font-semibold">{{ overdueInvoicesCount() }}</div>
                    </div>
                    <div class="p-2 rounded bg-orange-50 dark:bg-orange-900/10">
                        <div class="text-xs text-orange-700 dark:text-orange-300">Fallidas</div>
                        <div class="text-lg font-semibold">{{ failedPaymentsCount() }}</div>
                    </div>
                </div>

                @if (outstandingInvoices().length === 0) {
                    <div class="p-3 rounded border border-green-200 bg-green-50 dark:bg-green-900/10 text-green-800 dark:text-green-200 text-sm mb-3">
                        Sin pendientes, vencidas o fallidas.
                    </div>
                }

                <p-table [value]="outstandingInvoices()" [tableStyle]="{ 'min-width': '100%' }" responsiveLayout="scroll">
                    <ng-template #header>
                        <tr>
                            <th>Factura</th>
                            <th>Monto</th>
                            <th>Estado</th>
                            <th>Vence</th>
                        </tr>
                    </ng-template>
                    <ng-template #body let-inv>
                        <tr>
                            <td>#{{ inv.id }}</td>
                            <td>{{ inv.amount | currency:'USD' }}</td>
                            <td><p-tag [value]="getInvoiceDisplayStatus(inv)" [severity]="getInvoiceSeverity(getInvoiceDisplayStatus(inv))" /></td>
                            <td>{{ inv.due_date ? (inv.due_date | date:'dd/MM/yyyy') : '-' }}</td>
                        </tr>
                    </ng-template>
                </p-table>
            </p-card>
        </div>

        <p-card header="Actividad Técnica Reciente del Tenant">
            <p-table [value]="tenantLogs()" [tableStyle]="{ 'min-width': '100%' }" responsiveLayout="scroll">
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
                        <td>{{ log.source }}</td>
                        <td>{{ log.description }}</td>
                    </tr>
                </ng-template>
            </p-table>
        </p-card>

        <p-dialog
            [(visible)]="suspensionDialogVisible"
            header="Suspender suscripción"
            [modal]="true"
            [style]="{ width: '32rem' }"
            [breakpoints]="{'960px':'75vw','640px':'100vw'}"
            (onHide)="closeSuspensionDialog()"
        >
            <div class="space-y-4">
                <p class="m-0 text-sm text-gray-600">
                    Indica el motivo de la suspensión. Este texto puede usarse para soporte y auditoría.
                </p>
                <textarea
                    pTextarea
                    [(ngModel)]="suspensionReason"
                    rows="4"
                    class="w-full"
                    maxlength="240"
                    placeholder="Ej: facturas vencidas, solicitud del cliente, fraude detectado"
                ></textarea>
            </div>
            <ng-template #footer>
                <p-button label="Cancelar" severity="secondary" (onClick)="closeSuspensionDialog()" />
                <p-button
                    label="Suspender"
                    severity="warn"
                    icon="pi pi-pause"
                    (onClick)="confirmSuspension()"
                    [disabled]="!suspensionReason.trim()"
                    [loading]="saving()"
                />
            </ng-template>
        </p-dialog>

        <p-dialog
            [(visible)]="planChangeBlockedVisible"
            header="Cambio de plan bloqueado"
            [modal]="true"
            [style]="{ width: '34rem' }"
            [breakpoints]="{'960px':'75vw','640px':'100vw'}"
            [draggable]="false"
            [resizable]="false"
        >
            <div class="space-y-4">
                <div class="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-900/20">
                    <i class="pi pi-exclamation-triangle text-amber-600 dark:text-amber-300 text-lg mt-1"></i>
                    <div>
                        <div class="font-semibold text-amber-900 dark:text-amber-100">{{ planChangeBlockInfo.title }}</div>
                        <p class="m-0 text-sm text-amber-800 dark:text-amber-200">{{ planChangeBlockInfo.message }}</p>
                    </div>
                </div>

                @if (selectedPlanPreview(); as preview) {
                    <div class="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/40 text-sm space-y-2">
                        <div><strong>Plan seleccionado:</strong> {{ preview.display_name || preview.name || '-' }}</div>
                        <div><strong>Límite de usuarios:</strong> {{ formatLimit(preview.max_users) }}</div>
                        <div><strong>Sucursales múltiples:</strong> {{ preview.allows_multiple_branches ? 'Sí' : 'No' }}</div>
                    </div>
                }
            </div>
            <ng-template #footer>
                <p-button label="Entendido" icon="pi pi-check" (onClick)="closePlanChangeBlockedDialog()" />
            </ng-template>
        </p-dialog>
    `
})
export class TenantDetail implements OnInit {
    private readonly errorLogger = inject(AdminErrorLogService);

    tenantId = signal<number | null>(null);
    tenant = signal<any>(null);
    tenantStats = signal<any>(null);
    users = signal<any[]>([]);
    tenantSubscription = signal<any>(null);
    userSubscriptions = signal<any[]>([]);
    tenantInvoices = signal<any[]>([]);
    tenantLogs = signal<any[]>([]);
    plans = signal<any[]>([]);
    selectedPlanId: number | null = null;
    loading = signal(false);
    saving = signal(false);
    diagnostics = signal<DiagnosticFinding[]>([]);
    suspensionDialogVisible = false;
    suspensionReason = '';
    planChangeBlockedVisible = false;
    planChangeBlockInfo: PlanChangeBlockInfo = {
        title: 'No se puede aplicar este cambio',
        message: 'Revisa las restricciones actuales del tenant antes de volver a intentarlo.'
    };

    planOptions = signal<any[]>([]);

    constructor(
        private destroyRef: DestroyRef,
        private route: ActivatedRoute,
        private router: Router,
        private tenantService: TenantService,
        private subscriptionService: SubscriptionService,
        private activityLogService: ActivityLogService,
        private billingService: BillingService,
        private messageService: MessageService
    ) {}

    ngOnInit(): void {
        const id = Number(this.route.snapshot.paramMap.get('id'));
        if (!id) {
            this.goBack();
            return;
        }
        this.tenantId.set(id);
        this.loadTenantData();
        this.loadPlans();
    }

    loadTenantData(): void {
        const id = this.tenantId();
        if (!id) return;

        this.loading.set(true);
        const invoices$ = this.billingService
            .getInvoices({ tenant: id })
            .pipe(catchError(() => of([])));

        forkJoin({
            tenant: this.tenantService.getTenantById(id).pipe(catchError(() => of(null))),
            stats: this.tenantService.getTenantStats(id).pipe(catchError(() => of(null))),
            users: this.tenantService.getTenantUsers(id).pipe(catchError(() => of([]))),
            subscription: this.tenantService.getTenantSubscription(id).pipe(catchError(() => of(null))),
            userSubscriptions: this.subscriptionService.getUserSubscriptions({ tenant: id }).pipe(catchError(() => of([]))),
            invoices: invoices$,
            logs: this.activityLogService.getAuditLogs({ tenant: id, page_size: 20 }).pipe(catchError(() => of({ results: [] })))
        }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: ({ tenant, stats, users, subscription, userSubscriptions, invoices, logs }) => {
                const usersArr = Array.isArray(users) ? users : users?.results || [];
                const userSubsArr = Array.isArray(userSubscriptions) ? userSubscriptions : userSubscriptions?.results || [];
                const normalizedUserSubsArr = this.normalizeUserSubscriptions(userSubsArr);
                const invoicesArrRaw = Array.isArray(invoices) ? invoices : invoices?.results || [];
                const logsArr = logs?.results || [];

                this.tenant.set(tenant);
                this.tenantStats.set(stats);
                this.users.set(usersArr);
                this.tenantSubscription.set(subscription);
                this.userSubscriptions.set(normalizedUserSubsArr);
                this.tenantInvoices.set(invoicesArrRaw);
                this.tenantLogs.set(logsArr);
                this.selectedPlanId = tenant?.subscription_plan?.id || tenant?.subscription_plan || null;
                this.diagnostics.set(this.buildDiagnostics(tenant, invoicesArrRaw, logsArr, normalizedUserSubsArr));
                this.loading.set(false);
            },
            error: (error) => {
                this.loading.set(false);
                this.showError('No se pudo cargar detalle del tenant', error);
            }
        });
    }

    loadPlans(): void {
        this.subscriptionService.getPlans().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (data: any) => {
                const plans = Array.isArray(data) ? data : data?.results || [];
                this.plans.set(plans);
                this.planOptions.set(plans.map((p: any) => ({
                    id: p.id,
                    name: p.name,
                    displayName: p.display_name || p.name
                })));
            },
            error: () => {
                this.planOptions.set([]);
            }
        });
    }

    applyPlanChange(): void {
        const id = this.tenantId();
        if (!id || !this.selectedPlanId || !this.canApplyPlanChange()) return;

        this.saving.set(true);
        this.tenantService.updateTenant(id, { subscription_plan: this.selectedPlanId }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: () => {
                this.saving.set(false);
                this.showSuccess('Plan actualizado correctamente');
                this.loadTenantData();
            },
            error: (error) => {
                this.saving.set(false);
                this.openPlanChangeBlockedDialog(error);
                this.showError('No se pudo actualizar plan del tenant', error);
            }
        });
    }

    toggleActive(): void {
        const current = this.tenant();
        if (!current) return;

        const action$ = current.is_active
            ? this.tenantService.deactivateTenant(this.tenantId()!)
            : this.tenantService.activateTenant(this.tenantId()!);

        this.saving.set(true);
        action$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: () => {
                this.saving.set(false);
                this.showSuccess(current.is_active ? 'Tenant desactivado' : 'Tenant activado');
                this.loadTenantData();
            },
            error: (error) => {
                this.saving.set(false);
                this.showError('No se pudo actualizar estado activo', error);
            }
        });
    }

    toggleSuspension(): void {
        const current = this.tenant();
        if (!current) return;

        if (current.subscription_status === 'suspended') {
            this.resumeSuspension();
            return;
        }

        this.suspensionReason = '';
        this.suspensionDialogVisible = true;
    }

    confirmSuspension(): void {
        const id = this.tenantId();
        const reason = this.suspensionReason.trim();
        if (!id || !reason) return;

        this.saving.set(true);
        this.tenantService.suspendTenant(id, reason).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: () => {
                this.saving.set(false);
                this.closeSuspensionDialog();
                this.showSuccess('Suscripción suspendida');
                this.loadTenantData();
            },
            error: (error) => {
                this.saving.set(false);
                this.showError('No se pudo suspender suscripción', error);
            }
        });
    }

    closeSuspensionDialog(): void {
        this.suspensionDialogVisible = false;
        this.suspensionReason = '';
    }

    toggleUserSubscription(sub: any): void {
        if (!sub?.id || !this.canToggleUserSubscription(sub)) return;
        const isCancelled = !!sub.cancelled_at;
        const action$ = isCancelled
            ? this.subscriptionService.reactivateUserSubscription(sub.id)
            : this.subscriptionService.cancelUserSubscription(sub.id);

        action$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: () => {
                this.showSuccess(isCancelled ? 'Suscripción reactivada' : 'Suscripción cancelada');
                this.loadTenantData();
            },
            error: (error) => this.showError('No se pudo cambiar estado de suscripción', error)
        });
    }

    canToggleUserSubscription(sub: any): boolean {
        if (!sub?.id) return false;
        if (this.isTenantSuspended()) return false;
        if (!sub.cancelled_at) return true;
        return !this.isSubscriptionExpired(sub);
    }

    getUserSubscriptionActionLabel(sub: any): string {
        if (this.isTenantSuspended()) return 'Bloqueada';
        if (sub?.cancelled_at) return this.canToggleUserSubscription(sub) ? 'Reactivar' : 'Histórica';
        return 'Cancelar';
    }

    getUserSubscriptionStatusLabel(sub: any): string {
        if (this.isTenantAccessBlocked()) {
            return sub?.is_active ? 'Inactiva (tenant suspendido)' : 'Inactiva';
        }
        return sub?.is_active ? 'Activa' : 'Inactiva';
    }

    getUserSubscriptionStatusSeverity(sub: any): 'success' | 'info' | 'warn' | 'danger' | 'secondary' | 'contrast' {
        if (this.isTenantAccessBlocked()) return 'danger';
        return sub?.is_active ? 'success' : 'danger';
    }

    overdueInvoicesCount(): number {
        const now = new Date();
        return this.tenantInvoices().filter((inv) => inv?.status === 'pending' && inv?.due_date && new Date(inv.due_date) < now).length;
    }

    failedPaymentsCount(): number {
        return this.tenantInvoices().filter((inv) => inv?.status === 'failed').length;
    }

    pendingInvoicesCount(): number {
        return this.tenantInvoices().filter((inv) => inv?.status === 'pending').length;
    }

    totalInvoicesCount(): number {
        return this.tenantInvoices().length;
    }

    paidInvoicesCount(): number {
        return this.tenantInvoices().filter((inv) => inv?.status === 'paid' || inv?.is_paid === true).length;
    }

    outstandingInvoices(): any[] {
        return this.tenantInvoices().filter((inv) => {
            if (!inv) return false;
            if (inv.status === 'failed' || inv.status === 'overdue') return true;
            return inv.status === 'pending';
        });
    }

    getInvoiceDisplayStatus(inv: any): string {
        if (!inv) return 'pending';
        if (inv.status === 'pending' && inv.due_date && new Date(inv.due_date) < new Date()) {
            return 'overdue';
        }
        return inv.status || 'pending';
    }

    getSubscriptionSeverity(status?: string): 'success' | 'info' | 'warn' | 'danger' | 'secondary' | 'contrast' {
        if (!status) return 'secondary';
        if (status === 'active') return 'success';
        if (status === 'trial') return 'info';
        if (status === 'suspended') return 'danger';
        return 'warn';
    }

    getInvoiceSeverity(status?: string): 'success' | 'info' | 'warn' | 'danger' | 'secondary' | 'contrast' {
        if (status === 'paid') return 'success';
        if (status === 'pending') return 'warn';
        if (status === 'failed' || status === 'overdue') return 'danger';
        return 'secondary';
    }

    getLogSeverity(action?: string): 'success' | 'info' | 'warn' | 'danger' | 'secondary' | 'contrast' {
        if (!action) return 'secondary';
        if (action.includes('ERROR')) return 'danger';
        if (action.includes('ALERT')) return 'warn';
        if (action === 'CREATE' || action === 'UPDATE') return 'success';
        return 'info';
    }

    getDiagnosticClass(severity: 'critical' | 'warning' | 'info'): string {
        if (severity === 'critical') return 'border-red-600 bg-red-50 dark:bg-red-900/10';
        if (severity === 'warning') return 'border-amber-600 bg-amber-50 dark:bg-amber-900/10';
        return 'border-blue-600 bg-blue-50 dark:bg-blue-900/10';
    }

    trackByDiagnostic(index: number, item: DiagnosticFinding): string {
        return `${item.severity}-${item.title}-${index}`;
    }

    private buildDiagnostics(tenant: any, invoices: any[], logs: any[], userSubscriptions: any[]): DiagnosticFinding[] {
        const findings: DiagnosticFinding[] = [];
        const overdue = invoices.filter((inv) => inv?.status === 'pending' && inv?.due_date && new Date(inv.due_date) < new Date()).length;
        const failed = invoices.filter((inv) => inv?.status === 'failed').length;
        const errors = logs.filter((log) => String(log?.action || '').includes('ERROR')).length;
        const inactiveUsers = (this.users() || []).filter((u) => u && u.is_active === false).length;
        const inactiveSubs = userSubscriptions.filter((s) => s && s.is_active === false).length;
        const suspensionContext = this.extractSuspensionContext(logs);

        if (tenant?.subscription_status === 'suspended') {
            findings.push({
                severity: 'critical',
                title: 'Tenant suspendido',
                detail: 'El tenant no está en estado operativo normal.',
                action: suspensionContext
                    ? `Causa detectada en logs: ${suspensionContext}. Verifica "Facturación y Cobros" (pending/failed) y luego usa "Reanudar Suscripción" en "Acciones Operativas".`
                    : 'Revisa "Actividad Técnica Reciente del Tenant" para identificar el último evento de suspensión, valida "Facturación y Cobros" (pending/failed) y luego usa "Reanudar Suscripción" en "Acciones Operativas".'
            });
        }

        if (overdue > 0) {
            findings.push({
                severity: 'warning',
                title: 'Facturas vencidas detectadas',
                detail: `Se detectaron ${overdue} facturas vencidas.`,
                action: 'Contactar al cliente y gestionar cobro o plan de regularización.'
            });
        }

        if (failed > 0) {
            findings.push({
                severity: 'warning',
                title: 'Pagos fallidos',
                detail: `Se detectaron ${failed} pagos fallidos para este tenant.`,
                action: 'Revisar método de pago y logs de integración (Stripe/PayPal).'
            });
        }

        if (errors > 0) {
            findings.push({
                severity: 'warning',
                title: 'Errores técnicos recientes',
                detail: `Hay ${errors} eventos de error en actividad reciente del tenant.`,
                action: 'Inspeccionar logs técnicos y validar dependencias externas.'
            });
        }

        if (inactiveUsers > 0) {
            findings.push({
                severity: 'info',
                title: 'Usuarios inactivos',
                detail: `${inactiveUsers} usuarios están inactivos en este tenant.`,
                action: 'Confirmar si la inactividad es esperada o requiere soporte.'
            });
        }

        if (inactiveSubs > 0) {
            findings.push({
                severity: 'info',
                title: 'Suscripciones de usuario inactivas',
                detail: `${inactiveSubs} suscripciones de usuario aparecen inactivas.`,
                action: 'En "Suscripciones de Usuarios", revisa Estado/Plan/Fin por usuario. Si aplica, usa "Reactivar"; si el plan no corresponde, ajusta plan del tenant en "Acciones Operativas".'
            });
        }

        return findings;
    }

    private extractSuspensionContext(logs: any[]): string {
        if (!Array.isArray(logs) || logs.length === 0) return '';

        const suspensionLog = logs.find((log) => {
            const action = String(log?.action || '').toLowerCase();
            const description = String(log?.description || '').toLowerCase();
            return action.includes('suspend') || description.includes('suspend');
        });

        const description = String(suspensionLog?.description || '').trim();
        return description.substring(0, 120);
    }

    private normalizeUserSubscriptions(subscriptions: any[]): any[] {
        if (!Array.isArray(subscriptions)) return [];

        const bestByKey = new Map<string, any>();
        for (const sub of subscriptions) {
            const key = `${this.getSubscriptionUserKey(sub)}::${this.getSubscriptionPlanKey(sub)}`;
            const current = bestByKey.get(key);
            if (!current || this.isBetterSubscriptionCandidate(sub, current)) {
                bestByKey.set(key, sub);
            }
        }

        return Array.from(bestByKey.values()).sort((a, b) => this.getSubscriptionSortScore(b) - this.getSubscriptionSortScore(a));
    }

    private isBetterSubscriptionCandidate(candidate: any, current: any): boolean {
        const candidateRank = this.getSubscriptionRank(candidate);
        const currentRank = this.getSubscriptionRank(current);

        if (candidateRank.currentPeriod !== currentRank.currentPeriod) {
            return candidateRank.currentPeriod > currentRank.currentPeriod;
        }

        if (candidateRank.startTs !== currentRank.startTs) {
            return candidateRank.startTs > currentRank.startTs;
        }

        if (candidateRank.endTs !== currentRank.endTs) {
            return candidateRank.endTs > currentRank.endTs;
        }

        return candidateRank.id > currentRank.id;
    }

    private getSubscriptionSortScore(sub: any): number {
        return this.toTimestamp(sub?.start_date) || this.toTimestamp(sub?.end_date) || 0;
    }

    private getSubscriptionRank(sub: any): { currentPeriod: number; startTs: number; endTs: number; id: number } {
        const startTs = this.toTimestamp(sub?.start_date);
        const endTs = this.toTimestamp(sub?.end_date);
        const nowTs = this.todayTimestamp();
        const startsBeforeNow = !startTs || startTs <= nowTs;
        const endsAfterNow = !endTs || endTs >= nowTs;
        const currentPeriod = startsBeforeNow && endsAfterNow ? 1 : 0;
        const id = Number(sub?.id || 0);

        return { currentPeriod, startTs, endTs, id };
    }

    private getSubscriptionUserKey(sub: any): string {
        return String(sub?.user?.id || sub?.user_id || sub?.user?.email || sub?.user_email || 'unknown-user');
    }

    private getSubscriptionPlanKey(sub: any): string {
        return String(sub?.plan?.id || sub?.plan_id || sub?.plan?.name || sub?.plan_name || 'unknown-plan');
    }

    private isSubscriptionExpired(sub: any): boolean {
        const endDate = this.toDate(sub?.end_date);
        if (!endDate) return false;

        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return endDate < today;
    }

    private isTenantSuspended(): boolean {
        return this.tenant()?.subscription_status === 'suspended';
    }

    private resumeSuspension(): void {
        const id = this.tenantId();
        if (!id) return;

        this.saving.set(true);
        this.tenantService.resumeTenant(id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: () => {
                this.saving.set(false);
                this.showSuccess('Suscripción reanudada');
                this.loadTenantData();
            },
            error: (error) => {
                this.saving.set(false);
                this.showError('No se pudo reanudar suscripción', error);
            }
        });
    }

    private isTenantAccessBlocked(): boolean {
        const tenant = this.tenant();
        return tenant?.is_active === false || tenant?.subscription_status === 'suspended';
    }

    selectedPlanPreview(): any | null {
        if (!this.selectedPlanId) return null;
        return this.plans().find((plan) => plan?.id === this.selectedPlanId) || null;
    }

    currentTenantPlanId(): number | null {
        const tenant = this.tenant();
        const planId = tenant?.subscription_plan?.id || tenant?.subscription_plan || null;
        return typeof planId === 'number' ? planId : Number(planId) || null;
    }

    isSelectedPlanCurrent(): boolean {
        return !!this.selectedPlanId && this.selectedPlanId === this.currentTenantPlanId();
    }

    canApplyPlanChange(): boolean {
        return !!this.selectedPlanId && !this.isSelectedPlanCurrent();
    }

    getTenantPlanDisplayName(): string {
        const tenant = this.tenant();
        const currentPlan = this.plans().find((plan) => plan?.id === this.currentTenantPlanId());
        return (
            currentPlan?.display_name ||
            tenant?.subscription_plan?.display_name ||
            tenant?.subscription_plan?.name ||
            tenant?.plan_type ||
            '-'
        );
    }

    formatLimit(limit: number | null | undefined): string {
        return !limit ? 'Ilimitado' : String(limit);
    }

    currentUsersCount(): number {
        return Number(this.tenantStats()?.current_users ?? this.users().length ?? 0);
    }

    selectedPlanCreatesUserOverage(): boolean {
        const selectedPlan = this.selectedPlanPreview();
        if (!selectedPlan || !selectedPlan.max_users) return false;
        return this.currentUsersCount() > selectedPlan.max_users;
    }

    private toDate(value: any): Date | null {
        if (!value) return null;
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return null;
        date.setHours(0, 0, 0, 0);
        return date;
    }

    private toTimestamp(value: any): number {
        const date = this.toDate(value);
        return date ? date.getTime() : 0;
    }

    private todayTimestamp(): number {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return today.getTime();
    }

    goBack(): void {
        this.router.navigate(['/admin/tenants']);
    }

    private showSuccess(detail: string): void {
        this.messageService.add({ severity: 'success', summary: 'Éxito', detail, life: 3000 });
    }

    private showError(detail: string, error?: any): void {
        this.errorLogger.log('TenantDetail', detail, error);
        const errorMessage = this.extractErrorMessage(error, detail);
        this.messageService.add({ severity: 'error', summary: 'Error', detail: errorMessage.substring(0, 240), life: 5000 });
    }

    private openPlanChangeBlockedDialog(error?: any): void {
        const message = this.extractErrorMessage(error, 'Revisa las restricciones del tenant e inténtalo de nuevo.');
        this.planChangeBlockInfo = {
            title: 'El tenant no puede cambiar a ese plan todavía',
            message
        };
        this.planChangeBlockedVisible = true;
    }

    closePlanChangeBlockedDialog(): void {
        this.planChangeBlockedVisible = false;
    }

    private extractErrorMessage(error: any, fallback: string): string {
        const payload = error?.error;

        if (typeof payload === 'string' && payload.trim()) {
            return payload.trim();
        }

        if (payload?.message && typeof payload.message === 'string') {
            return payload.message;
        }

        if (payload && typeof payload === 'object') {
            const firstFieldError = Object.values(payload)
                .flatMap((value: any) => Array.isArray(value) ? value : [value])
                .find((value: any) => typeof value === 'string' && value.trim());

            if (typeof firstFieldError === 'string') {
                return firstFieldError;
            }
        }

        if (typeof error?.message === 'string' && error.message.trim()) {
            return error.message;
        }

        return fallback;
    }
}
