import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule, ActivatedRoute } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { RippleModule } from 'primeng/ripple';
import { AuthService } from '../../core/services/auth/auth.service';
import { AppConfigService } from '../../core/services/app-config.service';
import { LocaleService } from '../../core/services/locale/locale.service';
import { roleKey } from '../../core/utils/role-normalizer';

@Component({
    selector: 'app-error',
    imports: [CommonModule, ButtonModule, RippleModule, RouterModule],
    standalone: true,
    template: `
        <div class="bg-surface-50 dark:bg-surface-950 flex items-center justify-center min-h-screen min-w-screen overflow-hidden px-4">
            <div class="flex flex-col items-center justify-center">
                <div style="border-radius: 56px; padding: 0.3rem; background: linear-gradient(180deg, rgba(233, 30, 99, 0.4) 10%, rgba(33, 150, 243, 0) 30%)">
                    <div class="w-full bg-surface-0 dark:bg-surface-900 py-16 px-8 sm:px-20 flex flex-col items-center text-center" style="border-radius: 53px">
                        <div class="gap-4 flex flex-col items-center max-w-lg">
                            <div class="flex items-center gap-3 mb-2 self-start">
                                <img src="assets/logos/logo-final.png" alt="Auron Suite" class="h-12 w-12 rounded-2xl object-contain shadow-sm" />
                    <div class="text-left">
                        <div class="text-xs uppercase tracking-[0.22em] text-surface-500">{{ t('auth.error.title') }}</div>
                        <div class="text-lg font-bold text-surface-900 dark:text-surface-0">{{ t('auth.error.heading') }}</div>
                    </div>
                            </div>
                            <div class="flex justify-center items-center border-2 border-pink-500 rounded-full" style="height: 3.2rem; width: 3.2rem">
                                <i class="pi pi-fw pi-exclamation-circle text-2xl! text-pink-500"></i>
                            </div>
                            <h1 class="text-surface-900 dark:text-surface-0 font-bold text-5xl mb-2">{{ t('auth.error.heading') }}</h1>
                            <span class="text-muted-color mb-4">{{ message }}</span>
                            <div class="mb-4 flex h-32 w-32 items-center justify-center rounded-[2rem] bg-pink-500/10">
                                <img src="assets/logos/logo-final.png" alt="Auron Suite" class="h-16 w-16 rounded-2xl object-contain" />
                            </div>

                             <a *ngIf="homeRoute" (click)="goHome()" class="w-full flex items-center py-6 border-surface-300 dark:border-surface-500 border-b cursor-pointer">
                                 <span class="flex justify-center items-center border-2 border-pink-500 text-pink-500 rounded-border" style="height: 3.5rem; width: 3.5rem">
                                     <i class="pi pi-fw pi-table text-2xl!"></i>
                                 </span>
                                 <span class="ml-6 flex flex-col text-left">
                                     <span class="text-surface-900 dark:text-surface-0 lg:text-xl font-medium mb-0 block">{{ t('auth.error.go_panel') }}</span>
                                     <span class="text-surface-600 dark:text-surface-200 lg:text-xl">{{ t('auth.error.go_panel_desc') }}</span>
                                 </span>
                             </a>
                             <a (click)="retry()" class="w-full flex items-center py-6 border-surface-300 dark:border-surface-500 border-b cursor-pointer">
                                 <span class="flex justify-center items-center border-2 border-pink-500 text-pink-500 rounded-border" style="height: 3.5rem; width: 3.5rem">
                                     <i class="pi pi-fw pi-refresh text-2xl!"></i>
                                 </span>
                                 <span class="ml-6 flex flex-col text-left">
                                     <span class="text-surface-900 dark:text-surface-0 lg:text-xl font-medium mb-0">{{ t('auth.error.retry') }}</span>
                                     <span class="text-surface-600 dark:text-surface-200 lg:text-xl">{{ t('auth.error.retry_desc') }}</span>
                                 </span>
                             </a>
                             <a routerLink="/landing" class="w-full flex items-center mb-6 py-6 border-surface-300 dark:border-surface-500 border-b">
                                 <span class="flex justify-center items-center border-2 border-pink-500 text-pink-500 rounded-border" style="height: 3.5rem; width: 3.5rem">
                                     <i class="pi pi-fw pi-home text-2xl!"></i>
                                 </span>
                                 <span class="ml-6 flex fx-col text-left">
                                     <span class="text-surface-900 dark:text-surface-0 lg:text-xl font-medium mb-0 block">{{ t('auth.error.go_home') }}</span>
                                     <span class="text-surface-600 dark:text-surface-200 lg:text-xl">{{ t('auth.error.go_home_desc') }}</span>
                                 </span>
                             </a>

                            <div *ngIf="errorId" class="w-full rounded-xl bg-surface-50 dark:bg-surface-800 p-4 text-left text-sm text-muted-color">
                                <div class="flex items-start gap-3">
                                    <i class="pi pi-code text-pink-500 mt-0.5"></i>
                                     <div>
                                         <div class="font-semibold text-surface-900 dark:text-surface-0 mb-1">{{ t('auth.error.error_id') }}</div>
                                         <code class="text-xs bg-surface-200 dark:bg-surface-700 px-2 py-1 rounded">{{ errorId }}</code>
                                         <div class="mt-2 text-xs text-surface-500">{{ errorTimestamp }}</div>
                                     </div>
                                </div>
                            </div>

                                 <div class="w-full rounded-xl bg-surface-50 dark:bg-surface-800 p-4 text-left text-sm text-muted-color">
                                     <div class="flex items-start gap-3">
                                         <i class="pi pi-envelope text-pink-500 mt-0.5"></i>
                                         <div>
                                             <div class="font-semibold text-surface-900 dark:text-surface-0 mb-1">{{ t('auth.error.need_help') }}</div>
                                             <p class="mb-0">{{ t('auth.error.help_desc') }}</p>
                                             <p class="mt-2 mb-0">Email: <strong class="text-surface-900 dark:text-surface-0">{{ appConfig.supportEmail() }}</strong></p>
                                         </div>
                                     </div>
                                 </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>`
})
export class Error {
    protected message: string;
    protected homeRoute = '';
    protected errorId = '';
    protected errorTimestamp = '';
    protected appConfig = inject(AppConfigService);
    private router = inject(Router);
    private authService = inject(AuthService);
    private localeService = inject(LocaleService);

    t(key: string): string {
        return this.localeService.t(key as any);
    }

    constructor(route?: ActivatedRoute) {
        const r = route ?? inject(ActivatedRoute);
        const msg = r.snapshot.queryParams['message'];
        this.message = msg ? msg : this.t('auth.error.default_message');

        const id = r.snapshot.queryParams['errorId'];
        if (id) {
            this.errorId = id;
            const d = new Date();
            this.errorTimestamp = `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`;
        }

        const user = this.authService.getCurrentUser();
        if (user) {
            const key = roleKey(user.role);
            this.homeRoute = key === 'SUPER_ADMIN' ? '/admin/dashboard' : '/client/dashboard';
        }
    }

    goHome() {
        if (this.homeRoute) this.router.navigate([this.homeRoute]);
    }

    retry() {
        window.history.back();
    }
}
