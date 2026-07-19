import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { BaseApiService } from '../base-api.service';
import { API_CONFIG } from '../../config/api.config';

export interface SubscriptionStatus {
  tenant_name: string;
  current_status: string;
  trial_end_date: string;
  access_level: string;
  days_in_grace: number;
  available_plans: any[];
}

@Injectable({
  providedIn: 'root'
})
export class SubscriptionService extends BaseApiService {

  getSubscriptionStatus(): Observable<SubscriptionStatus> {
    return this.get(API_CONFIG.ENDPOINTS.SUBSCRIPTIONS.RENEW);
  }

  renewSubscription(
    planId: number,
    paymentMethodId: string | null,
    months: number = 1,
    autoRenew: boolean = false,
    paymentIntentId?: string
  ): Observable<any> {
    const payload: any = {
      plan_id: planId,
      months,
      auto_renew: autoRenew
    };

    if (paymentIntentId) {
      payload.payment_intent_id = paymentIntentId;
    } else if (paymentMethodId) {
      payload.payment_method_id = paymentMethodId;
    }

    return this.post(API_CONFIG.ENDPOINTS.SUBSCRIPTIONS.RENEW, payload);
  }

  createPaypalOrder(planId: number, months: number = 1, autoRenew: boolean = false, billingInterval: string = 'month'): Observable<any> {
    return this.post(API_CONFIG.ENDPOINTS.SUBSCRIPTIONS.RENEW, {
      payment_provider: 'paypal',
      paypal_action: 'create_order',
      plan_id: planId,
      months,
      auto_renew: autoRenew,
      billing_interval: billingInterval
    });
  }

  capturePaypalOrder(orderId: string): Observable<any> {
    return this.post(API_CONFIG.ENDPOINTS.SUBSCRIPTIONS.RENEW, {
      payment_provider: 'paypal',
      paypal_action: 'capture_order',
      paypal_order_id: orderId
    });
  }

  capturePaypalSubscription(subscriptionId: string): Observable<any> {
    return this.post(API_CONFIG.ENDPOINTS.SUBSCRIPTIONS.RENEW, {
      payment_provider: 'paypal',
      paypal_action: 'capture_subscription',
      subscription_id: subscriptionId
    });
  }

  getPlans(): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.SUBSCRIPTIONS.PLANS);
  }

  getUserSubscriptions(params?: any): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.SUBSCRIPTIONS.USER_SUBSCRIPTIONS, params);
  }

  getSubscriptionAuditLogs(params?: any): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.SUBSCRIPTIONS.AUDIT_LOGS, params);
  }

  updateUserSubscription(id: number, data: any): Observable<any> {
    return this.patch(`${API_CONFIG.ENDPOINTS.SUBSCRIPTIONS.USER_SUBSCRIPTIONS}${id}/`, data);
  }

  cancelUserSubscription(id: number): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.SUBSCRIPTIONS.USER_SUBSCRIPTIONS}${id}/cancel/`, {});
  }

  reactivateUserSubscription(id: number): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.SUBSCRIPTIONS.USER_SUBSCRIPTIONS}${id}/reactivate/`, {});
  }

  updatePlan(planId: number, planData: any): Observable<any> {
    return this.patch(`${API_CONFIG.ENDPOINTS.SUBSCRIPTIONS.PLANS}${planId}/`, planData);
  }

  getPromotionalCredits(params?: any): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.SUBSCRIPTIONS.PROMOTIONAL_CREDITS, params);
  }

  createPromotionalCredit(data: any): Observable<any> {
    return this.post(API_CONFIG.ENDPOINTS.SUBSCRIPTIONS.PROMOTIONAL_CREDITS, data);
  }

  deletePromotionalCredit(id: number): Observable<any> {
    return this.delete(`${API_CONFIG.ENDPOINTS.SUBSCRIPTIONS.PROMOTIONAL_CREDITS}${id}/`);
  }

  // ── Azul (procesador primario para RD) ──

  createAzulPayment(data: {
    amount: number;
    currency?: string;
    order_number?: string;
    customer_email?: string;
    plan_id?: string;
    months?: number;
  }): Observable<any> {
    return this.post(API_CONFIG.ENDPOINTS.PAYMENTS + 'azul/checkout/', data);
  }

  verifyAzulTransaction(orderNumber: string): Observable<any> {
    return this.post(API_CONFIG.ENDPOINTS.PAYMENTS + 'azul/verify/', { order_number: orderNumber });
  }
}
