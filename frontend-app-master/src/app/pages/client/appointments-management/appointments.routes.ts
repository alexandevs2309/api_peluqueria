import { Routes } from '@angular/router';

export const APPOINTMENTS_ROUTES: Routes = [
    {
        path: '',
        loadComponent: () => import('./appointments-main').then((m) => m.AppointmentsMain),
        children: [
            {
                path: 'calendar',
                loadComponent: () => import('./appointments-calendar').then((m) => m.AppointmentsCalendar)
            },
            {
                path: 'list',
                loadComponent: () => import('./appointments-management').then((m) => m.AppointmentsManagement)
            },
            {
                path: '',
                pathMatch: 'full',
                redirectTo: 'calendar'
            }
        ]
    }
];
