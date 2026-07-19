import { Routes } from '@angular/router';
import { NoAuthGuard } from '../../core/guards/no-auth.guard';

export default [
    { path: 'access', loadComponent: () => import('./access').then(m => m.Access) },
    { path: 'error', loadComponent: () => import('./error').then(m => m.Error) },
    { path: 'login', loadComponent: () => import('./login').then(m => m.Login), canActivate: [NoAuthGuard] },
    { path: 'register', loadComponent: () => import('./register').then(m => m.Register), canActivate: [NoAuthGuard] },
    { path: 'registration-success', loadComponent: () => import('./registration-success').then(m => m.RegistrationSuccess) },
    { path: 'forgot-password', loadComponent: () => import('./forgot-password').then(m => m.ForgotPassword), canActivate: [NoAuthGuard] },
    { path: 'reset-password/:uid/:token', loadComponent: () => import('./reset-password').then(m => m.ResetPassword), canActivate: [NoAuthGuard] },
    { path: 'verify-email/:token', loadComponent: () => import('./verify-email').then(m => m.VerifyEmail), canActivate: [NoAuthGuard] }
] as Routes;
