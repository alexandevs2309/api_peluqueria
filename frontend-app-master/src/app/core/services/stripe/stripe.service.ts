import { Injectable } from '@angular/core';
import { environment } from '../../../../environments/environment';
import { firstValueFrom } from 'rxjs';
import { PosService } from '../pos/pos.service';

@Injectable({
    providedIn: 'root'
})
export class StripeService {
    private stripe: any = null;

    constructor(private readonly posService: PosService) {}

    private async getStripe() {
        if (!this.stripe) {
            const key = environment.stripePublishableKey;
            if (!key) throw new Error('Stripe publishable key no configurada');
            const { loadStripe } = await import('@stripe/stripe-js');
            this.stripe = await loadStripe(key);
        }
        return this.stripe;
    }

    async createPaymentIntent(amount: number, currency: string = 'DOP'): Promise<{ clientSecret: string; id: string }> {
        const result = await firstValueFrom(
            this.posService.chargeCard(amount, currency)
        ) as any;
        return { clientSecret: result.client_secret, id: result.transaction_id };
    }

    async confirmCardPayment(clientSecret: string, cardElement: any): Promise<any> {
        const stripe = await this.getStripe();
        const { error, paymentIntent } = await stripe.confirmCardPayment(clientSecret, {
            payment_method: { card: cardElement }
        });
        if (error) throw error;
        return paymentIntent;
    }

    elements(cardElementOptions?: any): Promise<any> {
        return this.getStripe().then(s => s.elements(cardElementOptions));
    }
}
