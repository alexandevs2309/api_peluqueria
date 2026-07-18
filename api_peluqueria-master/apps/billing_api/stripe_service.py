import stripe
from django.conf import settings
from django.utils import timezone
from .models import Invoice, PaymentAttempt
from apps.subscriptions_api.models import UserSubscription
from apps.tenants_api.models import Tenant

stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeService:
    @staticmethod
    def get_or_create_customer(user):
        """
        Obtener o crear cliente en Stripe.
        Persiste stripe_customer_id para evitar duplicados entre intentos.
        """
        try:
            if getattr(user, 'stripe_customer_id', None):
                try:
                    customer = stripe.Customer.retrieve(user.stripe_customer_id)
                    if not getattr(customer, 'deleted', False):
                        return customer
                except stripe.error.InvalidRequestError:
                    pass

            existing = stripe.Customer.list(email=user.email, limit=1)
            if existing.data:
                customer = existing.data[0]
                if not getattr(customer, 'deleted', False):
                    type(user).objects.filter(pk=user.pk).update(
                        stripe_customer_id=customer.id
                    )
                    user.stripe_customer_id = customer.id
                    return customer

            customer = stripe.Customer.create(
                email=user.email,
                name=getattr(user, 'full_name', '') or user.email,
                metadata={
                    'user_id': str(user.id),
                    'tenant_id': str(getattr(user, 'tenant_id', '') or ''),
                }
            )
            type(user).objects.filter(pk=user.pk).update(
                stripe_customer_id=customer.id
            )
            user.stripe_customer_id = customer.id
            return customer
        except stripe.error.StripeError as e:
            raise Exception(f"Error creando cliente Stripe: {str(e)}")

    @staticmethod
    def create_subscription(user, price_id):
        """Crear suscripción en Stripe"""
        try:
            customer = StripeService.get_or_create_customer(user)
            
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{'price': price_id}],
                payment_behavior='default_incomplete',
                expand=['latest_invoice.payment_intent'],
                metadata={
                    'user_id': str(user.id),
                    'tenant_id': str(getattr(user, 'tenant_id', '') or ''),
                }
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
