import { Routes } from '@angular/router';

export const PAYROLL_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./payroll.component').then(m => m.PayrollComponent),
    data: { title: 'Nómina Simple' }
  },
  {
    path: 'my-earnings',
    loadComponent: () => import('../my-earnings/my-earnings.component').then(m => m.MyEarningsComponent),
    data: { title: 'Mis Ingresos' }
  }
];
