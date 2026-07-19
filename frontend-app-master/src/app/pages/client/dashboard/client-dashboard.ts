import { Component, signal, OnInit, OnDestroy, inject, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../../core/services/auth/auth.service';
import { TrialService } from '../../../core/services/trial.service';
import { NotificationBadgeService } from '../../../core/services/notification/notification-badge.service';
import { MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';
import { TrialBannerComponent } from '../../../shared/components/trial-banner.component';
import { AuSkeleton, AuCard, AuBtn } from '../../../shared/components';
import { SubscriptionService } from '../../../core/services/subscription/subscription.service';
import { TenantService } from '../../../core/services/tenant/tenant.service';
import { StatsWidget } from '../../dashboard/components/statswidget';
import { RecentSalesWidget } from '../../dashboard/components/recentsaleswidget';
import { BestSellingWidget } from '../../dashboard/components/bestsellingwidget';
import { RevenueStreamWidget } from '../../dashboard/components/revenuestreamwidget';
import { NotificationsWidget } from '../../dashboard/components/notificationswidget';
import { Subscription } from 'rxjs';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { getSubscriptionPlanLabel } from '../../../core/utils/subscription-plan-label';
import { DashboardService } from '../../../core/services/dashboard/dashboard.service';
import { getRoleDisplayLabel, normalizeRole } from '../../../core/utils/role-normalizer';
import { safeGetItem } from '../../../core/utils/storage';

@Component({
    selector: 'app-client-dashboard',
    standalone: true,
    imports: [CommonModule, RouterModule, ToastModule, TrialBannerComponent, AuSkeleton, AuCard, AuBtn, StatsWidget, RecentSalesWidget, BestSellingWidget, RevenueStreamWidget, NotificationsWidget],
    providers: [MessageService],
    template: `
        <p-toast position="top-right" />
        <app-trial-banner></app-trial-banner>

        @if (loading()) {
            <!-- ===== SKELETON: Hero profile card ===== -->
            <div class="overflow-hidden rounded-xl border border-surface-200 bg-surface-0 shadow-sm dark:border-surface-800 dark:bg-surface-900">
                <div class="bg-surface-50/75 p-6 dark:bg-surface-800/75">
                    <div class="sm:flex sm:items-center sm:justify-between">
                        <div class="sm:flex sm:gap-x-5">
                            <div class="shrink-0 flex justify-center">
                                <au-skeleton variant="avatar" width="5rem" height="5rem" />
                            </div>
                            <div class="mt-4 text-center sm:mt-0 sm:pt-1 sm:text-left space-y-2">
                                <au-skeleton width="120px" height="12px" />
                                <au-skeleton width="200px" height="28px" />
                                <au-skeleton width="100px" height="12px" />
                            </div>
                        </div>
                        <div class="mt-5 flex justify-center gap-3 sm:mt-0">
                            <au-skeleton width="160px" height="36px" />
                            <au-skeleton width="140px" height="36px" />
                        </div>
                    </div>
                </div>
                <div class="grid grid-cols-1 divide-y divide-surface-200 border-t border-surface-200 bg-surface-0/50 dark:divide-surface-800 dark:border-surface-800 dark:bg-surface-900/50 sm:grid-cols-3 sm:divide-x sm:divide-y-0">
                    <div class="flex items-center gap-3 px-6 py-5">
                        <au-skeleton shape="circle" size="2.5rem" />
                        <div class="space-y-1">
                            <au-skeleton width="60px" height="24px" />
                            <au-skeleton width="140px" height="12px" />
                        </div>
                    </div>
                    <div class="flex items-center gap-3 px-6 py-5">
                        <au-skeleton shape="circle" size="2.5rem" />
                        <div class="space-y-1">
                            <au-skeleton width="60px" height="24px" />
                            <au-skeleton width="140px" height="12px" />
                        </div>
                    </div>
                    <div class="flex items-center gap-3 px-6 py-5">
                        <au-skeleton shape="circle" size="2.5rem" />
                        <div class="space-y-1">
                            <au-skeleton width="60px" height="24px" />
                            <au-skeleton width="140px" height="12px" />
                        </div>
                    </div>
                </div>
            </div>

            <!-- ===== SKELETON: Operations section ===== -->
            <section class="dashboard-operations mb-8">
                <header class="dashboard-operations__header">
                    <div>
                        <au-skeleton width="160px" height="14px" />
                        <au-skeleton width="240px" height="28px" class="mt-2" />
                    </div>
                    <au-skeleton width="320px" height="14px" />
                </header>
                <div class="dashboard-operations__grid">
                    @for (i of [1,2,3,4]; track i) {
                        <div class="dashboard-operation-card">
                            <au-skeleton variant="avatar" width="2.5rem" height="2.5rem" />
                            <au-skeleton width="80px" height="16px" />
                            <au-skeleton width="100%" height="12px" />
                        </div>
                    }
                </div>
            </section>

            <!-- ===== SKELETON: Dashboard widgets ===== -->
            <div class="grid grid-cols-12 gap-8">
                <div class="col-span-12 lg:col-span-6 xl:col-span-3">
                    <div class="card"><au-skeleton variant="card" height="120px" /></div>
                </div>
                <div class="col-span-12 lg:col-span-6 xl:col-span-3">
                    <div class="card"><au-skeleton variant="card" height="120px" /></div>
                </div>
                <div class="col-span-12 lg:col-span-6 xl:col-span-3">
                    <div class="card"><au-skeleton variant="card" height="120px" /></div>
                </div>
                <div class="col-span-12 lg:col-span-6 xl:col-span-3">
                    <div class="card"><au-skeleton variant="card" height="120px" /></div>
                </div>
                <div class="col-span-12 xl:col-span-6">
                    <div class="card"><au-skeleton variant="card" height="260px" /></div>
                    <div class="card mt-4"><au-skeleton variant="card" height="200px" /></div>
                </div>
                <div class="col-span-12 xl:col-span-6">
                    <div class="card"><au-skeleton variant="card" height="200px" /></div>
                    <div class="card mt-4"><au-skeleton variant="card" height="200px" /></div>
                </div>
            </div>
        } @else {
            @if (currentUser(); as user) {
            <div class="dash-page">

                <!-- Hero -->
                <header class="au-hero">
                    <div class="au-hero__main">
                        <h1 class="au-hero__title">{{ getGreeting() }}, {{ user.full_name.split(' ')[0] }}</h1>
                        <p class="au-hero__subtitle">
                            {{ getRoleDisplayName(user.role) }}
                            @if (currentTenant()?.name) {
                                <span class="au-hero__dot">·</span> {{ currentTenant().name }}
                            }
                        </p>
                    </div>

                    <div class="au-hero__actions">
                        @if (canSeePlanCard() && subscriptionStatus(); as subscription) {
                            <div class="au-plan">
                                <span class="au-plan__badge" [class.au-plan__badge--active]="subscription.current_status === 'active'">
                                    <i class="pi pi-credit-card"></i>
                                    {{ getCurrentPlanName() }}
                                </span>
                                <span class="au-plan__status">{{ getSubscriptionStatusLine(subscription) }}</span>
                            </div>
                            @if (canManageSubscription()) {
                                <button type="button" au-btn variant="secondary" size="sm" (click)="goTo('/client/payment')">
                                    {{ t('dashboard.client.view_plans') }}
                                </button>
                            }
                        }
                        <button type="button" au-btn variant="ghost" size="sm" (click)="copyShareLink()">
                            <i class="pi pi-share-alt"></i>
                            {{ t('dashboard.client.share_link') }}
                        </button>
                    </div>
                </header>

                <!-- KPI cards -->
                <div class="au-kpi-grid" style="margin-bottom: var(--dash-section-gap)">
                    <div class="au-kpi au-kpi--agenda">
                        <au-card variant="glass">
                            <span class="au-kpi__icon"><i class="pi pi-calendar-clock"></i></span>
                            <p class="au-kpi__label">{{ t('dashboard.client.appointments_today') }}</p>
                            <p class="au-kpi__value">{{ appointmentCount() }}</p>
                            <div class="au-kpi__footer">
                                @if (overdueCount() > 0) {
                                    <span class="au-delta down"><i class="pi pi-exclamation-triangle"></i>{{ overdueCount() }} {{ t('dashboard.client.overdue') }}</span>
                                } @else {
                                    <span class="au-delta neutral">{{ t('dashboard.client.overdue') }}: 0</span>
                                }
                            </div>
                        </au-card>
                    </div>

                    <div class="au-kpi">
                        <au-card variant="glass">
                            <span class="au-kpi__icon"><i class="pi pi-shield"></i></span>
                            <p class="au-kpi__label">{{ t('dashboard.client.role_label') }}</p>
                            <p class="au-kpi__value au-kpi__value--text">{{ getRoleDisplayName(user.role) }}</p>
                            <div class="au-kpi__footer">{{ getUserInitials(user.full_name) }} · {{ user.full_name }}</div>
                        </au-card>
                    </div>

                    @if (topBarberToday) {
                        <div class="au-kpi au-kpi--pos">
                            <au-card variant="glass">
                                <span class="au-kpi__icon"><i class="pi pi-trophy"></i></span>
                                <p class="au-kpi__label">{{ t('dashboard.client.today') }}</p>
                                <p class="au-kpi__value au-kpi__value--text">{{ topBarberToday.name }}</p>
                                <div class="au-kpi__footer">
                                    <span class="au-delta up">{{ topBarberToday.sales }} servicios</span>
                                </div>
                            </au-card>
                        </div>
                    }
                </div>

                <hr class="au-dash-divider">

                <!-- Quick actions -->
                <p class="au-dash-section-title">{{ isRestrictedDashboard() ? t('dashboard.client.my_day') : t('dashboard.client.quick_entries') }}</p>
                <div class="dashboard-operations__grid" style="margin-bottom: var(--dash-section-gap)">
                    @for (action of operationalCards(); track action.route) {
                        <au-card variant="lift" style="cursor:pointer" (click)="goTo(action.route)">
                            <span class="dashboard-operation-card__icon"><i [class]="action.icon"></i></span>
                            <strong>{{ action.label }}</strong>
                            <p>{{ action.copy }}</p>
                        </au-card>
                    }
                </div>

                @if (canSeeBusinessDashboard()) {
                    <hr class="au-dash-divider">
                    <p class="au-dash-section-title">{{ t('dashboard.client.daily_operations') }}</p>
                    <div class="grid grid-cols-12 gap-8">
                        <app-stats-widget class="contents" />
                        <div class="col-span-12 xl:col-span-6">
                            <app-recent-sales-widget />
                            @if (showAdminWidgets()) {
                                <app-best-selling-widget />
                            }
                        </div>
                        <div class="col-span-12 xl:col-span-6">
                            @if (showAdminWidgets()) {
                                <app-revenue-stream-widget />
                            }
                            @defer (on viewport) {
                                <app-notifications-widget />
                            } @placeholder {
                                <div class="au-kpi h-32"></div>
                            }
                        </div>
                    </div>
                }

            </div>
            }
        }
        `,
    styles: [`
        .dash-page {
            display: flex;
            flex-direction: column;
            gap: 0;
        }

        /* ===== Hero ===== */
        .au-hero {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 1.25rem;
            padding: 1.75rem 1.75rem;
            border-radius: var(--radius-xl, 1rem);
            background:
                radial-gradient(120% 140% at 0% 0%, rgba(26, 86, 219, 0.10), transparent 55%),
                radial-gradient(120% 140% at 100% 0%, rgba(212, 168, 75, 0.10), transparent 50%),
                var(--surface-card, #fff);
            border: 1px solid var(--surface-border, #E5E0DB);
            box-shadow: var(--shadow-card, 0 1px 3px rgba(30,27,24,0.06));
            margin-bottom: var(--dash-section-gap, 1.75rem);
        }
        .app-dark .au-hero {
            background:
                radial-gradient(120% 140% at 0% 0%, rgba(26, 86, 219, 0.18), transparent 55%),
                radial-gradient(120% 140% at 100% 0%, rgba(212, 168, 75, 0.14), transparent 50%),
                var(--surface-card, #13161D);
        }

        .au-hero__title {
            margin: 0;
            font-family: var(--font-display, 'EB Garamond', Georgia, serif);
            font-size: clamp(1.6rem, 1rem + 2vw, 2.4rem);
            font-weight: 600;
            line-height: 1.1;
            letter-spacing: -0.02em;
            color: var(--text-color, #1E1B18);
        }

        .au-hero__subtitle {
            margin: 0.6rem 0 0;
            font-size: 0.92rem;
            color: var(--text-color-secondary, #9C948C);
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }
        .au-hero__subtitle i { font-size: 0.85rem; color: var(--brand, #1A56DB); }
        .au-hero__dot { opacity: 0.5; }

        .au-hero__actions {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            flex-wrap: wrap;
        }

        .au-plan {
            display: inline-flex;
            align-items: center;
            gap: 0.6rem;
            padding: 0.4rem 0.5rem 0.4rem 0.85rem;
            border-radius: var(--radius-full, 9999px);
            background: var(--surface-50, #F7F5F2);
            border: 1px solid var(--surface-border, #E5E0DB);
            white-space: nowrap;
        }
        .app-dark .au-plan { background: var(--surface-800, #1F232F); }

        .au-plan__badge {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            font-size: 0.82rem;
            font-weight: 600;
            color: var(--text-color-secondary, #9C948C);
        }
        .au-plan__badge--active { color: var(--success, #4A8C5C); }

        .au-plan__status {
            font-size: 0.72rem;
            color: var(--text-color-secondary, #9C948C);
        }

        /* ===== KPI grid ===== */
        .au-kpi-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 1rem;
        }
        .au-kpi { display: flex; }

        .au-kpi__icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 2.75rem;
            height: 2.75rem;
            border-radius: 0.9rem;
            background: rgba(26, 86, 219, 0.10);
            color: var(--brand, #1A56DB);
            font-size: 1.15rem;
            margin-bottom: 0.9rem;
        }
        .au-kpi--agenda .au-kpi__icon { background: rgba(74, 140, 92, 0.12); color: var(--success, #4A8C5C); }
        .au-kpi--pos .au-kpi__icon { background: rgba(212, 168, 75, 0.14); color: var(--accent, #D4A84B); }

        .au-kpi__label {
            margin: 0;
            font-size: 0.82rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            color: var(--text-color-secondary, #9C948C);
            text-transform: uppercase;
        }
        .au-kpi__value {
            margin: 0.35rem 0 0;
            font-family: var(--font-display, 'EB Garamond', Georgia, serif);
            font-size: 2.4rem;
            font-weight: 600;
            line-height: 1;
            letter-spacing: -0.02em;
            color: var(--text-color, #1E1B18);
            animation: au-kpi-pop 480ms cubic-bezier(0.16, 1, 0.3, 1) both;
        }
        .au-kpi__value--text {
            font-size: 1.4rem;
            line-height: 1.2;
            margin-top: 0.5rem;
        }
        .au-kpi__footer {
            margin-top: 0.85rem;
            font-size: 0.82rem;
            color: var(--text-color-secondary, #9C948C);
        }

        @keyframes au-kpi-pop {
            from { opacity: 0; transform: translateY(8px) scale(0.96); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }

        .au-delta {
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            font-weight: 600;
        }
        .au-delta.up { color: var(--success, #4A8C5C); }
        .au-delta.down { color: var(--danger, #B84A4A); }
        .au-delta.neutral { color: var(--text-color-secondary, #9C948C); }

        /* ===== Section title & divider ===== */
        .au-dash-section-title {
            margin: 0 0 1rem;
            font-size: 1.05rem;
            font-weight: 700;
            letter-spacing: -0.01em;
            color: var(--text-color, #1E1B18);
        }
        .au-dash-divider {
            border: none;
            border-top: 1px solid var(--surface-border, #E5E0DB);
            margin: var(--dash-section-gap, 1.75rem) 0;
        }

        /* ===== Quick actions ===== */
        .dashboard-operations__grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.85rem;
        }

        .dashboard-operation-card__icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 2.6rem;
            height: 2.6rem;
            border-radius: 0.9rem;
            background: rgba(26, 86, 219, 0.1);
            color: var(--brand);
            font-size: 1rem;
            margin-bottom: 0.65rem;
        }

        .dashboard-operation-card strong {
            font-size: 1rem;
            color: var(--text-color);
            display: block;
        }

        .dashboard-operation-card p {
            margin: 0.35rem 0 0;
            font-size: 0.85rem;
            line-height: 1.5;
            color: var(--text-color-secondary);
        }

        .app-dark .dashboard-operation-card__icon {
            background: rgba(26, 86, 219, 0.18);
            color: var(--brand-400);
        }

        @media (max-width: 1100px) {
            .au-kpi-grid { grid-template-columns: 1fr; }
            .dashboard-operations__grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        @media (max-width: 640px) {
            .dashboard-operations__grid { grid-template-columns: 1fr; }
            .au-hero { padding: 1.25rem; }
        }
    `]
})
export class ClientDashboard implements OnInit, OnDestroy {
    currentUser = signal<any>(null);
    subscriptionStatus = signal<any>(null);
    currentTenant = signal<any>(null);
    loading = signal(true);
    private subscription = new Subscription();
    private notificationService = inject(NotificationBadgeService);
    private messageService = inject(MessageService);
    private router = inject(Router);
    private dashboardService = inject(DashboardService);

    constructor(
        private authService: AuthService,
        private trialService: TrialService,
        private subscriptionService: SubscriptionService,
        private tenantService: TenantService,
        private localeService: LocaleService
    ) {}

    topBarberToday: { name: string; sales: number } | null = null;

    ngOnInit() {
        this.subscription.add(
            this.authService.currentUser$.subscribe({
                next: (user) => {
                    this.currentUser.set(user);
                    this.loading.set(false);
                },
                error: () => this.loading.set(false)
            })
        );
        
        setTimeout(() => {
            this.trialService.loadTrialStatus();
            this.loadSubscriptionStatus();
            this.loadCurrentTenant();
            this.loadTopBarberToday();
            if (this.canLoadAppointments()) {
                this.showAppointmentNotifications();
            }
        }, 0);
    }

    showAppointmentNotifications() {
        const todayAppointments = this.notificationService.todayAppointments();
        const todayCount = todayAppointments.length;
        const overdueCount = this.notificationService.overdueAppointments().length;
        const summaryLines: string[] = [];

        if (todayCount > 0) {
            summaryLines.push(this.t('dashboard.notifications.today_appointments_detail').replace('{count}', String(todayCount)));
        }

        if (overdueCount > 0) {
            summaryLines.push(this.t('dashboard.notifications.overdue_appointments_detail').replace('{count}', String(overdueCount)));
        }

        if (summaryLines.length > 0) {
            this.messageService.add({
                severity: overdueCount > 0 ? 'warn' : 'info',
                summary: this.t('dashboard.client.summary'),
                detail: summaryLines.join(' · '),
                life: 6000
            });
        }

        if (overdueCount > 0) {
            this.playNotificationSound();
        }
    }

    ngOnDestroy() {
        this.subscription.unsubscribe();
    }

    getRoleDisplayName(role: string): string {
        const key = normalizeRole(role);
        const roleKey_ = `dashboard.role.${key.toLowerCase()}`;
        const translated = this.t(roleKey_);
        return translated !== roleKey_ ? translated : getRoleDisplayLabel(role);
    }

    getUserInitials(fullName: string): string {
        if (!fullName) return '?';
        const parts = fullName.trim().split(/\s+/);
        if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
        return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
    }

    appointmentCount(): number {
        return this.notificationService.todayAppointments().length;
    }

    overdueCount(): number {
        return this.notificationService.overdueAppointments().length;
    }

    private currentRoleKey(): string {
        // Fix RBAC inconsistency: dashboard role checks now use the canonical normalized role.
        return normalizeRole(this.currentUser()?.role);
    }

    isRestrictedDashboard(): boolean {
        const role = this.currentRoleKey();
        return role === 'CLIENT_STAFF' || role === 'ESTILISTA';
    }

    canSeeBusinessDashboard(): boolean {
        const role = this.currentRoleKey();
        return role === 'CLIENT_ADMIN' || role === 'CAJERA' || role === 'MANAGER';
    }

    canSeePlanCard(): boolean {
        const role = this.currentRoleKey();
        return role === 'CLIENT_ADMIN' || role === 'MANAGER';
    }

    canSeeBusinessOperations(): boolean {
        const role = this.currentRoleKey();
        return role === 'CLIENT_ADMIN' || role === 'CAJERA' || role === 'MANAGER';
    }

    canManageSubscription(): boolean {
        const role = this.currentRoleKey();
        return role === 'CLIENT_ADMIN' || role === 'MANAGER';
    }

    canAccessClients(): boolean {
        const role = this.currentRoleKey();
        return role === 'CLIENT_ADMIN' || role === 'CLIENT_STAFF' || role === 'CAJERA' || role === 'MANAGER' || role === 'ESTILISTA';
    }

    quickActions(): Array<{ label: string; icon: string; route: string }> {
        if (this.isRestrictedDashboard()) {
            return [
                { label: this.t('dashboard.client.my_appointments'), icon: 'pi pi-calendar', route: '/client/appointments' },
                { label: this.t('dashboard.client.clients_btn'), icon: 'pi pi-users', route: '/client/clients' },
                { label: this.t('dashboard.client.my_profile'), icon: 'pi pi-user', route: '/client/profile' }
            ];
        }

        const actions = [
            { label: this.t('dashboard.client.agenda'), icon: 'pi pi-calendar', route: '/client/appointments' },
            { label: this.t('dashboard.client.clients_btn'), icon: 'pi pi-users', route: '/client/clients' }
        ];

        if (this.canSeeBusinessOperations()) {
            actions.splice(1, 0, { label: this.t('dashboard.client.cash_register') + ' / POS', icon: 'pi pi-shopping-cart', route: '/client/pos' });
        }

        if (this.currentRoleKey() === 'CLIENT_ADMIN') {
            actions.push({ label: this.t('dashboard.client.business'), icon: 'pi pi-cog', route: '/client/settings' });
        }

        return actions;
    }

    operationalCards(): Array<{ label: string; copy: string; icon: string; route: string }> {
        if (this.isRestrictedDashboard()) {
            return [
                { label: this.t('dashboard.client.my_appointments'), copy: this.t('dashboard.client.my_appointments_desc'), icon: 'pi pi-calendar', route: '/client/appointments' },
                { label: this.t('dashboard.client.clients_btn'), copy: this.t('dashboard.client.clients_desc'), icon: 'pi pi-users', route: '/client/clients' },
                { label: this.t('dashboard.client.my_profile'), copy: this.t('dashboard.client.profile_desc'), icon: 'pi pi-user', route: '/client/profile' }
            ];
        }

        const cards = [
            { label: this.t('dashboard.client.agenda'), copy: this.t('dashboard.client.agenda_desc'), icon: 'pi pi-calendar', route: '/client/appointments' },
            { label: this.t('dashboard.client.clients_btn'), copy: this.t('dashboard.client.clients_desc2'), icon: 'pi pi-users', route: '/client/clients' }
        ];

        if (this.canSeeBusinessOperations()) {
            cards.splice(1, 0, { label: this.t('dashboard.client.cash_register'), copy: this.t('dashboard.client.cash_register_desc'), icon: 'pi pi-shopping-cart', route: '/client/pos' });
        }

        if (this.currentRoleKey() === 'CLIENT_ADMIN') {
            cards.push({ label: this.t('dashboard.client.business'), copy: this.t('dashboard.client.business_desc'), icon: 'pi pi-cog', route: '/client/settings' });
        }

        return cards;
    }

    getHeroSummary(): string {
        const appointmentCount = this.appointmentCount();
        const overdueCount = this.overdueCount();
        if (appointmentCount === 0 && overdueCount === 0) {
            return this.t('dashboard.hero_summary_empty');
        }
        return this.t('dashboard.hero_summary_active')
            .replace('{appointments}', String(appointmentCount))
            .replace('{overdue}', String(overdueCount));
    }

    getGreeting(): string {
        const hour = new Date().getHours();
        if (hour < 12) return this.t('dashboard.client.greeting_morning');
        if (hour < 19) return this.t('dashboard.client.greeting_afternoon');
        return this.t('dashboard.client.greeting_evening');
    }

    copyShareLink(): void {
        const link = this.currentTenant()?.share_link || window.location.origin;
        try {
            navigator.clipboard?.writeText(link);
        } catch {
            /* clipboard not available */
        }
        this.messageService.add({
            severity: 'success',
            summary: this.t('dashboard.client.share_link'),
            detail: this.t('dashboard.client.share_copied'),
            life: 3000
        });
    }

    goTo(route: string): void {
        this.router.navigate([route]);
    }

    getCurrentPlanName(): string {
        const tenant = this.currentTenant();
        if (tenant?.subscription_plan?.display_name || tenant?.subscription_plan?.name || tenant?.plan_type) {
            return getSubscriptionPlanLabel(
                tenant?.subscription_plan?.display_name,
                tenant?.subscription_plan?.name,
                tenant?.plan_type
            );
        }

        const status = this.subscriptionStatus();
        if (status?.plan_display) {
            return getSubscriptionPlanLabel(status.plan_display);
        }

        try {
            const tenant = JSON.parse(safeGetItem('tenant') || '{}');
            return getSubscriptionPlanLabel(
                tenant?.subscription_plan?.display_name,
                tenant?.subscription_plan?.name,
                tenant?.plan_type,
                this.t('dashboard.client.plan_active')
            );
        } catch {
            return this.t('dashboard.client.plan_active');
        }
    }

    getSubscriptionCopy(subscription: any): string {
        const status = String(subscription?.current_status || '').toLowerCase();
        const graceDays = Number(subscription?.days_in_grace || 0);

        if (status === 'active') {
            return this.t('dashboard.client.subscription_active');
        }

        if (graceDays > 0) {
            return this.t('dashboard.client.subscription_grace').replace('{days}', String(graceDays));
        }

        if (status === 'trial') {
            return this.t('dashboard.client.subscription_trial');
        }

        return this.t('dashboard.client.subscription_review');
    }

    getSubscriptionStatusLine(subscription: any): string {
        const status = String(subscription?.current_status || '').toLowerCase();
        const graceDays = Number(subscription?.days_in_grace || 0);

        if (status === 'active') {
            return this.t('dashboard.client.status_active');
        }

        if (graceDays > 0) {
            return this.t('dashboard.client.status_grace').replace('{days}', String(graceDays));
        }

        if (status === 'trial') {
            return this.t('dashboard.client.status_trial');
        }

        return this.t('dashboard.client.status_review');
    }

    canAccessFeature(feature: string): boolean {
        return this.trialService.canAccessFeature(feature);
    }

    showAdminWidgets(): boolean {
        const role = this.currentRoleKey();
        return role === 'CLIENT_ADMIN' || role === 'MANAGER';
    }

    private canLoadAppointments(): boolean {
        const role = this.currentRoleKey();
        return role === 'CLIENT_ADMIN' || role === 'CLIENT_STAFF' || role === 'CAJERA' || role === 'MANAGER' || role === 'ESTILISTA';
    }

    private loadTopBarberToday(): void {
        if (!this.canSeeBusinessDashboard()) return;
        this.subscription.add(
            this.dashboardService.getRecentSales(50).subscribe({
                next: (data: any) => {
                    const sales: any[] = Array.isArray(data) ? data : (data.results || []);
                    const today = new Date().toDateString();
                    const todaySales = sales.filter(s => s.date_time && new Date(s.date_time).toDateString() === today);
                    if (!todaySales.length) return;
                    const barberMap = new Map<string, { name: string; sales: number }>();
                    todaySales.forEach(sale => {
                        const name = sale.barber_name || sale.employee_name || sale.stylist_name;
                        if (name) {
                            const current = barberMap.get(name) || { name, sales: 0 };
                            current.sales += 1;
                            barberMap.set(name, current);
                        }
                    });
                    this.topBarberToday = [...barberMap.values()].sort((a, b) => b.sales - a.sales)[0] || null;
                },
                error: () => {}
            })
        );
    }

    private loadSubscriptionStatus(): void {
        this.subscription.add(
            this.subscriptionService.getSubscriptionStatus().subscribe({
                next: (status) => this.subscriptionStatus.set(status),
                error: () => this.subscriptionStatus.set(null)
            })
        );
    }

    private loadCurrentTenant(): void {
        this.subscription.add(
            this.tenantService.getCurrentTenant().subscribe({
                next: (tenant) => this.currentTenant.set(tenant),
                error: () => this.currentTenant.set(null)
            })
        );
    }

    private playNotificationSound(): void {
        try {
            const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.type = 'sine';
            oscillator.frequency.setValueAtTime(880, audioContext.currentTime);
            gainNode.gain.setValueAtTime(0.07, audioContext.currentTime);

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillator.start();
            oscillator.stop(audioContext.currentTime + 0.18);
        } catch {
        }
    }

    t(key: string): string {
        return this.localeService.t(key as any);
    }

    private buildTodayAppointmentsDetail(appointments: any[]): string {
        const maxItems = 3;
        const lines = appointments.slice(0, maxItems).map((apt) => {
            const time = this.localeService.formatTime(apt.date_time);
            const client = apt.client_name || `${this.t('clients.th_client' as any) || 'Cliente'} #${apt.client}`;
            const service = apt.service_name || this.t('dashboard.recent_sales.na');
            return `• ${time} - ${client} - ${service}`;
        });

        if (appointments.length > maxItems) {
            lines.push(this.t('dashboard.notifications.more').replace('{count}', String(appointments.length - maxItems)));
        } else {
            lines.push(this.t('dashboard.notifications.view_full_agenda'));
        }

        return lines.join('\n');
    }
}
