import { Injectable, computed, signal } from '@angular/core';
import { forkJoin, of, Subscription, timer } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';
import { BillingService } from '../billing.service';
import { TenantService } from '../tenant/tenant.service';
import { SystemMonitorService } from '../system-monitor.service';
import { getSubscriptionPlanLabel } from '../../utils/subscription-plan-label';

export interface AdminPlatformNotification {
    id: number;
    type: 'system' | 'warning' | 'sale';
    title: string;
    message: string;
    is_read: boolean;
    created_at: string;
}

interface PlatformSummary {
    suspendedTenants: number;
    expiringTrials: number;
    overdueInvoices: number;
}

@Injectable({
    providedIn: 'root'
})
export class AdminPlatformNotificationService {
    private readonly notificationsSignal = signal<AdminPlatformNotification[]>([]);
    private readonly summarySignal = signal<PlatformSummary>({
        suspendedTenants: 0,
        expiringTrials: 0,
        overdueInvoices: 0
    });
    private readonly readIds = signal<Set<number>>(new Set());
    private pollingSub?: Subscription;

    readonly notifications = computed(() =>
        this.notificationsSignal().map((item) => ({
            ...item,
            is_read: this.readIds().has(item.id)
        }))
    );

    readonly unreadCount = computed(() => this.notifications().filter((item) => !item.is_read).length);
    readonly summary = computed(() => this.summarySignal());

    constructor(
        private tenantService: TenantService,
        private billingService: BillingService,
        private systemMonitorService: SystemMonitorService
    ) {}

    start(): void {
        if (this.pollingSub) return;

        this.pollingSub = timer(0, 60000)
            .pipe(
                switchMap(() =>
                    forkJoin({
                        tenants: this.tenantService.getTenants({ page_size: 500 }).pipe(catchError(() => of([]))),
                        billingStats: this.billingService.getAdminStats().pipe(catchError(() => of(null))),
                        systemHealth: this.systemMonitorService.checkSystemHealth().pipe(catchError(() => of(null)))
                    })
                )
            )
            .subscribe(({ tenants, billingStats, systemHealth }) => {
                const tenantList = this.normalizeResults(tenants);
                const notifications = this.buildNotifications(tenantList, billingStats, systemHealth);

                this.summarySignal.set({
                    suspendedTenants: tenantList.filter((tenant) => tenant?.subscription_status === 'suspended').length,
                    expiringTrials: tenantList.filter((tenant) => this.isExpiringTrial(tenant)).length,
                    overdueInvoices: Number(billingStats?.overdue_invoices ?? 0)
                });

                this.notificationsSignal.set(notifications);
            });
    }

    stop(): void {
        this.pollingSub?.unsubscribe();
        this.pollingSub = undefined;
    }

    markAsRead(notificationId: number): void {
        this.readIds.update((current) => {
            const next = new Set(current);
            next.add(notificationId);
            return next;
        });
    }

    markAllAsRead(): void {
        this.readIds.set(new Set(this.notificationsSignal().map((item) => item.id)));
    }

    private buildNotifications(tenants: any[], billingStats: any, systemHealth: any): AdminPlatformNotification[] {
        const notifications: AdminPlatformNotification[] = [];
        const nowIso = new Date().toISOString();

        const suspendedTenants = tenants.filter((tenant) => tenant?.subscription_status === 'suspended');
        if (suspendedTenants.length > 0) {
            notifications.push({
                id: 1001,
                type: 'warning',
                title: `${suspendedTenants.length} tenants suspendidos`,
                message: 'Revisa cobros, reactivaciones o casos de soporte con prioridad.',
                created_at: nowIso,
                is_read: false
            });
        }

        const expiringTrials = tenants.filter((tenant) => this.isExpiringTrial(tenant));
        if (expiringTrials.length > 0) {
            notifications.push({
                id: 1002,
                type: 'system',
                title: `${expiringTrials.length} trials por vencer`,
                message: 'Haz seguimiento comercial antes de que expiren en los próximos 7 días.',
                created_at: nowIso,
                is_read: false
            });
        }

        const overdueInvoices = Number(billingStats?.overdue_invoices ?? 0);
        if (overdueInvoices > 0) {
            notifications.push({
                id: 1003,
                type: 'sale',
                title: `${overdueInvoices} facturas vencidas`,
                message: 'La cobranza necesita atención para evitar churn y suspensiones innecesarias.',
                created_at: nowIso,
                is_read: false
            });
        }

        const criticalAlerts = Array.isArray(systemHealth?.alerts)
            ? systemHealth.alerts.filter((alert: any) => alert && alert.resolved !== true)
            : [];

        if (criticalAlerts.length > 0) {
            const topAlert = criticalAlerts[0];
            notifications.push({
                id: 1004,
                type: 'warning',
                title: topAlert?.title || 'Alertas del sistema activas',
                message: topAlert?.message || 'Hay incidencias globales que requieren revisión técnica.',
                created_at: topAlert?.created_at || nowIso,
                is_read: false
            });
        }

        const newestTenant = [...tenants]
            .filter((tenant) => !!tenant?.created_at)
            .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];

        if (newestTenant && this.isRecent(newestTenant.created_at, 3)) {
            notifications.push({
                id: 1005,
                type: 'system',
                title: `Nuevo tenant: ${newestTenant.name || 'Sin nombre'}`,
                message: `Alta reciente en ${getSubscriptionPlanLabel(newestTenant.plan_type, newestTenant.subscription_plan?.name)}.`,
                created_at: newestTenant.created_at,
                is_read: false
            });
        }

        return notifications.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    }

    private normalizeResults(payload: any): any[] {
        return Array.isArray(payload) ? payload : payload?.results || [];
    }

    private isExpiringTrial(tenant: any): boolean {
        if (!tenant) return false;
        const status = String(tenant.subscription_status || '').toLowerCase();
        if (status !== 'trial') return false;

        const rawDate = tenant.trial_end_date || tenant.trial_end;
        if (!rawDate) return false;

        const trialEnd = new Date(rawDate);
        if (Number.isNaN(trialEnd.getTime())) return false;

        const now = new Date();
        const diff = trialEnd.getTime() - now.getTime();
        const days = diff / (1000 * 60 * 60 * 24);
        return days >= 0 && days <= 7;
    }

    private isRecent(value: string, maxDays: number): boolean {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return false;
        const diff = Date.now() - date.getTime();
        return diff >= 0 && diff <= maxDays * 24 * 60 * 60 * 1000;
    }
}
