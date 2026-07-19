import { Component, HostListener, OnInit, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { CardModule } from 'primeng/card';
import { DividerModule } from 'primeng/divider';
import { ToastModule } from 'primeng/toast';
import { Router } from '@angular/router';
import { TrialService, TrialStatus } from '../../../core/services/trial.service';
import { SubscriptionService } from '../../../core/services/subscription/subscription.service';
import { MessageService } from 'primeng/api';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { I18nPipe } from '../../../core/pipes/i18n.pipe';
import { AuBtn } from '../../../shared/components';

@Component({
  selector: 'app-payment',
  standalone: true,
  imports: [CommonModule, CardModule, DividerModule, ToastModule, I18nPipe, AuBtn],
  providers: [MessageService],
  template: `
    <p-toast />

    <div class="plans-shell">
      <div class="plans-header">
        <div>
          <div class="plans-header__eyebrow">{{ 'payment.header.eyebrow' | t }}</div>
          <h1 class="plans-header__title display-3">{{ 'payment.header.title' | t }}</h1>
          <p class="plans-header__copy">{{ 'payment.header.copy' | t }}</p>
          
          <div class="billing-toggle-container">
            <div class="billing-toggle-bar">
              <button type="button" 
                      class="billing-toggle-btn"
                      [class.is-active]="billingInterval === 'month'"
                      (click)="setBillingInterval('month')">
                {{ 'payment.billing.monthly' | t }}
              </button>
              <button type="button" 
                      class="billing-toggle-btn"
                      [class.is-active]="billingInterval === 'year'"
                      (click)="setBillingInterval('year')">
                {{ 'payment.billing.annually' | t }}
                <span class="billing-toggle-discount">{{ 'payment.billing.discount' | t }}</span>
              </button>
            </div>
          </div>
        </div>
        <div class="plans-header__trust" *ngIf="getRecommendedPlan() as recommended">
          <div class="plans-header__trust-card">
            <span class="plans-header__trust-label">{{ 'payment.recommended' | t }}</span>
            <strong>{{ recommended.display_name || recommended.name }}</strong>
            <span *ngIf="billingInterval === 'month'">\${{ recommended.price | number:'1.1-2' }}{{ t('payment.billing.monthly_note') }}</span>
            <span *ngIf="billingInterval === 'year'">\${{ (recommended.annual_price / 12) | number:'1.1-2' }}{{ t('payment.billing.monthly_note') }}</span>
            <span *ngIf="billingInterval === 'year'" class="recommended-annual-note">{{ t('payment.billing.billed_annually_note').replace('{price}', (recommended.annual_price | number:'1.1-2') ?? '') }}</span>
            <button au-btn variant="primary" [icon]="'pi pi-arrow-right'" (click)="selectPlan(recommended)" class="w-full">{{ 'payment.choose_recommended' | t }}</button>
          </div>
        </div>
      </div>

      <div *ngIf="currentSubscription" class="current-sub-card">
        <div class="current-sub-card__body">
          <div class="current-sub-card__info">
            <div class="current-sub-card__label">{{ 'payment.current_plan' | t }}</div>
            <div class="current-sub-card__plan">{{ currentSubscription.plan_name || currentSubscription.plan?.name || '—' }}</div>
            <div class="current-sub-card__dates">
              <span *ngIf="currentSubscription.start_date">{{ t('payment.dates.start').replace('{date}', (currentSubscription.start_date | date:'dd/MM/yyyy') ?? '') }}</span>
              <span *ngIf="currentSubscription.end_date">{{ t('payment.dates.end').replace('{date}', (currentSubscription.end_date | date:'dd/MM/yyyy') ?? '') }}</span>
            </div>
            <div *ngIf="currentSubscription.is_cancelled" class="current-sub-card__cancelled-badge">
              <i class="pi pi-info-circle"></i>
              {{ t('payment.cancelled_grace').replace('{date}', (currentSubscription.access_until | date:'dd/MM/yyyy') ?? '') }}
            </div>
          </div>
          <div class="current-sub-card__actions">
            <button au-btn variant="secondary" [icon]="'pi pi-arrow-right'" (click)="goToProfile()">{{ 'payment.manage_account' | t }}</button>
          </div>
        </div>
      </div>

      <div *ngIf="loading" class="plans-loading">
        <i class="pi pi-spin pi-spinner"></i> {{ 'payment.loading_plans' | t }}
      </div>

      <div *ngIf="!loading" class="plans-list">
        <div *ngFor="let plan of plans" class="plan-row" [class.plan-row--recommended]="plan.recommended" (click)="selectPlan(plan)">
          <div class="plan-row__left">
            <div class="plan-row__name">{{ plan.display_name || plan.name }}</div>
            <div class="plan-row__helper">{{ plan.recommended ? t('payment.plans.recommended_helper') : t('payment.plans.standard_helper') }}</div>
            <div class="plan-row__features">
              <span *ngFor="let f of plan.features" class="plan-row__feature">
                <i class="pi pi-check"></i> {{ f }}
              </span>
            </div>
          </div>
          <div class="plan-row__right">
            <div class="plan-row__price">
              <strong *ngIf="billingInterval === 'month'">\${{ plan.price | number:'1.1-2' }}</strong>
              <strong *ngIf="billingInterval === 'year'">\${{ (plan.annual_price / 12) | number:'1.1-2' }}</strong>
              <span>{{ t('payment.billing.monthly_note') }}</span>
              <div *ngIf="billingInterval === 'year'" class="plan-row__annual-note">
                {{ t('payment.billing.billed_annually_note').replace('{price}', (plan.annual_price | number:'1.1-2') ?? '') }}
              </div>
            </div>
            <button au-btn [variant]="plan.recommended ? 'primary' : 'secondary'" (click)="selectPlan(plan); $event.stopPropagation()">{{ plan.recommended ? t('payment.plans.choose_recommended') : t('payment.plans.choose_plan') }}</button>
          </div>
        </div>
      </div>
    </div>

    <style>
    .plans-shell { max-width: 720px; margin: 0 auto; padding: 1.5rem; display: flex; flex-direction: column; gap: 1.25rem; }

    .plans-header { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(16rem, 0.85fr); align-items: stretch; gap: 1rem; }
    .plans-header__eyebrow { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; color: var(--text-color-secondary); }
    .plans-header__title { font-size: clamp(2rem, 5vw, 3.1rem); line-height: 0.98; font-weight: 900; color: var(--text-color); margin: 0.3rem 0 0.75rem; }
    .plans-header__copy { margin: 0; max-width: 34rem; color: var(--text-color-secondary); line-height: 1.55; }
    .plans-header__trust { display: flex; }
    .plans-header__trust-card {
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
      padding: 1.15rem;
      border-radius: 1rem;
      background: #0f172a;
      color: #e2e8f0;
      box-shadow: 0 16px 40px rgba(15, 23, 42, 0.18);
    }
    .plans-header__trust-label { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.16em; color: #94a3b8; }
    .plans-header__trust-card strong { font-size: 1.45rem; line-height: 1.05; }
    .plans-header__trust-card strong { font-size: 1.45rem; line-height: 1.05; }

    .plans-loading { display: flex; align-items: center; gap: 0.5rem; color: var(--text-color-secondary); padding: 2rem; justify-content: center; }

    .plans-list { display: flex; flex-direction: column; gap: 0.5rem; }

    .plan-row {
      display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap;
      padding: 1rem 1.25rem;
      border: 1px solid var(--surface-border);
      background: var(--surface-card);
      border-radius: 0.85rem;
      cursor: pointer;
      transition: border-color 120ms, box-shadow 120ms;
    }

    .plan-row:hover { border-color: var(--brand); box-shadow: 0 0 0 1px var(--brand); }

    .plan-row--recommended {
      border-color: #10b981;
      box-shadow: 0 0 0 1px #10b981;
    }

    .plan-row__left { flex: 1; min-width: 0; }
    .plan-row__name { font-size: 1rem; font-weight: 700; color: var(--text-color); margin-bottom: 0.4rem; }
    .plan-row__helper { font-size: 0.82rem; color: var(--text-color-secondary); margin-bottom: 0.55rem; }
    .plan-row__features { display: flex; flex-wrap: wrap; gap: 0.35rem 0.75rem; }
    .plan-row__feature { font-size: 0.78rem; color: var(--text-color-secondary); display: flex; align-items: center; gap: 0.25rem; }
    .plan-row__feature .pi-check { color: #10b981; font-size: 0.7rem; }

    .plan-row__right { display: flex; align-items: center; gap: 1rem; flex-shrink: 0; }
    .plan-row__price { text-align: right; }
    .plan-row__price strong { font-size: 1.4rem; font-weight: 800; color: var(--text-color); }
    .plan-row__price span { font-size: 0.82rem; color: var(--text-color-secondary); }

    .current-sub-card {
      border: 1px solid var(--surface-border);
      background: var(--surface-card);
      border-radius: 0.85rem;
      overflow: hidden;
    }
    .current-sub-card__body {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      padding: 1.25rem;
      flex-wrap: wrap;
    }
    .current-sub-card__info { flex: 1; min-width: 0; }
    .current-sub-card__label { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; color: var(--text-color-secondary); margin-bottom: 0.25rem; }
    .current-sub-card__plan { font-size: 1.2rem; font-weight: 800; color: var(--text-color); }
    .current-sub-card__dates { font-size: 0.8rem; color: var(--text-color-secondary); margin-top: 0.15rem; }
    .current-sub-card__cancelled-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      margin-top: 0.5rem;
      padding: 0.3rem 0.65rem;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 600;
      background: #fef3c7;
      color: #92400e;
    }
    :host-context(.app-dark) .current-sub-card__cancelled-badge {
      background: rgba(251, 191, 36, 0.12);
      color: #fbbf24;
    }
    .current-sub-card__actions { display: flex; gap: 0.5rem; flex-shrink: 0; }

    .billing-toggle-container {
      display: flex;
      margin-top: 1.25rem;
    }
    .billing-toggle-bar {
      display: inline-flex;
      border-radius: 9999px;
      background: var(--surface-hover);
      padding: 3px;
      border: 1px solid var(--surface-border);
    }
    .billing-toggle-btn {
      position: relative;
      width: 100px;
      border-radius: 9999px;
      padding: 0.4rem 0;
      font-size: 0.78rem;
      font-weight: 700;
      border: none;
      background: transparent;
      cursor: pointer;
      color: var(--text-color-secondary);
      transition: all 180ms ease-in-out;
    }
    .billing-toggle-btn.is-active {
      background: var(--brand);
      color: var(--p-primary-contrast-color);
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
    }
    .billing-toggle-discount {
      position: absolute;
      top: -8px;
      right: -6px;
      background: #10b981;
      color: white;
      font-size: 0.55rem;
      font-weight: 800;
      padding: 0.05rem 0.3rem;
      border-radius: 9999px;
      line-height: 1;
    }
    .plan-row__annual-note {
      font-size: 0.72rem;
      color: #10b981;
      font-weight: 600;
      margin-top: 0.15rem;
    }
    .recommended-annual-note {
      font-size: 0.72rem;
      color: #34d399;
      font-weight: 500;
    }

    @media (max-width: 860px) {
      .plans-header { grid-template-columns: 1fr; }
    }
    </style>
  `
})
export class PaymentComponent implements OnInit {
  trialStatus: TrialStatus | null = null;
  plans: any[] = [];
  loading = false;
  recommendedPlanNameFromState: string | null = null;
  currentSubscription: any = null;
  
  billingInterval: 'month' | 'year' = 'month';

  private trialService = inject(TrialService);
  private subscriptionService = inject(SubscriptionService);
  private router = inject(Router);
  private messageService = inject(MessageService);
  private destroyRef = inject(DestroyRef);
  private localeService = inject(LocaleService);

  ngOnInit() {
    this.trialStatus = this.trialService.getCurrentTrialStatus();
    this.recommendedPlanNameFromState = history.state?.recommendedPlanName || null;
    this.loadSubscription();
    this.loadPlans();
  }

  t(key: string): string {
    return this.localeService.t(key as any);
  }

  goToProfile() {
    this.router.navigate(['/client/profile']);
  }

  loadSubscription() {
    this.subscriptionService.getUserSubscriptions().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (data: any) => {
        const subs = Array.isArray(data) ? data : (data.results || []);
        if (subs.length > 0) {
          this.currentSubscription = subs[0];
        }
      },
      error: () => {
        this.currentSubscription = null;
      }
    });
  }

  loadPlans() {
    this.loading = true;
    this.subscriptionService.getPlans().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (data: any) => {
        const allPlans = Array.isArray(data) ? data : (data.results || []);
        this.plans = allPlans
          .filter((plan: any) => plan.is_active !== false && plan.is_public !== false)
          .map((plan: any) => {
            const priceVal = Number(plan.price ?? 0);
            const annualPriceVal = plan.annual_price !== undefined && plan.annual_price !== null
              ? Number(plan.annual_price)
              : priceVal * 12 * 0.8;
            return {
              ...plan,
              price: priceVal,
              annual_price: annualPriceVal,
              recommended: this.isRecommendedPlan(plan),
              features: this.getFeaturesList(plan.features)
            };
          });
        this.loading = false;
      },
      error: (error: any) => {
        this.messageService.add({
          severity: 'error',
          summary: this.t('common.error'),
          detail: this.t('payment.toast.load_error')
        });
        this.loading = false;
      }
    });
  }

  getFeaturesList(features: any): string[] {
    if (!features || typeof features !== 'object') return [];

    const featureNames: { [key: string]: string } = {
      'appointments': this.t('payment.features.appointments'),
      'reports': this.t('payment.features.reports'),
      'multi_location': this.t('payment.features.multi_location'),
      'custom_branding': this.t('payment.features.custom_branding'),
      'priority_support': this.t('payment.features.priority_support'),
      'export_reports': this.t('payment.features.export_reports'),
      'whatsapp_notifications': this.t('payment.features.whatsapp_notifications')
    };

    return Object.entries(features)
      .filter(([key, value]) => value === true)
      .map(([key]) => featureNames[key] || key);
  }

  setBillingInterval(interval: 'month' | 'year') {
    this.billingInterval = interval;
  }

  selectPlan(plan: any) {
    this.router.navigate(['/client/checkout'], {
      state: { 
        plan: plan,
        billingInterval: this.billingInterval
      }
    });
  }

  getRecommendedPlan(): any | null {
    return this.plans.find((plan) => plan.recommended) || this.plans[0] || null;
  }

  @HostListener('document:keydown.enter', ['$event'])
  handleEnterShortcut(event: KeyboardEvent): void {
    const target = event.target as HTMLElement | null;
    const tag = target?.tagName?.toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select' || this.loading) {
      return;
    }

    const recommended = this.getRecommendedPlan();
    if (recommended) {
      event.preventDefault();
      this.selectPlan(recommended);
    }
  }

  private isRecommendedPlan(plan: any): boolean {
    const normalizedRecommended = String(this.recommendedPlanNameFromState || '').trim().toLowerCase();
    const normalizedPlanName = String(plan?.name || '').trim().toLowerCase();
    const normalizedDisplayName = String(plan?.get_name_display || '').trim().toLowerCase();

    if (normalizedRecommended) {
      return normalizedPlanName === normalizedRecommended || normalizedDisplayName === normalizedRecommended;
    }

    return normalizedPlanName === 'standard';
  }
}
