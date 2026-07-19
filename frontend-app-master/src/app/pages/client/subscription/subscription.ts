import { Component, HostListener, OnInit, OnDestroy, DestroyRef, inject, signal,  } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CardModule } from 'primeng/card';
import { CheckboxModule } from 'primeng/checkbox';
import { InputTextModule } from 'primeng/inputtext';
import { ToastModule } from 'primeng/toast';
import { ActivatedRoute, Router } from '@angular/router';
import { SubscriptionService } from '../../../core/services/subscription/subscription.service';
import { PaypalReturnRecoveryService } from '../../../core/services/paypal-return-recovery.service';
import { TrialService,  } from '../../../core/services/trial.service';
import { MessageService } from 'primeng/api';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { I18nPipe } from '../../../core/pipes/i18n.pipe';
import { AuBtn, AuSkeleton } from '../../../shared/components';

@Component({
  selector: 'app-subscription',
  standalone: true,
  imports: [CommonModule, FormsModule, CardModule, CheckboxModule, InputTextModule, ToastModule, I18nPipe, AuBtn, AuSkeleton],
  providers: [MessageService],
  template: `
    <p-toast />

    <!-- STEP 1: Plan Listing -->
    @if (step() === 'plans') {
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
                        (click)="billingInterval = 'month'">
                  {{ 'payment.billing.monthly' | t }}
                </button>
                <button type="button" 
                        class="billing-toggle-btn"
                        [class.is-active]="billingInterval === 'year'"
                        (click)="billingInterval = 'year'">
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

        @if (currentSubscription) {
          <div class="current-sub-card">
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
                <button au-btn variant="secondary" [icon]="'pi pi-user'" (click)="goToProfile()">{{ 'payment.manage_account' | t }}</button>
              </div>
            </div>
          </div>
        }

        @if (loadingPlans()) {
          <div class="plans-loading">
            <au-skeleton></au-skeleton>
            <span>{{ 'payment.loading_plans' | t }}</span>
          </div>
        }

        @if (!loadingPlans()) {
          <div class="plans-list">
            @for (plan of plans(); track plan.id) {
              <div class="plan-row" [class.plan-row--recommended]="plan.recommended" (click)="selectPlan(plan)">
                <div class="plan-row__left">
                  <div class="plan-row__name">{{ plan.display_name || plan.name }}</div>
                  <div class="plan-row__helper">{{ plan.recommended ? t('payment.plans.recommended_helper') : t('payment.plans.standard_helper') }}</div>
                  <div class="plan-row__features">
                    @for (f of plan.features; track f) {
                      <span class="plan-row__feature">
                        <i class="pi pi-check"></i> {{ f }}
                      </span>
                    }
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
            }
          </div>
        }
      </div>
    }

    <!-- STEP 2: Checkout -->
    @if (step() === 'checkout' && selectedPlan()) {
      <div class="checkout-shell au-module-card">
        <div class="checkout-header">
          <div>
            <span class="checkout-header__eyebrow">{{ 'checkout.header.eyebrow' | t }}</span>
            <h1>{{ 'checkout.header.title' | t }}</h1>
            <p>{{ 'checkout.header.desc' | t }}</p>
          </div>
        </div>

        <div class="checkout-billing-cycle">
          <label class="checkout-billing-cycle__label">{{ 'checkout.billing_cycle' | t }}</label>
          <div class="checkout-cycle-toggle">
            <button type="button"
                    class="checkout-cycle-btn"
                    [class.is-active]="billingInterval === 'month'"
                    (click)="setBillingInterval('month')">
              {{ 'checkout.billing.monthly' | t }}
            </button>
            <button type="button"
                    class="checkout-cycle-btn relative"
                    [class.is-active]="billingInterval === 'year'"
                    (click)="setBillingInterval('year')">
              {{ 'checkout.billing.annually' | t }}
              <span class="discount-badge">{{ 'checkout.billing.discount' | t }}</span>
            </button>
          </div>
        </div>

        <div class="checkout-summary">
          <div class="checkout-summary__plan">
            <span class="checkout-summary__label">{{ 'checkout.summary.plan' | t }}</span>
            <strong>{{ selectedPlan()!.display_name || selectedPlan()!.name }}</strong>
          </div>
          <div class="checkout-summary__price">
            <strong>\${{ getTotalAmount() }}</strong>
            <span>{{ billingInterval === 'year' ? t('checkout.summary.annually_period') : (enableAutoRenew ? t('checkout.summary.monthly_auto') : (selectedMonths === 1 ? t('checkout.summary.months_count').replace('{count}', '1') : t('checkout.summary.months_count_plural').replace('{count}', selectedMonths.toString()))) }}</span>
          </div>
        </div>

        <div class="checkout-total-panel">
          <span class="checkout-total-panel__label">{{ 'checkout.total_to_charge' | t }}</span>
          <strong class="checkout-total-panel__amount">\${{ getTotalAmount() }}</strong>
          <div class="checkout-total-panel__note">
            {{ billingInterval === 'year' ? t('checkout.total_note_annually') : t('checkout.total_note_monthly') }}
          </div>
        </div>

        <div class="checkout-options">
          @if (billingInterval === 'month') {
            <div class="checkout-options__months">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <label>{{ 'checkout.months_label' | t }}</label>
                <div class="checkout-autorenew-toggle" style="display: flex; align-items: center; gap: 0.5rem;">
                  <p-checkbox [(ngModel)]="enableAutoRenew" [binary]="true" inputId="auto_renew"></p-checkbox>
                  <label for="auto_renew" style="cursor: pointer; margin: 0; font-size: 0.85rem; color: var(--text-color-secondary);">{{ 'checkout.auto_renew' | t }}</label>
                </div>
              </div>
              <div class="checkout-months-grid">
                @for (m of monthOptions; track m) {
                  <button type="button"
                    class="checkout-month-btn" [class.is-active]="selectedMonths === m && !enableAutoRenew"
                    [disabled]="enableAutoRenew" (click)="selectedMonths = m">
                    {{ m }}
                  </button>
                }
              </div>
            </div>
          } @else {
            <div class="checkout-options__months">
              <label>{{ 'checkout.period_label' | t }}</label>
              <span class="checkout-annual-locked-text">
                <i class="pi pi-check-circle"></i> {{ 'checkout.annual_locked_text' | t }}
              </span>
            </div>
          }
        </div>

        <div class="checkout-payment-method">
          <label class="checkout-payment-method__label">{{ 'checkout.payment_method' | t }}</label>
          <div class="checkout-payment-toggle">
            <button type="button"
                    class="checkout-payment-btn"
                    [class.is-active]="paymentMethod === 'card'"
                    (click)="paymentMethod = 'card'">
              <i class="pi pi-credit-card"></i> {{ 'checkout.method_card' | t }}
            </button>
            <button type="button"
                    class="checkout-payment-btn"
                    [class.is-active]="paymentMethod === 'paypal'"
                    (click)="paymentMethod = 'paypal'">
              <i class="pi pi-paypal"></i> {{ 'checkout.method_paypal' | t }}
            </button>
          </div>
        </div>

        @if (paymentMethod === 'card') {
          <div class="checkout-card-section">
            <label class="checkout-card-label">{{ 'checkout.how_it_works' | t }}</label>
            <div class="checkout-card-host checkout-card-host--card">
              <strong>1.</strong> {{ 'checkout.step1' | t }}
              <strong>2.</strong> {{ 'checkout.step2' | t }}
              <strong>3.</strong> {{ 'checkout.step3' | t }}
            </div>
            <div class="checkout-azul-form">
              <div class="checkout-azul-field">
                <label>{{ 'checkout.azul.cardholder' | t }}</label>
                <input pInputText type="text" [(ngModel)]="cardHolder" placeholder="Juan Perez" />
              </div>
              <div class="checkout-azul-field">
                <label>{{ 'checkout.azul.card_number' | t }}</label>
                <input pInputText type="text" [(ngModel)]="cardNumber" placeholder="4111 1111 1111 1111" maxlength="19" />
              </div>
              <div class="checkout-azul-row">
                <div class="checkout-azul-field">
                  <label>{{ 'checkout.azul.expiry' | t }}</label>
                  <input pInputText type="text" [(ngModel)]="cardExpiry" placeholder="12/28" maxlength="5" />
                </div>
                <div class="checkout-azul-field">
                  <label>{{ 'checkout.azul.cvv' | t }}</label>
                  <input pInputText type="text" [(ngModel)]="cardCvv" placeholder="123" maxlength="4" />
                </div>
              </div>
            </div>
          </div>
        }

        @if (paymentMethod === 'paypal') {
          <div class="checkout-card-section">
            <label class="checkout-card-label">{{ 'checkout.how_it_works' | t }}</label>
            <div class="checkout-card-host checkout-card-host--paypal">
              <strong>1.</strong> {{ 'checkout.step1' | t }}
              <strong>2.</strong> {{ 'checkout.step2' | t }}
              <strong>3.</strong> {{ 'checkout.step3' | t }}
            </div>
            @if (paypalCancelled) {
              <small class="checkout-card-error">{{ 'checkout.cancelled_payment' | t }}</small>
            }
          </div>
        }

        <div class="checkout-compliance-notice">
          <strong>{{ 'checkout.compliance_title' | t }}</strong>
          <p>{{ 'checkout.compliance_text' | t }}</p>
        </div>

        <div class="checkout-actions">
          <button au-btn variant="ghost" type="button" (click)="goBackToPlans()">{{ 'checkout.go_back' | t }}</button>
          <button au-btn variant="primary" type="button"
            [loading]="processing"
            [disabled]="processing"
            class="checkout-pay-btn"
            (click)="processPayment()">
            {{ processing ? ('checkout.processing' | t) : getPayButtonLabel() }}
          </button>
        </div>

        <div class="checkout-trust">
          @if (paymentMethod === 'card') {
            <span><i class="pi pi-lock"></i> {{ 'checkout.secure_azul' | t }}</span>
          } @else {
            <span><i class="pi pi-paypal"></i> {{ 'checkout.secure_paypal' | t }}</span>
          }
          <span><i class="pi pi-lock"></i> {{ 'checkout.external_validation' | t }}</span>
          <span><i class="pi pi-refresh"></i> {{ 'checkout.reactivate_anytime' | t }}</span>
        </div>
      </div>
    }
  `,
  styles: [`
    /* ── Plans Step Styles ── */
    .plans-shell { max-width: 720px; margin: 0 auto; padding: 1.5rem; display: flex; flex-direction: column; gap: 1.25rem; }
    .plans-header { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(16rem, 0.85fr); align-items: stretch; gap: 1rem; }
    .plans-header__eyebrow { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; color: var(--text-color-secondary); }
    .plans-header__title { font-size: clamp(2rem, 5vw, 3.1rem); line-height: 0.98; font-weight: 900; color: var(--text-color); margin: 0.3rem 0 0.75rem; }
    .plans-header__copy { margin: 0; max-width: 34rem; color: var(--text-color-secondary); line-height: 1.55; }
    .plans-header__trust { display: flex; }
    .plans-header__trust-card { width: 100%; display: flex; flex-direction: column; gap: 0.45rem; padding: 1.15rem; border-radius: 1rem; background: #0f172a; color: #e2e8f0; box-shadow: 0 16px 40px rgba(15, 23, 42, 0.18); }
    .plans-header__trust-label { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.16em; color: #94a3b8; }
    .plans-header__trust-card strong { font-size: 1.45rem; line-height: 1.05; }
    .plans-loading { display: flex; align-items: center; gap: 0.5rem; color: var(--text-color-secondary); padding: 2rem; justify-content: center; }
    .plans-list { display: flex; flex-direction: column; gap: 0.5rem; }
    .plan-row { display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap; padding: 1rem 1.25rem; border: 1px solid var(--surface-border); background: var(--surface-card); border-radius: 0.85rem; cursor: pointer; transition: border-color 120ms, box-shadow 120ms; }
    .plan-row:hover { border-color: var(--brand); box-shadow: 0 0 0 1px var(--brand); }
    .plan-row--recommended { border-color: #10b981; box-shadow: 0 0 0 1px #10b981; }
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
    .current-sub-card { border: 1px solid var(--surface-border); background: var(--surface-card); border-radius: 0.85rem; overflow: hidden; }
    .current-sub-card__body { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 1.25rem; flex-wrap: wrap; }
    .current-sub-card__info { flex: 1; min-width: 0; }
    .current-sub-card__label { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; color: var(--text-color-secondary); margin-bottom: 0.25rem; }
    .current-sub-card__plan { font-size: 1.2rem; font-weight: 800; color: var(--text-color); }
    .current-sub-card__dates { font-size: 0.8rem; color: var(--text-color-secondary); margin-top: 0.15rem; }
    .current-sub-card__cancelled-badge { display: inline-flex; align-items: center; gap: 0.35rem; margin-top: 0.5rem; padding: 0.3rem 0.65rem; border-radius: 999px; font-size: 0.78rem; font-weight: 600; background: #fef3c7; color: #92400e; }
    :host-context(.app-dark) .current-sub-card__cancelled-badge { background: rgba(251, 191, 36, 0.12); color: #fbbf24; }
    .current-sub-card__actions { display: flex; gap: 0.5rem; flex-shrink: 0; }
    .billing-toggle-container { display: flex; margin-top: 1.25rem; }
    .billing-toggle-bar { display: inline-flex; border-radius: 9999px; background: var(--surface-hover); padding: 3px; border: 1px solid var(--surface-border); }
    .billing-toggle-btn { position: relative; width: 100px; border-radius: 9999px; padding: 0.4rem 0; font-size: 0.78rem; font-weight: 700; border: none; background: transparent; cursor: pointer; color: var(--text-color-secondary); transition: all 180ms ease-in-out; }
    .billing-toggle-btn.is-active { background: var(--brand); color: var(--p-primary-contrast-color); box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15); }
    .billing-toggle-discount { position: absolute; top: -8px; right: -6px; background: #10b981; color: white; font-size: 0.55rem; font-weight: 800; padding: 0.05rem 0.3rem; border-radius: 9999px; line-height: 1; }
    .plan-row__annual-note { font-size: 0.72rem; color: #10b981; font-weight: 600; margin-top: 0.15rem; }
    .recommended-annual-note { font-size: 0.72rem; color: #34d399; font-weight: 500; }
    @media (max-width: 860px) { .plans-header { grid-template-columns: 1fr; } }

    /* ── Checkout Step Styles ── */
    .checkout-shell { max-width: 640px; margin: 0 auto; padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem; }
    .checkout-header h1 { margin: 0.45rem 0 0.6rem; font-size: clamp(2rem, 6vw, 3.35rem); line-height: 0.96; color: var(--text-color); }
    .checkout-header p { margin: 0; color: var(--text-color-secondary); line-height: 1.55; }
    .checkout-header__eyebrow { display: inline-flex; padding: 0.35rem 0.75rem; border-radius: 999px; background: var(--surface-100); color: var(--text-color-secondary); font-size: 0.74rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.16em; }
    .checkout-summary { display: flex; align-items: center; justify-content: space-between; padding: 1rem 1.25rem; background: var(--surface-900); color: #fff; border-radius: 0.85rem; }
    .checkout-summary__plan { display: flex; flex-direction: column; gap: 0.15rem; }
    .checkout-summary__label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(255,255,255,0.55); }
    .checkout-summary__plan strong { font-size: 1rem; font-weight: 700; }
    .checkout-summary__price { text-align: right; }
    .checkout-summary__price strong { display: block; font-size: 1.9rem; font-weight: 800; font-family: 'Courier New', monospace; }
    .checkout-summary__price span { font-size: 0.78rem; color: rgba(255,255,255,0.6); }
    .checkout-total-panel { padding: 1rem 1.2rem; border-radius: 1rem; background: linear-gradient(135deg, var(--gray-900) 0%, var(--gray-800) 100%); color: var(--gray-50); box-shadow: 0 18px 40px rgba(15, 23, 42, 0.18); }
    .checkout-total-panel__label { display: block; font-size: 0.74rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.18em; color: var(--gray-400); }
    .checkout-total-panel__amount { display: block; margin-top: 0.45rem; font-size: clamp(3rem, 8vw, 4.8rem); line-height: 0.92; font-weight: 900; font-family: 'Courier New', monospace; }
    .checkout-total-panel__note { margin-top: 0.6rem; font-size: 0.92rem; line-height: 1.5; color: var(--gray-300); }
    .checkout-options { padding: 0.85rem 1rem; border: 1px solid var(--surface-border); background: var(--surface-card); border-radius: 0.75rem; }
    .checkout-options__months { display: flex; align-items: center; gap: 0.5rem; }
    .checkout-options__months label { font-size: 0.82rem; font-weight: 600; color: var(--text-color-secondary); }
    .checkout-months-grid { display: flex; gap: 0.35rem; }
    .checkout-month-btn { width: 2.2rem; height: 2.2rem; border: 1px solid var(--surface-border); background: var(--surface-ground); border-radius: 6px; font-size: 0.85rem; font-weight: 600; cursor: pointer; transition: all 120ms; color: var(--text-color); }
    .checkout-month-btn.is-active { background: var(--brand); color: #fff; border-color: var(--brand); }
    .checkout-month-btn:disabled { opacity: 0.4; cursor: not-allowed; }
    .checkout-payment-method { padding: 0.85rem 1rem; border: 1px solid var(--surface-border); background: var(--surface-card); border-radius: 0.75rem; }
    .checkout-payment-method__label { display: block; font-size: 0.82rem; font-weight: 600; color: var(--text-color-secondary); margin-bottom: 0.5rem; }
    .checkout-payment-toggle { display: flex; gap: 0.5rem; }
    .checkout-payment-btn { flex: 1; display: flex; align-items: center; justify-content: center; gap: 0.5rem; padding: 0.6rem 1rem; border-radius: 8px; font-size: 0.88rem; font-weight: 600; border: 2px solid var(--surface-border); background: var(--surface-ground); color: var(--text-color-secondary); cursor: pointer; transition: all 0.2s ease; }
    .checkout-payment-btn.is-active { border-color: var(--brand); background: var(--brand); color: #fff; }
    .checkout-card-section { display: flex; flex-direction: column; gap: 0.5rem; padding: 1rem; border: 1px solid var(--surface-border); background: var(--surface-card); border-radius: 0.75rem; }
    .checkout-card-label { font-size: 0.82rem; font-weight: 600; color: var(--text-color-secondary); }
    .checkout-card-host { border: 1px solid var(--surface-border); border-radius: 8px; padding: 0.85rem; min-height: 48px; background: var(--surface-ground); }
    .checkout-card-host--paypal, .checkout-card-host--card { display: grid; grid-template-columns: auto 1fr; gap: 0.4rem 0.7rem; align-items: start; color: var(--text-color-secondary); }
    .checkout-card-error { color: #ef4444; font-size: 0.82rem; }
    .checkout-azul-form { display: flex; flex-direction: column; gap: 0.75rem; }
    .checkout-azul-field { display: flex; flex-direction: column; gap: 0.3rem; }
    .checkout-azul-field label { font-size: 0.8rem; font-weight: 600; color: var(--text-color-secondary); }
    .checkout-azul-field input { width: 100%; }
    .checkout-azul-row { display: flex; gap: 0.75rem; }
    .checkout-azul-row .checkout-azul-field { flex: 1; }
    .checkout-compliance-notice { padding: 1rem; background: var(--surface-100); border-radius: 6px; font-size: 0.85rem; color: var(--text-color-secondary); }
    .checkout-compliance-notice p { margin-top: 0.5rem; line-height: 1.4; }
    .checkout-actions { display: flex; gap: 0.75rem; }
    .checkout-pay-btn { flex: 1; height: 3rem; font-size: 1rem; font-weight: 700; }
    .checkout-trust { display: flex; justify-content: center; gap: 1.25rem; font-size: 0.78rem; color: var(--text-color-secondary); }
    .checkout-trust span { display: flex; align-items: center; gap: 0.3rem; }
    .checkout-billing-cycle { display: flex; align-items: center; justify-content: space-between; padding: 0.85rem 1rem; border: 1px solid var(--surface-border); background: var(--surface-card); border-radius: 0.75rem; }
    .checkout-billing-cycle__label { font-size: 0.82rem; font-weight: 600; color: var(--text-color-secondary); }
    .checkout-cycle-toggle { display: flex; background: var(--surface-ground); padding: 0.2rem; border-radius: 999px; border: 1px solid var(--surface-border); }
    .checkout-cycle-btn { padding: 0.4rem 1rem; border-radius: 999px; font-size: 0.85rem; font-weight: 600; border: none; background: transparent; color: var(--text-color-secondary); cursor: pointer; transition: all 0.2s ease; }
    .checkout-cycle-btn.is-active { background: var(--brand); color: #fff; }
    .discount-badge { position: absolute; top: -8px; right: -8px; background: #10b981; color: white; font-size: 0.65rem; padding: 0.1rem 0.35rem; border-radius: 999px; font-weight: 700; }
    .checkout-annual-locked-text { font-size: 0.88rem; font-weight: 600; color: #10b981; display: inline-flex; align-items: center; gap: 0.25rem; }
  `]
})
export class SubscriptionComponent implements OnInit, OnDestroy {
  step = signal<'plans' | 'checkout'>('plans');
  plans = signal<any[]>([]);
  loadingPlans = signal(false);
  currentSubscription: any = null;
  billingInterval: 'month' | 'year' = 'month';
  selectedPlan = signal<any | null>(null);

  // Checkout state
  processing = false;
  selectedMonths = 1;
  monthOptions = [1, 3, 6, 12];
  enableAutoRenew = false;
  paypalCancelled = false;
  paymentMethod: 'card' | 'paypal' = 'card';
  cardHolder = '';
  cardNumber = '';
  cardExpiry = '';
  cardCvv = '';

  private trialService = inject(TrialService);
  private subscriptionService = inject(SubscriptionService);
  private paypalReturnRecoveryService = inject(PaypalReturnRecoveryService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private messageService = inject(MessageService);
  private destroyRef = inject(DestroyRef);
  private localeService = inject(LocaleService);

  ngOnInit() {
    // Handle PayPal return callbacks
    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      const paypalStatus = params.get('paypal');
      const token = params.get('token');
      const storedOrderId = this.paypalReturnRecoveryService.getPendingOrderId();

      const intervalParam = params.get('billing_interval') || params.get('billingInterval');
      if (intervalParam === 'year' || intervalParam === 'month') {
        this.billingInterval = intervalParam;
        if (this.billingInterval === 'year') this.selectedMonths = 12;
      }

      if (paypalStatus === 'cancelled' || params.get('paypal_sub') === 'cancelled') {
        this.paypalReturnRecoveryService.clearPendingOrderId();
        this.paypalCancelled = true;
        this.messageService.add({ severity: 'warn', summary: this.t('checkout.toast.cancelled_summary'), detail: this.t('checkout.toast.cancelled_detail') });
        return;
      }

      if (token) { this.finalizePaypalPayment(token); return; }

      const isSubSuccess = params.get('paypal_sub') === 'success';
      const subIdFromUrl = params.get('subscription_id');
      if (isSubSuccess && subIdFromUrl) { this.finalizePaypalPayment(subIdFromUrl, true); return; }
      if (isSubSuccess && storedOrderId) { this.finalizePaypalPayment(storedOrderId, true); return; }
      if (paypalStatus === 'success' && storedOrderId) { this.finalizePaypalPayment(storedOrderId, false); return; }

      if ((paypalStatus === 'success' || isSubSuccess) && !storedOrderId && !subIdFromUrl) {
        this.messageService.add({ severity: 'warn', summary: this.t('checkout.toast.incomplete_summary'), detail: this.t('checkout.toast.incomplete_detail') });
        return;
      }
    });

    // If we have a selected plan from router state (deep link), go to checkout
    const navState = history.state;
    if (navState?.plan) {
      this.selectedPlan.set(navState.plan);
      this.billingInterval = navState.billingInterval || navState.billing_interval || 'month';
      if (this.billingInterval === 'year') this.selectedMonths = 12;
      this.step.set('checkout');
    }

    this.loadSubscription();
    this.loadPlans();
  }

  ngOnDestroy() {
    // Clean URL params on destroy
    if (this.route.snapshot.queryParams['paypal'] || this.route.snapshot.queryParams['token']) {
      void this.router.navigate([], { relativeTo: this.route, queryParams: {}, replaceUrl: true });
    }
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
        if (subs.length > 0) this.currentSubscription = subs[0];
      },
      error: () => { this.currentSubscription = null; }
    });
  }

  loadPlans() {
    this.loadingPlans.set(true);
    this.subscriptionService.getPlans().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (data: any) => {
        const allPlans = Array.isArray(data) ? data : (data.results || []);
        this.plans.set(allPlans
          .filter((plan: any) => plan.is_active !== false && plan.is_public !== false)
          .map((plan: any) => {
            const priceVal = Number(plan.price ?? 0);
            const annualPriceVal = plan.annual_price != null ? Number(plan.annual_price) : priceVal * 12 * 0.8;
            return { ...plan, price: priceVal, annual_price: annualPriceVal, recommended: this.isRecommendedPlan(plan), features: this.getFeaturesList(plan.features) };
          }));
        this.loadingPlans.set(false);
      },
      error: () => {
        this.messageService.add({ severity: 'error', summary: this.t('common.error'), detail: this.t('payment.toast.load_error') });
        this.loadingPlans.set(false);
      }
    });
  }

  getFeaturesList(features: any): string[] {
    if (!features || typeof features !== 'object') return [];
    const featureNames: Record<string, string> = {
      'appointments': this.t('payment.features.appointments'),
      'reports': this.t('payment.features.reports'),
      'multi_location': this.t('payment.features.multi_location'),
      'custom_branding': this.t('payment.features.custom_branding'),
      'priority_support': this.t('payment.features.priority_support'),
      'export_reports': this.t('payment.features.export_reports'),
      'whatsapp_notifications': this.t('payment.features.whatsapp_notifications')
    };
    return Object.entries(features).filter(([, v]) => v === true).map(([k]) => featureNames[k] || k);
  }

  getRecommendedPlan(): any | null {
    return this.plans().find(p => p.recommended) || this.plans()[0] || null;
  }

  selectPlan(plan: any) {
    this.selectedPlan.set(plan);
    if (this.billingInterval === 'year') this.selectedMonths = 12;
    this.step.set('checkout');
  }

  goBackToPlans() {
    this.step.set('plans');
    this.selectedPlan.set(null);
    this.paypalCancelled = false;
  }

  // ── Checkout logic ──

  getTotalAmount(): number {
    if (!this.selectedPlan()) return 0;
    if (this.billingInterval === 'year') {
      const annualPrice = this.selectedPlan()!.annual_price;
      if (annualPrice) return Number(Number(annualPrice).toFixed(2));
    }
    return Number((Number(this.selectedPlan()!.price || 0) * this.selectedMonths).toFixed(2));
  }

  setBillingInterval(interval: 'month' | 'year') {
    this.billingInterval = interval;
    this.selectedMonths = interval === 'year' ? 12 : 1;
  }

  getPayButtonLabel(): string {
    const label = this.paymentMethod === 'paypal' ? this.t('checkout.pay_with_paypal') : this.t('checkout.pay_with_card');
    return label + ' $' + this.getTotalAmount();
  }

  processPayment() {
    if (!this.selectedPlan() || this.processing) return;
    if (this.paymentMethod === 'paypal') this.processPaypal();
    else this.processAzulCard();
  }

  private processPaypal() {
    this.processing = true;
    this.messageService.add({ severity: 'info', summary: this.t('checkout.toast.redirect_paypal_summary'), detail: this.t('checkout.toast.redirect_paypal_detail') });
    if (!this.selectedPlan()?.id) return;

    this.subscriptionService.createPaypalOrder(this.selectedPlan()!.id, this.selectedMonths, this.enableAutoRenew, this.billingInterval)
      .pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (response) => {
          const approveUrl = response?.approve_url;
          const orderId = response?.order_id;
          const subId = response?.subscription_id;
          if (!approveUrl) { this.handleError({ error: { message: 'PayPal no devolvió una URL válida.' } }); return; }
          if (orderId) this.paypalReturnRecoveryService.setPendingOrderId(orderId);
          else if (subId) this.paypalReturnRecoveryService.setPendingOrderId(subId);
          window.location.href = approveUrl;
        },
        error: (error) => this.handleError(error)
      });
  }

  private processAzulCard() {
    if (!this.cardHolder.trim() || !this.cardNumber.trim() || !this.cardExpiry.trim() || !this.cardCvv.trim()) {
      this.messageService.add({ severity: 'warn', summary: this.t('checkout.toast.error_summary'), detail: 'Completa todos los campos de la tarjeta' });
      return;
    }
    this.processing = true;
    const amount = this.getTotalAmount();
    const orderNumber = `SUB-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
    this.messageService.add({ severity: 'info', summary: this.t('checkout.toast.confirm_payment_summary'), detail: this.t('checkout.toast.confirm_payment_detail') });

    this.subscriptionService.createAzulPayment({ amount, order_number: orderNumber, customer_email: '', plan_id: String(this.selectedPlan()?.id || ''), months: this.selectedMonths })
      .pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (response) => {
          this.processing = false;
          const langLocale = this.localeService.getCurrentLanguage() === 'es' ? 'es-DO' : 'en-US';
          this.messageService.add({ severity: 'success', summary: this.t('checkout.toast.success_summary'), detail: this.t('checkout.toast.success_detail').replace('{date}', new Date(response?.access_until || Date.now()).toLocaleDateString(langLocale)) });
          setTimeout(() => this.router.navigate(['/client/dashboard']), 1800);
        },
        error: (error) => this.handleError(error)
      });
  }

  private finalizePaypalPayment(orderId: string, isSubscription = false) {
    if (!orderId || this.processing) return;
    this.processing = true;
    this.messageService.add({ severity: 'info', summary: this.t('checkout.toast.confirm_payment_summary'), detail: this.t('checkout.toast.confirm_payment_detail') });

    const request = isSubscription
      ? this.subscriptionService.capturePaypalSubscription(orderId)
      : this.subscriptionService.capturePaypalOrder(orderId);

    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (response) => {
        this.processing = false;
        this.paypalReturnRecoveryService.clearPendingOrderId();
        const langLocale = this.localeService.getCurrentLanguage() === 'es' ? 'es-DO' : 'en-US';
        this.messageService.add({ severity: 'success', summary: this.t('checkout.toast.success_summary'), detail: this.t('checkout.toast.success_detail').replace('{date}', new Date(response?.access_until || Date.now()).toLocaleDateString(langLocale)) });
        void this.router.navigate([], { relativeTo: this.route, queryParams: {}, replaceUrl: true });
        setTimeout(() => this.router.navigate(['/client/dashboard']), 1800);
      },
      error: (error) => {
        void this.router.navigate([], { relativeTo: this.route, queryParams: {}, replaceUrl: true });
        this.handleError(error);
      }
    });
  }

  private handleError(error: any) {
    this.messageService.add({ severity: 'error', summary: this.t('checkout.toast.error_summary'), detail: error?.error?.message || error?.error?.error || this.t('checkout.toast.error_detail_default') });
    this.processing = false;
  }

  private isRecommendedPlan(plan: any): boolean {
    const nav = history.state;
    const normalizedRecommended = String(nav?.recommendedPlanName || '').trim().toLowerCase();
    const normalizedPlanName = String(plan?.name || '').trim().toLowerCase();
    if (normalizedRecommended) return normalizedPlanName === normalizedRecommended;
    return normalizedPlanName === 'standard';
  }

  @HostListener('document:keydown.enter', ['$event'])
  handleEnterShortcut(event: Event): void {
    const kbevent = event as KeyboardEvent;

    const target = event.target as HTMLElement | null;
    const tag = target?.tagName?.toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

    if (this.step() === 'plans') {
      const recommended = this.getRecommendedPlan();
      if (recommended) { kbevent.preventDefault(); this.selectPlan(recommended); }
    } else if (this.step() === 'checkout' && !this.processing) {
      event.preventDefault();
      this.processPayment();
    }
  }
}
