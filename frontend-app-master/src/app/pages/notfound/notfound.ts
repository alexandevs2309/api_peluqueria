import { Component, inject } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { AuthService } from '../../core/services/auth/auth.service';
import { roleKey } from '../../core/utils/role-normalizer';

@Component({
    selector: 'app-notfound',
    standalone: true,
    imports: [RouterModule, ButtonModule],
    template: `
        <div class="flex items-center justify-center min-h-screen overflow-hidden px-4">
            <div class="flex flex-col items-center justify-center">
                <div style="border-radius: 56px; padding: 0.3rem; background: linear-gradient(180deg, color-mix(in srgb, var(--primary-color), transparent 60%) 10%, var(--surface-ground) 30%)">
                    <div class="w-full bg-surface-0 dark:bg-surface-900 py-16 px-8 sm:px-20 flex flex-col items-center text-center" style="border-radius: 53px">
                        <div class="mb-6 flex items-center gap-3">
                            <img src="assets/logos/logo-final.png" alt="Auron Suite" class="h-12 w-12 rounded-2xl object-contain shadow-sm" />
                            <div class="text-left">
                                <div class="text-xs uppercase tracking-[0.22em] text-surface-500">Auron Suite</div>
                                <div class="text-lg font-bold text-surface-900 dark:text-surface-0">Ruta no encontrada</div>
                            </div>
                        </div>
                        <span class="text-primary font-bold text-3xl">404</span>
                        <h1 class="text-surface-900 dark:text-surface-0 font-bold text-3xl lg:text-5xl mb-2">Pagina no encontrada</h1>
                        <div class="text-surface-600 dark:text-surface-200 mb-8 max-w-xl">La direccion que buscabas no existe o ya cambio dentro de Auron Suite. Te dejamos accesos rapidos para volver a una seccion util.</div>
                        <a (click)="goHome()" class="w-full flex items-center py-8 border-surface-300 dark:border-surface-500 border-b cursor-pointer">
                            <span class="flex justify-center items-center border-2 border-primary text-primary rounded-border" style="height: 3.5rem; width: 3.5rem">
                                <i class="pi pi-fw pi-table text-2xl!"></i>
                            </span>
                            <span class="ml-6 flex flex-col">
                                <span class="text-surface-900 dark:text-surface-0 lg:text-xl font-medium mb-0 block">Volver al panel</span>
                                <span class="text-surface-600 dark:text-surface-200 lg:text-xl">Retoma tu agenda, ventas y operaciones.</span>
                            </span>
                        </a>
                        <a routerLink="/landing" class="w-full flex items-center py-8 border-surface-300 dark:border-surface-500 border-b">
                            <span class="flex justify-center items-center border-2 border-primary text-primary rounded-border" style="height: 3.5rem; width: 3.5rem">
                                <i class="pi pi-fw pi-question-circle text-2xl!"></i>
                            </span>
                            <span class="ml-6 flex flex-col">
                                <span class="text-surface-900 dark:text-surface-0 lg:text-xl font-medium mb-0">Ir a la landing</span>
                                <span class="text-surface-600 dark:text-surface-200 lg:text-xl">Consulta informacion comercial y planes.</span>
                            </span>
                        </a>
                        <a routerLink="/auth/login" class="w-full flex items-center mb-8 py-8 border-surface-300 dark:border-surface-500 border-b">
                            <span class="flex justify-center items-center border-2 border-primary text-primary rounded-border" style="height: 3.5rem; width: 3.5rem">
                                <i class="pi pi-fw pi-unlock text-2xl!"></i>
                            </span>
                            <span class="ml-6 flex flex-col">
                                <span class="text-surface-900 dark:text-surface-0 lg:text-xl font-medium mb-0">Iniciar sesion</span>
                                <span class="text-surface-600 dark:text-surface-200 lg:text-xl">Accede de nuevo con tu cuenta del negocio.</span>
                            </span>
                        </a>
                        <p-button (click)="goHome()" label="Volver al inicio" />
                    </div>
                </div>
            </div>
        </div>`
})
export class Notfound {
    private authService = inject(AuthService);
    private router = inject(Router);

    goHome() {
        const user = this.authService.getCurrentUser();
        if (!user) {
            this.router.navigate(['/landing']);
            return;
        }
        const normalizedRole = roleKey(user.role);
        if (normalizedRole === 'SUPER_ADMIN') {
            this.router.navigate(['/admin/dashboard']);
        } else {
            this.router.navigate(['/client/dashboard']);
        }
    }
}
