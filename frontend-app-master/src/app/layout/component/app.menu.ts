import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { RouterModule } from '@angular/router';
import { MenuItem } from 'primeng/api';
import { BadgeModule } from 'primeng/badge';
import { AppMenuitem } from './app.menuitem';
import { AuthService } from '../../core/services/auth/auth.service';
import { PlanAccessService } from '../../core/services/plan-access.service';
import { TrialService } from '../../core/services/trial.service';
import { LocaleService } from '../../core/services/locale/locale.service';
import { NotificationBadgeService } from '../../core/services/notification/notification-badge.service';
import { Subscription } from 'rxjs';
import { resolveBusinessRole, roleKey } from '../../core/utils/role-normalizer';

@Component({
    selector: 'app-menu',
    standalone: true,
    imports: [AppMenuitem, RouterModule, BadgeModule],
    template: `<ul class="layout-menu">
        @for (item of model; track item; let i = $index) {
            @if (!item.separator) {
                <li app-menuitem [item]="item" [index]="i" [root]="true"></li>
            }
            @if (item.separator) {
                <li class="menu-separator"></li>
            }
        }
    </ul> `
})
export class AppMenu implements OnInit, OnDestroy {
    model: MenuItem[] = [];
    private subscription = new Subscription();
    private refreshIntervalId: ReturnType<typeof setInterval> | null = null;
    notificationService = inject(NotificationBadgeService);

    constructor(
        private authService: AuthService,
        private planAccessService: PlanAccessService,
        private trialService: TrialService,
        private localeService: LocaleService
    ) {}

    ngOnInit() {
        // Build menu immediately if user exists
        const currentUser = this.authService.getCurrentUser();
        if (currentUser) {
            this.updateMenuForUser(currentUser.role, currentUser.business_role);
            // Load appointments badge only for roles that can access appointments
            if (this.canLoadAppointments(currentUser.role, currentUser.business_role)) {
                this.notificationService.loadAppointments();
                // Refresh every 5 minutes
                this.refreshIntervalId = setInterval(() => this.notificationService.refresh(), 5 * 60000);
            }
        }

        // Subscribe to user changes
        this.subscription.add(
            this.authService.currentUser$.subscribe(user => {
                if (user) {
                    this.updateMenuForUser(user.role, user.business_role);
                    if (this.canLoadAppointments(user.role, user.business_role)) {
                        this.notificationService.loadAppointments();
                    }
                } else {
                    this.model = [];
                }
            })
        );
        
        // Subscribe to language changes
        this.subscription.add(
            this.localeService.languageChanged$.subscribe(() => {
                const currentUser = this.authService.getCurrentUser();
                if (currentUser) {
                    this.updateMenuForUser(currentUser.role, currentUser.business_role);
                }
            })
        );
    }

    private updateMenuForUser(role: string, businessRole?: string) {
        const normalizedRole = roleKey(role);
        if (normalizedRole === 'SUPER_ADMIN') {
            this.model = this.getAdminMenu();
        } else {
            this.buildClientMenu(businessRole || resolveBusinessRole(role, businessRole));
        }
    }

    ngOnDestroy() {
        this.subscription.unsubscribe();
        if (this.refreshIntervalId) {
            clearInterval(this.refreshIntervalId);
            this.refreshIntervalId = null;
        }
    }

    buildClientMenu(businessRole?: string) {
        this.model = this.getClientMenu(businessRole);
    }

    getAdminMenu(): MenuItem[] {
        return [
            {
                label: 'Resumen',
                items: [
                    { label: this.localeService.t('menu.dashboard' as any), icon: 'pi pi-fw pi-home', auronIcon: 'dashboard', routerLink: ['/admin/dashboard'] }
                ]
            },
            {
                label: 'Crecimiento',
                items: [
                    { label: this.localeService.t('menu.subscription_plans' as any), icon: 'pi pi-fw pi-credit-card', routerLink: ['/admin/plans'] },
                    { label: this.localeService.t('menu.billing' as any), icon: 'pi pi-fw pi-dollar', routerLink: ['/admin/billing'] },
                    { label: this.localeService.t('menu.reports' as any), icon: 'pi pi-fw pi-chart-line', auronIcon: 'reports', routerLink: ['/admin/reports'] }
                ]
            },
            {
                label: 'Operaciones',
                items: [
                    { label: this.localeService.t('menu.tenants' as any), icon: 'pi pi-fw pi-building', routerLink: ['/admin/tenants'] },
                    { label: this.localeService.t('menu.users' as any), icon: 'pi pi-fw pi-users', auronIcon: 'clients', routerLink: ['/admin/users'] },
                    { label: this.localeService.t('menu.promotional_credits' as any), icon: 'pi pi-fw pi-gift', routerLink: ['/admin/promotional-credits'] },
                    { label: 'Soporte', icon: 'pi pi-fw pi-headphones', routerLink: ['/admin/support'] },
                    { label: this.localeService.t('menu.tutorials' as any), icon: 'pi pi-fw pi-video', routerLink: ['/admin/tutorials'] },
                    { label: this.localeService.t('menu.system_monitor' as any), icon: 'pi pi-fw pi-eye', routerLink: ['/admin/monitor'] },
                    { label: this.localeService.t('menu.audit_logs' as any), icon: 'pi pi-fw pi-list', routerLink: ['/admin/audit-logs'] },
                    { label: this.localeService.t('menu.system_settings' as any), icon: 'pi pi-fw pi-cog', routerLink: ['/admin/settings'] }
                ]
            }
        ];
    }

    getClientMenu(businessRoleArg?: string): MenuItem[] {
        const user = this.authService.getCurrentUser();
        const userRole = user?.role;
        const userBusinessRole = businessRoleArg || resolveBusinessRole(userRole, user?.business_role);
        const badgeCount = this.notificationService.badgeCount();
        const t = (key: string) => this.localeService.t(key as any);
        const badge = (count: number) => count > 0 ? count.toString() : undefined;

        const sections: MenuItem[] = [];

        if (userBusinessRole === 'owner' || userBusinessRole === 'manager') {
            const canSettings = userBusinessRole === 'owner';

            // Inicio
            sections.push({
                label: 'Inicio',
                items: [
                    { label: t('menu.dashboard'), icon: 'pi pi-fw pi-home', auronIcon: 'dashboard', routerLink: ['/client/dashboard'] }
                ]
            });

            // Atender
            sections.push({
                label: 'Atender',
                items: [
                    { label: t('menu.appointments'), icon: 'pi pi-fw pi-calendar', auronIcon: 'agenda', routerLink: ['/client/appointments'], badge: badge(badgeCount), badgeStyleClass: 'p-badge-danger' },
                    { label: t('menu.pos'), icon: 'pi pi-fw pi-shopping-cart', auronIcon: 'pos', routerLink: ['/client/pos'], visible: this.planAccessService.canAccessFeature('cash_register') },
                    { label: t('menu.clients'), icon: 'pi pi-fw pi-user-plus', auronIcon: 'clients', routerLink: ['/client/clients'] }
                ]
            });

            // Mi Equipo
            sections.push({
                label: 'Mi Equipo',
                items: [
                    { label: t('menu.employees'), icon: 'pi pi-fw pi-users', auronIcon: 'clients', routerLink: ['/client/employees'] },
                    { label: t('menu.schedules'), icon: 'pi pi-fw pi-calendar-plus', routerLink: ['/client/schedules'] },
                    { label: 'Mis Ganancias', icon: 'pi pi-fw pi-wallet', routerLink: ['/client/payroll'] }
                ]
            });

            // Mi Negocio
            sections.push({
                label: 'Mi Negocio',
                items: [
                    { label: t('menu.reports'), icon: 'pi pi-fw pi-chart-line', auronIcon: 'reports', routerLink: ['/client/reports'] },
                    { label: t('menu.services'), icon: 'pi pi-fw pi-wrench', routerLink: ['/client/services'] },
                    { label: t('menu.products'), icon: 'pi pi-fw pi-box', routerLink: ['/client/products'], visible: this.planAccessService.canAccessFeature('inventory') },
                    { label: t('menu.promotions'), icon: 'pi pi-fw pi-tags', routerLink: ['/client/promotions'], visible: this.planAccessService.canAccessFeature('cash_register') }
                ]
            });

            // Configuración
            const configItems: MenuItem[] = [];
            if (this.planAccessService.canAccessFeature('multi_location')) {
                configItems.push({ label: 'Sucursales', icon: 'pi pi-fw pi-sitemap', routerLink: ['/client/branches'] });
            }
            if (canSettings) {
                configItems.push({ label: t('menu.settings'), icon: 'pi pi-fw pi-cog', routerLink: ['/client/settings'] });
            }
            configItems.push(
                { label: 'Soporte', icon: 'pi pi-fw pi-headphones', routerLink: ['/client/support'] }
            );
            sections.push({ label: 'Configuración', items: configItems });

        } else if (userBusinessRole === 'professional' || userBusinessRole === 'internal_support') {
            // Inicio
            sections.push({
                label: 'Inicio',
                items: [
                    { label: t('menu.dashboard'), icon: 'pi pi-fw pi-home', auronIcon: 'dashboard', routerLink: ['/client/dashboard'] }
                ]
            });

            // Atender
            sections.push({
                label: 'Atender',
                items: [
                    { label: t('menu.my_appointments'), icon: 'pi pi-fw pi-calendar', auronIcon: 'agenda', routerLink: ['/client/appointments'], badge: badge(badgeCount), badgeStyleClass: 'p-badge-danger' },
                    { label: t('menu.clients'), icon: 'pi pi-fw pi-user-plus', auronIcon: 'clients', routerLink: ['/client/clients'] }
                ]
            });

            // Mis Ganancias
            sections.push({
                label: 'Mis Ganancias',
                items: [
                    { label: 'Mis Ingresos', icon: 'pi pi-fw pi-wallet', routerLink: ['/client/my-earnings'] }
                ]
            });

            // Configuración
            sections.push({
                label: 'Configuración',
                items: [
                    { label: 'Soporte', icon: 'pi pi-fw pi-headphones', routerLink: ['/client/support'] }
                ]
            });

        } else if (userBusinessRole === 'frontdesk_cashier') {
            // Inicio
            sections.push({
                label: 'Inicio',
                items: [
                    { label: t('menu.dashboard'), icon: 'pi pi-fw pi-home', auronIcon: 'dashboard', routerLink: ['/client/dashboard'] }
                ]
            });

            // Atender
            sections.push({
                label: 'Atender',
                items: [
                    { label: t('menu.appointments'), icon: 'pi pi-fw pi-calendar', auronIcon: 'agenda', routerLink: ['/client/appointments'], badge: badge(badgeCount), badgeStyleClass: 'p-badge-danger' },
                    { label: t('menu.sales'), icon: 'pi pi-fw pi-shopping-cart', auronIcon: 'pos', routerLink: ['/client/pos'], visible: this.planAccessService.canAccessFeature('cash_register') },
                    { label: t('menu.clients'), icon: 'pi pi-fw pi-user-plus', auronIcon: 'clients', routerLink: ['/client/clients'] }
                ]
            });

            // Catálogo
            sections.push({
                label: 'Catálogo',
                items: [
                    { label: t('menu.services'), icon: 'pi pi-fw pi-wrench', routerLink: ['/client/services'] },
                    { label: t('menu.products'), icon: 'pi pi-fw pi-box', routerLink: ['/client/products'], visible: this.planAccessService.canAccessFeature('inventory') }
                ]
            });

            // Configuración
            sections.push({
                label: 'Configuración',
                items: [
                    { label: 'Soporte', icon: 'pi pi-fw pi-headphones', routerLink: ['/client/support'] }
                ]
            });
        }

        return sections;
    }

    private canLoadAppointments(role?: string, businessRole?: string): boolean {
        const resolvedRole = resolveBusinessRole(role, businessRole);
        return resolvedRole === 'owner' || resolvedRole === 'manager' || resolvedRole === 'frontdesk_cashier' || resolvedRole === 'professional' || resolvedRole === 'internal_support';
    }
}
