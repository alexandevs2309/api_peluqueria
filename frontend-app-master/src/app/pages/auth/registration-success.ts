import { Component, inject, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { Subscription } from 'rxjs';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { AuBtn } from '../../shared/components';
import { AppConfigService } from '../../core/services/app-config.service';
import { LocaleService } from '../../core/services/locale/locale.service';

@Component({
  selector: 'app-registration-success',
  standalone: true,
  imports: [CommonModule, RouterModule, ButtonModule, CardModule, AuBtn],
  template: `
    <div class="relative min-h-screen overflow-hidden bg-linear-to-br from-slate-50 via-white to-emerald-50 dark:from-slate-950 dark:via-slate-950 dark:to-emerald-950 flex items-center justify-center p-4 lg:p-6">
      <div class="absolute inset-x-0 top-0 h-72 bg-linear-to-b from-emerald-500/10 via-violet-400/6 to-transparent dark:from-emerald-400/12 dark:via-violet-400/8 dark:to-transparent"></div>
      <div class="absolute -top-20 left-8 h-64 w-64 rounded-full bg-emerald-400/10 blur-3xl"></div>
      <div class="absolute right-0 top-24 h-80 w-80 rounded-full bg-violet-500/10 blur-3xl"></div>
      <div class="absolute inset-0 opacity-[0.035] dark:opacity-[0.06]" style="background-image: radial-gradient(circle at 1px 1px, rgba(15,23,42,0.28) 1px, transparent 0); background-size: 34px 34px;"></div>

      <div class="relative max-w-4xl w-full">
        <div class="backdrop-blur-xl rounded-[2rem] border border-white/60 dark:border-slate-700/70 bg-white/84 dark:bg-slate-900/84 shadow-[0_32px_110px_-62px_rgba(15,23,42,0.32)] overflow-hidden">
          <div class="absolute inset-0 rounded-[2rem] bg-linear-to-r from-emerald-500/16 via-violet-400/10 to-emerald-500/16 p-px">
            <div class="w-full h-full rounded-[2rem] bg-white/90 dark:bg-slate-900/90"></div>
          </div>

          <div class="relative p-8 lg:p-10">
            <a routerLink="/landing" class="inline-flex items-center gap-3 mb-8">
              <div class="flex items-center justify-center rounded-2xl border border-white/70 dark:border-white/10 bg-white/90 dark:bg-white/5 p-2.5 shadow-sm">
                <img src="assets/logos/logo-final.png" [alt]="appConfig.platformName()" class="h-9 w-9 rounded-xl object-contain" />
              </div>
              <div>
                <div class="text-[0.68rem] uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400 font-bold">{{ t('auth.login.business_os') || 'Business OS' }}</div>
                <div class="text-lg font-black tracking-tight text-slate-900 dark:text-white">{{ appConfig.platformName() }}</div>
              </div>
            </a>

            <div class="grid gap-8 lg:grid-cols-[minmax(0,1.1fr)_minmax(20rem,0.9fr)] items-start">
              <div>
                <div class="inline-flex items-center gap-2 rounded-full bg-emerald-50 dark:bg-emerald-950/40 px-4 py-2 text-sm font-semibold text-emerald-700 dark:text-emerald-300 mb-5">
                  <i class="pi pi-check-circle"></i>
                  {{ t('auth.success.badge') }}
                </div>

                <h1 class="text-4xl lg:text-5xl font-black tracking-tight text-slate-900 dark:text-white mb-4">{{ t('auth.success.title') }}</h1>
                <p class="text-base lg:text-lg leading-7 text-slate-600 dark:text-slate-300 mb-8">
                  {{ t('auth.success.description').replace('{business}', businessName) }}
                </p>

                <div class="rounded-[1.6rem] border border-emerald-200/80 dark:border-emerald-900/50 bg-emerald-50/90 dark:bg-emerald-950/25 p-5 mb-6">
                  <div class="flex items-start gap-4">
                    <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-emerald-500 text-white">
                      <i class="pi pi-envelope text-xl"></i>
                    </div>
                    <div>
                      <div class="font-semibold text-emerald-900 dark:text-emerald-100 mb-1">{{ t('auth.success.credentials_sent') }}</div>
                      <div class="text-sm text-emerald-800 dark:text-emerald-300 mb-3">{{ t('auth.success.check_email') }}</div>
                      <div class="rounded-xl border border-white/70 dark:border-white/10 bg-white/80 dark:bg-slate-900/70 px-4 py-3 font-mono text-sm text-slate-900 dark:text-slate-100">
                        {{ email }}
                      </div>
                      @if (tempPassword) {
                        <div class="mt-3 rounded-xl border border-amber-200/80 dark:border-amber-800/50 bg-amber-50/90 dark:bg-amber-950/30 px-4 py-3">
                          <div class="text-xs font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-400 mb-1">{{ t('auth.success.temp_password') }}</div>
                          <div class="font-mono text-sm text-slate-900 dark:text-slate-100 break-all select-all">{{ tempPassword }}</div>
                        </div>
                      }
                      @if (subdomain) {
                        <div class="mt-3 rounded-xl border border-violet-200/80 dark:border-violet-800/50 bg-violet-50/90 dark:bg-violet-950/30 px-4 py-3">
                          <div class="text-xs font-semibold uppercase tracking-wide text-violet-700 dark:text-violet-400 mb-1">{{ t('auth.success.subdomain') }}</div>
                          <div class="font-mono text-sm text-slate-900 dark:text-slate-100 break-all select-all">{{ subdomain }}</div>
                        </div>
                      }
                    </div>
                  </div>
                </div>

                <div class="rounded-[1.6rem] border border-slate-200 dark:border-slate-700 bg-slate-50/90 dark:bg-slate-800/75 p-6">
                  <h3 class="font-bold text-slate-900 dark:text-white mb-4">{{ t('auth.success.next_steps') }}</h3>
                  <div class="space-y-4">
                    <div class="flex gap-3">
                      <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-violet-600 text-sm font-bold text-white">1</div>
                      <div class="text-sm text-slate-600 dark:text-slate-300">{{ t('auth.success.step1') }}</div>
                    </div>
                    <div class="flex gap-3">
                      <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-violet-600 text-sm font-bold text-white">2</div>
                      <div class="text-sm text-slate-600 dark:text-slate-300">{{ t('auth.success.step2') }}</div>
                    </div>
                    <div class="flex gap-3">
                      <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-violet-600 text-sm font-bold text-white">3</div>
                      <div class="text-sm text-slate-600 dark:text-slate-300">{{ t('auth.success.step3') }}</div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="space-y-5">
                <div class="rounded-[1.6rem] border border-slate-200 dark:border-slate-700 bg-white/88 dark:bg-slate-900/70 p-6 shadow-[0_24px_80px_-56px_rgba(15,23,42,0.28)]">
                  <div class="text-xs uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400 mb-3">{{ t('auth.success.account_summary') }}</div>
                  <div class="space-y-4">
                    <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/70 p-4">
                      <div class="text-sm text-slate-500 dark:text-slate-400">{{ t('auth.register.business_label') }}</div>
                      <div class="font-semibold text-slate-900 dark:text-white">{{ businessName }}</div>
                    </div>
                    <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/70 p-4">
                      <div class="text-sm text-slate-500 dark:text-slate-400">{{ t('auth.success.plan') }}</div>
                      <div class="font-semibold text-slate-900 dark:text-white">
                        {{ planName }} - 
                        @if (billingInterval === 'year') {
                          \${{ (planPrice / 12) | number:'1.1-2' }}/mes ({{ t('auth.register.billed_annually') }} \${{ planPrice | number:'1.1-2' }}/{{ t('auth.register.year_suffix') }})
                        } @else {
                          \${{ planPrice | number:'1.1-2' }}/mes
                        }
                      </div>
                    </div>
                    <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/70 p-4">
                      <div class="text-sm text-slate-500 dark:text-slate-400">{{ t('auth.success.initial_status') }}</div>
                      <div class="font-semibold text-emerald-600 dark:text-emerald-300">{{ t('auth.success.trial_active') }}</div>
                    </div>
                  </div>
                </div>

                <div class="rounded-[1.6rem] border border-violet-200/80 dark:border-violet-900/50 bg-violet-50/90 dark:bg-violet-950/25 p-5">
                  <div class="flex items-start gap-3">
                    <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-violet-500 text-white">
                      <i class="pi pi-info-circle"></i>
                    </div>
                    <div>
                      <div class="font-semibold text-violet-900 dark:text-violet-100 mb-1">{{ t('auth.success.no_email_title') }}</div>
                      <div class="text-sm text-violet-800 dark:text-violet-300 leading-6">
                        {{ t('auth.success.no_email_desc').replace('{email}', appConfig.supportEmail()) }}
                      </div>
                    </div>
                  </div>
                </div>

                <div class="flex flex-col gap-3">
                  <button au-btn
                          [icon]="'pi pi-sign-in'"
                          class="w-full bg-linear-to-r! from-emerald-500! to-violet-500! border-0! text-white! font-semibold!"
                          (click)="goToLogin()">
                    {{ t('auth.success.go_login') }}
                  </button>
                  <button au-btn
                          variant="secondary"
                          [icon]="'pi pi-arrow-left'"
                          class="w-full"
                          routerLink="/landing">
                    {{ t('auth.success.go_home') }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
})
export class RegistrationSuccess implements OnInit, OnDestroy {
  private queryParamsSub: Subscription | undefined;
  businessName: string = '';
  email: string = '';
  planName: string = '';
  planPrice: number = 0;
  tempPassword: string = '';
  subdomain: string = '';
  billingInterval: string = 'month';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    public appConfig: AppConfigService,
    private localeService: LocaleService
  ) {
    const nav = this.router.getCurrentNavigation();
    this.tempPassword = nav?.extras?.state?.['tempPassword'] || '';
  }

  t(key: string): string {
    return this.localeService.t(key as any);
  }

  ngOnInit() {
    this.queryParamsSub = this.route.queryParams.subscribe(params => {
      this.businessName = params['businessName'] || 'Tu Barberia';
      this.email = params['email'] || '';
      this.planName = params['planName'] || 'Plan';
      this.planPrice = params['planPrice'] || 0;
      this.subdomain = params['subdomain'] || '';
      this.billingInterval = params['billing_interval'] || 'month';
    });
  }

  ngOnDestroy() {
    this.queryParamsSub?.unsubscribe();
  }

  goToLogin() {
    this.router.navigate(['/auth/login'], {
      queryParams: {
        email: this.email,
        message: 'check_email'
      }
    });
  }

  showEmailHelp() {
    this.router.navigate(['/auth/login'], {
      queryParams: {
        email: this.email,
        message: 'check_spam'
      }
    });
  }
}
