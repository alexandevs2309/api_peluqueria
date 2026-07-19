import { Routes } from '@angular/router';
import { AppLayout } from '../layout/component/app.layout';
import { AuthGuard, FeatureAccessGuard, RoleGuard, SecurityGuard } from '../core/guards';
import { TrialGuard } from '../core/guards/trial.guard';

export const clientRoutes: Routes = [
    {
        path: '',
        canActivate: [AuthGuard, RoleGuard],
        data: { roles: ['owner', 'manager', 'frontdesk_cashier', 'professional', 'internal_support'] },
        component: AppLayout,
        children: [
            {
                path: 'dashboard',
                canActivate: [TrialGuard, RoleGuard],
                data: { roles: ['owner', 'manager', 'frontdesk_cashier', 'professional', 'internal_support'] },
                loadComponent: () => import('../pages/client/dashboard/client-dashboard').then(m => m.ClientDashboard)
            },
            {
                path: 'subscription',
                canActivate: [RoleGuard],
                data: { roles: ['owner', 'manager'] },
                loadComponent: () => import('../pages/client/subscription/subscription').then(m => m.SubscriptionComponent)
            },
            {
                path: 'payment',
                redirectTo: 'subscription',
                pathMatch: 'full'
            },
            {
                path: 'checkout',
                redirectTo: 'subscription',
                pathMatch: 'full'
            },
            {
                path: 'employees',
                canActivate: [TrialGuard, RoleGuard],
                data: { roles: ['owner', 'manager'] },
                loadComponent: () => import('../pages/client/employees/employees-management').then(m => m.EmployeesManagement)
            },
            {
                path: 'schedules',
                canActivate: [TrialGuard, RoleGuard],
                data: { roles: ['owner', 'manager'] },
                loadComponent: () => import('../pages/client/schedules/schedules-management').then(m => m.SchedulesManagement)
            },
            {
                path: 'appointments',
                canActivate: [TrialGuard, RoleGuard],
                data: { roles: ['owner', 'manager', 'frontdesk_cashier', 'professional', 'internal_support'] },
                loadChildren: () => import('../pages/client/appointments-management/appointments.routes').then(m => m.APPOINTMENTS_ROUTES)
            },
            {
                path: 'pos',
                canActivate: [AuthGuard, SecurityGuard, TrialGuard, RoleGuard, FeatureAccessGuard],
                data: { roles: ['owner', 'manager', 'frontdesk_cashier'], requiredFeature: 'cash_register' },
                loadComponent: () => import('../pages/client/pos/pos-system').then(m => m.PosSystem)
            },
            {
                path: 'payroll',
                canActivate: [SecurityGuard, TrialGuard, RoleGuard],
                data: { roles: ['owner', 'manager'] },
                loadChildren: () => import('../pages/client/payroll/payroll.routes').then(m => m.PAYROLL_ROUTES)
            },
            {
                path: 'my-earnings',
                canActivate: [TrialGuard, RoleGuard],
                data: { roles: ['owner', 'manager', 'professional'] },
                loadComponent: () => import('../pages/client/my-earnings/my-earnings.component').then(m => m.MyEarningsComponent)
            },
            {
                path: 'services',
                canActivate: [TrialGuard, RoleGuard],
                data: { roles: ['owner', 'manager', 'frontdesk_cashier'] },
                loadComponent: () => import('../pages/client/services-managements/services-management').then(m => m.ServicesManagement)
            },
            {
                path: 'clients',
                canActivate: [TrialGuard, RoleGuard],
                data: { roles: ['owner', 'manager', 'frontdesk_cashier', 'professional', 'internal_support'] },
                loadComponent: () => import('../pages/client/clients-managements/clients-management').then(m => m.ClientsManagement)
            },
            {
                path: 'products',
                canActivate: [TrialGuard, RoleGuard, FeatureAccessGuard],
                data: { roles: ['owner', 'manager', 'frontdesk_cashier'], requiredFeature: 'inventory' },
                loadComponent: () => import('../pages/client/products/products-management').then(m => m.ProductsManagement)
            },
            {
                path: 'promotions',
                canActivate: [TrialGuard, RoleGuard, FeatureAccessGuard],
                data: { roles: ['owner', 'manager'], requiredFeature: 'cash_register' },
                loadComponent: () => import('../pages/client/promotions/promotions-management').then(m => m.PromotionsManagement)
            },
            {
                path: 'reports',
                canActivate: [SecurityGuard, TrialGuard, RoleGuard],
                data: { roles: ['owner', 'manager'] },
                loadComponent: () => import('../pages/client/reports/client-reports').then(m => m.ClientReports)
            },
            {
                path: 'settings',
                canActivate: [TrialGuard, RoleGuard],
                data: { roles: ['owner'] },
                loadComponent: () => import('../pages/client/settings/barbershop-settings').then(m => m.BarbershopSettingsComponent)
            },
            {
                path: 'profile',
                canActivate: [RoleGuard],
                data: { roles: ['owner', 'manager', 'frontdesk_cashier', 'professional', 'internal_support'] },
                loadComponent: () => import('../pages/client/profile/user-profile.component').then(m => m.UserProfileComponent)
            },
            {
                path: 'change-password',
                canActivate: [RoleGuard],
                data: { roles: ['owner', 'manager', 'frontdesk_cashier', 'professional', 'internal_support'] },
                loadComponent: () => import('../pages/client/profile/change-password.component').then(m => m.ChangePasswordComponent)
            },
            {
                path: 'help',
                canActivate: [RoleGuard],
                data: { roles: ['owner', 'manager', 'frontdesk_cashier', 'professional', 'internal_support'] },
                loadComponent: () => import('../pages/client/profile/help.component').then(m => m.HelpComponent)
            },
            {
                path: 'branches',
                canActivate: [TrialGuard, RoleGuard, FeatureAccessGuard],
                data: { roles: ['owner', 'manager'], requiredFeature: 'multi_location' },
                loadComponent: () => import('../pages/client/branches/branches-management').then(m => m.BranchesManagement)
            },
            {
                path: 'support',
                canActivate: [RoleGuard],
                data: { roles: ['owner', 'manager', 'frontdesk_cashier', 'professional', 'internal_support'] },
                loadComponent: () => import('../pages/client/support/support-ticket.component').then(m => m.SupportTicketComponent)
            },
            {
                path: 'tutorials',
                canActivate: [RoleGuard],
                data: { roles: ['owner', 'manager', 'frontdesk_cashier', 'professional', 'internal_support'] },
                loadComponent: () => import('../pages/client/tutorials/tutorials.component').then(m => m.TutorialsComponent)
            },

            { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
        ]
    }
];
