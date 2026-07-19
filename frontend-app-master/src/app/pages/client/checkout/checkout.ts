import { Component, HostListener, OnInit, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { CheckboxModule } from 'primeng/checkbox';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { SelectButtonModule } from 'primeng/selectbutton';
import { ActivatedRoute, Router } from '@angular/router';
import { SubscriptionService } from '../../../core/services/subscription/subscription.service';
import { PaypalReturnRecoveryService } from '../../../core/services/paypal-return-recovery.service';
import { MessageService } from 'primeng/api';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { I18nPipe } from '../../../core/pipes/i18n.pipe';
import { AuBtn, AuSkeleton } from '../../../shared/components';

@Component({
  selector: 'app-checkout',
  standalone: true,
  imports: [CommonModule, FormsModule, ButtonModule, CardModule, CheckboxModule, I18nPipe, InputTextModule, InputNumberModule, SelectButtonModule, AuBtn, AuSkeleton],
  templateUrl: './checkout.html',
  styles: [``]
})
export class CheckoutComponent implements OnInit {
  selectedPlan: any = null;
  processing = false;
  selectedMonths = 1;
  monthOptions = [1, 3, 6, 12];
  enableAutoRenew = false;
  paypalCancelled = false;
  billingInterval: 'month' | 'year' = 'month';
  paymentMethod: 'card' | 'paypal' = 'card';

  // Card form
  cardHolder = '';
  cardNumber = '';
  cardExpiry = '';
  cardCvv = '';

  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private subscriptionService = inject(SubscriptionService);
  private paypalReturnRecoveryService = inject(PaypalReturnRecoveryService);
  private messageService = inject(MessageService);
  private destroyRef = inject(DestroyRef);
  private localeService = inject(LocaleService);

  paymentMethodOptions = [
    { label: '', value: 'card' },
    { label: '', value: 'paypal' },
  ];

  ngOnInit() {
    const navigation = this.router.getCurrentNavigation();
    const state = navigation?.extras.state;

    if (state?.['plan']) {
      this.selectedPlan = state['plan'];
      this.billingInterval = state['billingInterval'] || state['billing_interval'] || 'month';
    } else if (history.state?.plan) {
      this.selectedPlan = history.state.plan;
      this.billingInterval = history.state.billingInterval || history.state.billing_interval || 'month';
    }

    if (this.billingInterval === 'year') {
      this.selectedMonths = 12;
    }

    if (this.selectedPlan && Number(this.selectedPlan.price) === 0) {
      this.messageService.add({
        severity: 'info',
        summary: this.t('checkout.toast.invalid_plan_summary'),
        detail: this.t('checkout.toast.invalid_plan_detail')
      });
      setTimeout(() => this.router.navigate(['/client/payment']), 100);
      return;
    }

    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      const paypalStatus = params.get('paypal');
      const token = params.get('token');
      const storedOrderId = this.paypalReturnRecoveryService.getPendingOrderId();

      const intervalParam = params.get('billing_interval') || params.get('billingInterval');
      if (intervalParam === 'year' || intervalParam === 'month') {
        this.billingInterval = intervalParam;
        if (this.billingInterval === 'year') {
          this.selectedMonths = 12;
        }
      }

      if (paypalStatus === 'cancelled' || params.get('paypal_sub') === 'cancelled') {
        this.paypalReturnRecoveryService.clearPendingOrderId();
        this.paypalCancelled = true;
        this.messageService.add({
          severity: 'warn',
          summary: this.t('checkout.toast.cancelled_summary'),
          detail: this.t('checkout.toast.cancelled_detail')
        });
        return;
      }

      if (token) {
        this.finalizePaypalPayment(token);
        return;
      }

      const isSubSuccess = params.get('paypal_sub') === 'success';
      const subIdFromUrl = params.get('subscription_id');

      if (isSubSuccess && subIdFromUrl) {
        this.finalizePaypalPayment(subIdFromUrl, true);
        return;
      }

      if (isSubSuccess && storedOrderId) {
        this.finalizePaypalPayment(storedOrderId, true);
        return;
      }

      if (paypalStatus === 'success' && storedOrderId) {
        this.finalizePaypalPayment(storedOrderId, false);
        return;
      }

      if ((paypalStatus === 'success' || isSubSuccess) && !storedOrderId && !subIdFromUrl) {
        this.messageService.add({
          severity: 'warn',
          summary: this.t('checkout.toast.incomplete_summary'),
          detail: this.t('checkout.toast.incomplete_detail')
        });
        return;
      }

      if (!this.selectedPlan && !this.paypalReturnRecoveryService.getPendingOrderId()) {
        setTimeout(() => {
          this.router.navigate(['/client/payment']);
        }, 100);
      }
    });
  }

  t(key: string): string {
    return this.localeService.t(key as any);
  }

  processPayment() {
    if (!this.selectedPlan || this.processing) {
      return;
    }

    if (this.paymentMethod === 'paypal') {
      this.processPaypal();
    } else {
      this.processAzulCard();
    }
  }

  private processPaypal() {
    this.processing = true;
    this.messageService.add({
      severity: 'info',
      summary: this.t('checkout.toast.redirect_paypal_summary'),
      detail: this.t('checkout.toast.redirect_paypal_detail')
    });

    if (!this.selectedPlan?.id) return;
    this.subscriptionService.createPaypalOrder(this.selectedPlan.id, this.selectedMonths, this.enableAutoRenew, this.billingInterval).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (response) => {
        const approveUrl = response?.approve_url;
        const orderId = response?.order_id;
        const subId = response?.subscription_id;

        if (!approveUrl) {
          this.handleError({ error: { message: 'PayPal no devolvió una URL de aprobación válida.' } });
          return;
        }

        if (orderId) {
          this.paypalReturnRecoveryService.setPendingOrderId(orderId);
        } else if (subId) {
          this.paypalReturnRecoveryService.setPendingOrderId(subId);
        }
        window.location.href = approveUrl;
      },
      error: (error) => this.handleError(error)
    });
  }

  private processAzulCard() {
    if (!this.cardHolder.trim() || !this.cardNumber.trim() || !this.cardExpiry.trim() || !this.cardCvv.trim()) {
      this.messageService.add({
        severity: 'warn',
        summary: this.t('checkout.toast.error_summary'),
        detail: 'Completa todos los campos de la tarjeta'
      });
      return;
    }

    this.processing = true;
    const amount = this.getTotalAmount();
    const orderNumber = `SUB-${Date.now()}-${Math.floor(Math.random() * 10000)}`;

    this.messageService.add({
      severity: 'info',
      summary: this.t('checkout.toast.confirm_payment_summary'),
      detail: this.t('checkout.toast.confirm_payment_detail')
    });

    this.subscriptionService.createAzulPayment({
      amount,
      order_number: orderNumber,
      customer_email: '',
      plan_id: String(this.selectedPlan?.id || ''),
      months: this.selectedMonths,
    }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (response) => {
        this.processing = false;
        const langLocale = this.localeService.getCurrentLanguage() === 'es' ? 'es-DO' : 'en-US';
        this.messageService.add({
          severity: 'success',
          summary: this.t('checkout.toast.success_summary'),
          detail: this.t('checkout.toast.success_detail').replace('{date}', new Date(response?.access_until || Date.now()).toLocaleDateString(langLocale))
        });
        setTimeout(() => {
          this.router.navigate(['/client/dashboard']);
        }, 1800);
      },
      error: (error) => this.handleError(error)
    });
  }

  goBack() {
    this.router.navigate(['/client/payment']);
  }

  @HostListener('document:keydown.enter', ['$event'])
  handleEnterShortcut(event: any): void {
    const target = event.target as HTMLElement | null;
    const tag = target?.tagName?.toLowerCase();
    if (tag === 'textarea' || this.processing) {
      return;
    }
    if (tag !== 'button') {
      event.preventDefault();
      this.processPayment();
    }
  }

  getTotalAmount(): number {
    if (this.billingInterval === 'year') {
      const annualPrice = this.selectedPlan?.annual_price ?? this.selectedPlan?.annualPrice;
      if (annualPrice) {
        return Number(Number(annualPrice).toFixed(2));
      }
    }
    const planPrice = Number(this.selectedPlan?.price || 0);
    return Number((planPrice * this.selectedMonths).toFixed(2));
  }

  setBillingInterval(interval: 'month' | 'year') {
    this.billingInterval = interval;
    if (interval === 'year') {
      this.selectedMonths = 12;
    } else {
      this.selectedMonths = 1;
    }
  }

  onPaymentMethodChange(value: string) {
    this.paymentMethod = value as 'card' | 'paypal';
  }

  getPayButtonLabel(): string {
    if (this.paymentMethod === 'paypal') {
      return this.t('checkout.pay_with_paypal') + ' $' + this.getTotalAmount();
    }
    return this.t('checkout.pay_with_card') + ' $' + this.getTotalAmount();
  }

  private finalizePaypalPayment(orderId: string, isSubscription: boolean = false) {
    if (!orderId || this.processing) {
      return;
    }

    this.processing = true;
    this.messageService.add({
      severity: 'info',
      summary: this.t('checkout.toast.confirm_payment_summary'),
      detail: this.t('checkout.toast.confirm_payment_detail')
    });

    const request = isSubscription
      ? this.subscriptionService.capturePaypalSubscription(orderId)
      : this.subscriptionService.capturePaypalOrder(orderId);

    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (response) => {
        this.processing = false;
        this.paypalReturnRecoveryService.clearPendingOrderId();

        const langLocale = this.localeService.getCurrentLanguage() === 'es' ? 'es-DO' : 'en-US';
        this.messageService.add({
          severity: 'success',
          summary: this.t('checkout.toast.success_summary'),
          detail: this.t('checkout.toast.success_detail').replace('{date}', new Date(response?.access_until || Date.now()).toLocaleDateString(langLocale))
        });

        void this.router.navigate([], {
          relativeTo: this.route,
          queryParams: {},
          replaceUrl: true
        });

        setTimeout(() => {
          this.router.navigate(['/client/dashboard']);
        }, 1800);
      },
      error: (error) => {
        void this.router.navigate([], {
          relativeTo: this.route,
          queryParams: {},
          replaceUrl: true
        });
        this.handleError(error);
      }
    });
  }

  private handleError(error: any) {
    this.messageService.add({
      severity: 'error',
      summary: this.t('checkout.toast.error_summary'),
      detail: error?.error?.message || error?.error?.error || this.t('checkout.toast.error_detail_default')
    });
    this.processing = false;
  }
}
