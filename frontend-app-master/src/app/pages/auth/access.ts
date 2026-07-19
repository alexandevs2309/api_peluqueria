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
    selector: 'app-access',
    standalone: true,
    imports: [CommonModule, ButtonModule, RouterModule, RippleModule],
    template: `
        <div class="bg-surface-50 dark:bg-surface-950 flex items-center justify-center min-h-screen min-w-screen overflow-hidden px-4">
            <div class="flex flex-col items-center justify-center">
                <div style="border-radius: 56px; padding: 0.3rem; background: linear-gradient(180deg, rgba(247, 149, 48, 0.4) 10%, rgba(247, 149, 48, 0) 30%)">
                    <div class="w-full bg-surface-0 dark:bg-surface-900 py-16 px-8 sm:px-20 flex flex-col items-center text-center" style="border-radius: 53px">
                        <div class="gap-4 flex flex-col items-center max-w-lg">
                            <div class="flex items-center gap-3 mb-2 self-start">
                                <img src="assets/logos/logo-final.png" alt="Auron Suite" class="h-12 w-12 rounded-2xl object-contain shadow-sm" />
                    <div class="text-left">
                        <div class="text-xs uppercase tracking-[0.22em] text-surface-500">{{ t('auth.access.title') }}</div>
                        <div class="text-lg font-bold text-surface-900 dark:text-surface-0">{{ t('auth.access.subtitle') }}</div>
                    </div>
                            </div>
                            <div class="flex justify-center items-center border-2 border-orange-500 rounded-full" style="width: 3.2rem; height: 3.2rem">
                                <i class="text-orange-500 pi pi-fw pi-lock text-2xl!"></i>
                            </div>
                            <h1 class="text-surface-900 dark:text-surface-0 font-bold text-4xl lg:text-5xl mb-2">{{ t('auth.access.heading') }}</h1>
                            <span class="text-muted-color mb-4">{{ message }}</span>
                            <div class="mb-4 flex h-32 w-32 items-center justify-center rounded-4xl bg-orange-500/10">
                                <img src="assets/logos/logo-final.png" alt="Auron Suite" class="h-16 w-16 rounded-2xl object-contain" />
                            </div>

                             <a *ngIf="homeRoute" (click)="goHome()" class="w-full flex items-center py-6 border-surface-300 dark:border-surface-500 border-b cursor-pointer">
                                 <span class="flex justify-center items-center border-2 border-orange-500 text-orange-500 rounded-border" style="height: 3.5rem; width: 3.5rem">
                                     <i class="pi pi-fw pi-table text-2xl!"></i>
                                 </span>
                                 <span class="ml-6 flex flex-col text-left">
                                     <span class="text-surface-900 dark:text-surface-0 lg:text-xl font-medium mb-0 block">{{ t('auth.access.go_panel') }}</span>
                                     <span class="text-surface-600 dark:text-surface-200 lg:text-xl">{{ t('auth.access.go_panel_desc') }}</span>
                                 </span>
                             </a>
                             <a routerLink="/landing" class="w-full flex items-center py-6 border-surface-300 dark:border-surface-500 border-b">
                                 <span class="flex justify-center items-center border-2 border-orange-500 text-orange-500 rounded-border" style="height: 3.5rem; width: 3.5rem">
                                     <i class="pi pi-fw pi-question-circle text-2xl!"></i>
                                 </span>
                                 <span class="ml-6 flex flex-col text-left">
                                     <span class="text-surface-900 dark:text-surface-0 lg:text-xl font-medium mb-0">{{ t('auth.access.go_landing') }}</span>
                                     <span class="text-surface-600 dark:text-surface-200 lg:text-xl">{{ t('auth.access.go_landing_desc') }}</span>
                                 </span>
                             </a>
                             <a routerLink="/auth/login" class="w-full flex items-center mb-6 py-6 border-surface-300 dark:border-surface-500 border-b">
                                 <span class="flex justify-center items-center border-2 border-orange-500 text-orange-500 rounded-border" style="height: 3.5rem; width: 3.5rem">
                                     <i class="pi pi-fw pi-unlock text-2xl!"></i>
                                 </span>
                                 <span class="ml-6 flex flex-col text-left">
                                     <span class="text-surface-900 dark:text-surface-0 lg:text-xl font-medium mb-0">{{ t('auth.access.go_login') }}</span>
                                     <span class="text-surface-600 dark:text-surface-200 lg:text-xl">{{ t('auth.access.go_login_desc') }}</span>
                                 </span>
                             </a>

                             <div class="w-full rounded-xl bg-surface-50 dark:bg-surface-800 p-4 text-left text-sm text-muted-color">
                                 <div class="flex items-start gap-3">
                                     <i class="pi pi-info-circle text-orange-500 mt-0.5"></i>
                                     <div>
                                         <div class="font-semibold text-surface-900 dark:text-surface-0 mb-1">{{ t('auth.access.need_permissions') }}</div>
                                         <p class="mb-0">{{ t('auth.access.contact_admin') }}</p>
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
export class Access {
    protected message: string;
    protected homeRoute = '';
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
        this.message = msg ? msg : this.t('auth.access.default_message');

        const user = this.authService.getCurrentUser();
        if (user) {
            const key = roleKey(user.role);
            this.homeRoute = key === 'SUPER_ADMIN' ? '/admin/dashboard' : '/client/dashboard';
        }
    }

    goHome() {
        if (this.homeRoute) this.router.navigate([this.homeRoute]);
    }
}
