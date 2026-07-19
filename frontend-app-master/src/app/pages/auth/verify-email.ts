import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { AuBtn } from '../../shared/components';
import { AuthService } from '../../core/services/auth/auth.service';
import { AppConfigService } from '../../core/services/app-config.service';
import { LocaleService } from '../../core/services/locale/locale.service';

@Component({
    selector: 'app-verify-email',
    standalone: true,
    imports: [CommonModule, RouterModule, ButtonModule, CardModule, ProgressSpinnerModule, AuBtn],
    template: `
    <div class="relative min-h-screen overflow-hidden bg-linear-to-br from-slate-50 via-white to-emerald-50 dark:from-slate-950 dark:via-slate-950 dark:to-emerald-950 flex items-center justify-center p-4 lg:p-6">
      <div class="absolute inset-x-0 top-0 h-72 bg-linear-to-b from-emerald-500/10 via-violet-400/6 to-transparent dark:from-emerald-400/12 dark:via-violet-400/8 dark:to-transparent"></div>
      <div class="absolute -top-20 left-8 h-64 w-64 rounded-full bg-emerald-400/10 blur-3xl"></div>
      <div class="absolute right-0 top-24 h-80 w-80 rounded-full bg-violet-500/10 blur-3xl"></div>

      <div class="relative max-w-lg w-full">
        <div class="backdrop-blur-xl rounded-[2rem] border border-white/60 dark:border-slate-700/70 bg-white/84 dark:bg-slate-900/84 shadow-[0_32px_110px_-62px_rgba(15,23,42,0.32)] overflow-hidden">
          <div class="relative p-8 lg:p-10 text-center">

            <a routerLink="/landing" class="inline-flex items-center gap-3 mb-8 justify-center">
              <div class="flex items-center justify-center rounded-2xl border border-white/70 dark:border-white/10 bg-white/90 dark:bg-white/5 p-2.5 shadow-sm">
                <img src="assets/logos/logo-final.png" [alt]="appConfig.platformName()" class="h-9 w-9 rounded-xl object-contain" />
              </div>
              <div>
                <div class="text-[0.68rem] uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400 font-bold">{{ t('auth.login.business_os') || 'Business OS' }}</div>
                <div class="text-lg font-black tracking-tight text-slate-900 dark:text-white">{{ appConfig.platformName() }}</div>
              </div>
            </a>

            @if (status() === 'loading') {
              <div class="py-12">
                <p-progressSpinner styleClass="w-12 h-12" strokeWidth="4" fill="transparent" animationDuration=".8s"></p-progressSpinner>
                <p class="text-slate-500 dark:text-slate-400 mt-6 text-sm">{{ t('auth.verify.verifying') || 'Verificando tu correo...' }}</p>
              </div>
            }

            @if (status() === 'success') {
              <div class="py-6">
                <div class="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-emerald-50 dark:bg-emerald-950/50 mb-6">
                  <i class="pi pi-check-circle text-4xl text-emerald-500"></i>
                </div>
                <h1 class="text-2xl font-black tracking-tight text-slate-900 dark:text-white mb-2">{{ t('auth.verify.success_title') || 'Correo verificado' }}</h1>
                <p class="text-slate-500 dark:text-slate-400 mb-8">{{ t('auth.verify.success_desc') || 'Tu direccion de correo ha sido verificada exitosamente. Ya puedes iniciar sesion.' }}</p>
                <button au-btn
                        [icon]="'pi pi-sign-in'"
                        class="w-full bg-linear-to-r! from-emerald-500! to-violet-500! border-0! text-white! font-semibold!"
                        (click)="goToLogin()">
                  {{ t('auth.success.go_login') }}
                </button>
              </div>
            }

            @if (status() === 'error') {
              <div class="py-6">
                <div class="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-red-50 dark:bg-red-950/50 mb-6">
                  <i class="pi pi-times-circle text-4xl text-red-500"></i>
                </div>
                <h1 class="text-2xl font-black tracking-tight text-slate-900 dark:text-white mb-2">{{ t('auth.verify.invalid_link_title') || 'Enlace invalido' }}</h1>
                <p class="text-slate-500 dark:text-slate-400 mb-6">{{ t('auth.verify.invalid_link_desc') || 'El enlace de verificacion es invalido o ya expiro. Solicita uno nuevo.' }}</p>
                <button au-btn
                        variant="secondary"
                        [icon]="'pi pi-envelope'"
                        class="w-full"
                        routerLink="/auth/login">
                  {{ t('auth.verify.request_new_link') || 'Solicitar nuevo enlace' }}
                </button>
              </div>
            }

          </div>
        </div>
      </div>
    </div>
  `
})
export class VerifyEmail implements OnInit {
  status = signal<'loading' | 'success' | 'error'>('loading');

  private authService = inject(AuthService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private localeService = inject(LocaleService);
  appConfig = inject(AppConfigService);

  t(key: string): string {
    return this.localeService.t(key as any);
  }

  ngOnInit() {
    const token = this.route.snapshot.params['token'] || '';
    if (!token) {
      this.status.set('error');
      return;
    }
    this.authService.verifyEmail(token).subscribe({
      next: () => this.status.set('success'),
      error: () => this.status.set('error')
    });
  }

  goToLogin() {
    this.router.navigate(['/auth/login']);
  }
}
