import { Routes } from '@angular/router';
import { AppLayout } from '../layout/component/app.layout';
import { AuthGuard } from '../core/guards';
import { SuperAdminGuard } from '../core/guards/super-admin.guard';

export const adminRoutes: Routes = [
    {
        path: '',
        canActivate: [AuthGuard, SuperAdminGuard],
        canActivateChild: [AuthGuard, SuperAdminGuard],
        data: { roles: ['SUPER_ADMIN'] },
        component: AppLayout,
        children: [
            { 
                path: 'dashboard', 
                loadComponent: () => import('../pages/admin/admin-dashboard').then(m => m.AdminDashboard)
            },
            { 
                path: 'tenants', 
                loadComponent: () => import('../pages/admin/tenants-management').then(m => m.TenantsManagement)
            },
            {
                path: 'tenants/:id',
                loadComponent: () => import('../pages/admin/tenant-detail').then(m => m.TenantDetail)
            },
            { 
                path: 'users', 
                loadComponent: () => import('../pages/admin/users-management').then(m => m.UsersManagement)
            },
            { 
                path: 'plans', 
                loadComponent: () => import('../pages/admin/subscription-plans').then(m => m.SubscriptionPlans)
            },
            { 
                path: 'settings', 
                loadComponent: () => import('../pages/admin/system-settings').then(m => m.SystemSettings)
            },
            { 
                path: 'audit-logs', 
                loadComponent: () => import('../pages/admin/audit-logs').then(m => m.AuditLogs)
            },
            { 
                path: 'billing', 
                loadComponent: () => import('../pages/admin/billing-management').then(m => m.BillingManagement)
            },
            { 
                path: 'reports', 
                loadComponent: () => import('../pages/admin/admin-reports').then(m => m.AdminReports)
            },
            {
                path: 'support',
                loadComponent: () => import('../pages/admin/admin-support').then(m => m.AdminSupport)
            },
            {
                path: 'tutorials',
                loadComponent: () => import('../pages/admin/tutorials-management').then(m => m.TutorialsManagement)
            },
            {
                path: 'monitor',
                loadComponent: () => import('../pages/admin/system-monitor').then(m => m.SystemMonitor)
            },
            {
                path: 'promotional-credits',
                loadComponent: () => import('../pages/admin/promotional-credits').then(m => m.PromotionalCredits)
            },
            { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
        ]
    }
];
