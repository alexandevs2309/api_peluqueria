import { Routes } from '@angular/router';
import { Notfound } from './app/pages/notfound/notfound';

export const appRoutes: Routes = [
    // Landing page
    {
        path: '',
        loadComponent: () => import('./app/pages/landing/landing.component').then(m => m.LandingComponent),
        pathMatch: 'full'
    },
    {
        path: 'register',
        redirectTo: 'auth/register',
        pathMatch: 'full'
    },
    {
        path: 'privacy',
        loadComponent: () => import('./app/pages/legal/privacy.component').then(m => m.PrivacyComponent)
    },
    {
        path: 'terms',
        loadComponent: () => import('./app/pages/legal/terms.component').then(m => m.TermsComponent)
    },
    {
        path: 'cookies',
        loadComponent: () => import('./app/pages/legal/cookies.component').then(m => m.CookiesComponent)
    },
    {
        path: 'acceptable-use',
        loadComponent: () => import('./app/pages/legal/acceptable-use.component').then(m => m.AcceptableUseComponent)
    },
    {
        path: 'billing-policy',
        loadComponent: () => import('./app/pages/legal/billing-policy.component').then(m => m.BillingPolicyComponent)
    },
    {
        path: 'dpa',
        loadComponent: () => import('./app/pages/legal/dpa.component').then(m => m.DpaComponent)
    },
    {
        path: 'support',
        redirectTo: 'client/support',
        pathMatch: 'full'
    },
    {
        path: 'docs',
        loadComponent: () => import('./app/pages/recursos/docs.component').then(m => m.DocsComponent)
    },
    {
        path: 'status',
        loadComponent: () => import('./app/pages/recursos/status.component').then(m => m.StatusComponent)
    },
    {
        path: 'changelog',
        loadComponent: () => import('./app/pages/recursos/changelog.component').then(m => m.ChangelogComponent)
    },

    // Auth routes FIRST (login, register, forgot-password, reset-password)
    {
        path: 'auth',
        loadChildren: () => import('./app/pages/auth/auth.routes')
    },

    // Admin shell (fully lazy bundle)
    {
        path: 'admin',
        data: { preload: true, preloadAfterAuth: true, preloadFor: ['SUPER_ADMIN'] },
        loadChildren: () => import('./app/routes/admin.routes').then(m => m.adminRoutes)
    },

    // Client shell (fully lazy bundle)
    {
        path: 'client',
        data: {
            preload: true,
            preloadAfterAuth: true,
            preloadFor: ['CLIENT_ADMIN', 'CLIENT_STAFF', 'Cajera', 'Estilista', 'Manager']
        },
        loadChildren: () => import('./app/routes/client.routes').then(m => m.clientRoutes)
    },

    // 404 page
    { path: 'notfound', component: Notfound },
    { path: '**', redirectTo: '/notfound' }
];
