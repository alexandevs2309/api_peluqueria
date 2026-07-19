import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { MessageService } from 'primeng/api';
import { SubscriptionService } from './subscription/subscription.service';

@Injectable({
  providedIn: 'root'
})
export class PaypalReturnRecoveryService {
  private readonly pendingKeys = ['pending_paypal_order_id', 'pending_paypal_order_id_fallback'];
  private readonly attemptedOrderIds = new Set<string>();
  private readonly router = inject(Router);
  private readonly subscriptionService = inject(SubscriptionService);
  private readonly messageService = inject(MessageService);

  init(): void {
    const url = new URL(window.location.href);
    const token = url.searchParams.get('token');
    const paypalStatus = url.searchParams.get('paypal');
    const payerId = url.searchParams.get('PayerID');
    const pendingOrderId = this.getPendingOrderId();
    const currentPath = url.pathname || '';
    const isClientArea = currentPath.startsWith('/client');
    const isCheckoutPage = currentPath === '/client/checkout';

    if (paypalStatus === 'cancelled') {
      this.clearPendingOrderId();
      this.clearPaypalQueryParams(url);
      return;
    }

    if (isCheckoutPage && (paypalStatus === 'success' || !!token || !!payerId)) {
      return;
    }

    const orderId = token || pendingOrderId;
    const shouldAttemptRecovery = isClientArea && !!orderId && (paypalStatus === 'success' || !!token || !!payerId || !!pendingOrderId);

    if (!shouldAttemptRecovery || !orderId || this.attemptedOrderIds.has(orderId)) {
      return;
    }

    this.attemptedOrderIds.add(orderId);
    this.subscriptionService.capturePaypalOrder(orderId).subscribe({
      next: (response) => {
        this.clearPendingOrderId();
        this.clearPaypalQueryParams(url);
        this.messageService.add({
          severity: 'success',
          summary: 'Pago confirmado',
          detail: `Tu suscripción quedó activa hasta ${new Date(response?.access_until || Date.now()).toLocaleDateString('es-DO')}`
        });

        if (!currentPath.startsWith('/client/dashboard')) {
          void this.router.navigate(['/client/dashboard']);
        }
      },
      error: () => {
        this.clearPendingOrderId();
        this.clearPaypalQueryParams(url);
      }
    });
  }

  setPendingOrderId(orderId: string): void {
    if (!orderId) {
      return;
    }
    sessionStorage.setItem(this.pendingKeys[0], orderId);
    localStorage.setItem(this.pendingKeys[1], orderId);
  }

  clearPendingOrderId(): void {
    for (const key of this.pendingKeys) {
      sessionStorage.removeItem(key);
      localStorage.removeItem(key);
    }
  }

  getPendingOrderId(): string | null {
    return sessionStorage.getItem(this.pendingKeys[0]) || localStorage.getItem(this.pendingKeys[1]);
  }

  private clearPaypalQueryParams(url: URL): void {
    url.searchParams.delete('paypal');
    url.searchParams.delete('token');
    url.searchParams.delete('PayerID');
    window.history.replaceState({}, document.title, `${url.pathname}${url.searchParams.toString() ? `?${url.searchParams.toString()}` : ''}`);
  }
}
