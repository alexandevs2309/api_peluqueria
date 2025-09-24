import stripe
import os
from django.conf import settings
from django.utils import timezone
from .models import Invoice, PaymentAttempt
from apps.subscriptions_api.models import UserSubscription
from apps.tenants_api.models import Tenant

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

class StripeService:
    @staticmethod
    def create_customer(user):
        """Crear cliente en Stripe"""
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.full_name,
                metadata={'user_id': user.id}
            )
            return customer
        except stripe.error.StripeError as e:
            raise Exception(f"Error creando cliente Stripe: {str(e)}")

    @staticmethod
    def create_subscription(user, price_id):
        """Crear suscripción en Stripe"""
        try:
            # Crear o obtener cliente
            customer = StripeService.create_customer(user)
            
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{'price': price_id}],
                payment_behavior='default_incomplete',
                expand=['latest_invoice.payment_intent'],
                metadata={'user_id': user.id}
            )
            return subscription
        except stripe.error.StripeError as e:
            raise Exception(f"Error creando suscripción: {str(e)}")

    @staticmethod
    def cancel_subscription(subscription_id):
        """Cancelar suscripción en Stripe"""
        try:
            return stripe.Subscription.delete(subscription_id)
        except stripe.error.StripeError as e:
            raise Exception(f"Error cancelando suscripción: {str(e)}")

    @staticmethod
    def suspend_customer(customer_id):
        """Suspender cliente moroso"""
        try:
            # Pausar todas las suscripciones activas
            subscriptions = stripe.Subscription.list(customer=customer_id, status='active')
            for sub in subscriptions.data:
                stripe.Subscription.modify(
                    sub.id,
                    pause_collection={'behavior': 'void'}
                )
            return True
        except stripe.error.StripeError as e:
            raise Exception(f"Error suspendiendo cliente: {str(e)}")