# ============================================================
# FIX 1: apps/billing_api/stripe_service.py
# PROBLEMA: create_customer() siempre crea un nuevo Customer en
#            Stripe, incluso si el usuario ya tiene uno.
#            stripe_customer_id ya existe en User model pero nunca
#            se persiste ni se consulta.
# SOLUCIÓN: get_or_create_customer() — busca primero en Stripe,
#            persiste el ID en user.stripe_customer_id.
# ============================================================

import stripe
from django.conf import settings
from django.utils import timezone
from .models import Invoice, PaymentAttempt
from apps.subscriptions_api.models import UserSubscription
from apps.tenants_api.models import Tenant

stripe.api_key = settings.STRIPE_SECRET_KEY  # Usar settings, no os.getenv()


class StripeService:

    @staticmethod
    def get_or_create_customer(user):
        """
        Obtener o crear cliente en Stripe.
        Persiste stripe_customer_id en el modelo User para evitar duplicados.
        Si el ID guardado ya no existe en Stripe (edge case), crea uno nuevo.
        """
        # 1. Ya tenemos el ID — verificar que sigue vivo en Stripe
        if user.stripe_customer_id:
            try:
                customer = stripe.Customer.retrieve(user.stripe_customer_id)
                if not getattr(customer, 'deleted', False):
                    return customer
            except stripe.error.InvalidRequestError:
                # El customer fue borrado en Stripe — continuar y crear uno nuevo
                pass

        # 2. Buscar por email en Stripe (previene duplicados si el ID se perdió)
        existing = stripe.Customer.list(email=user.email, limit=1)
        if existing.data:
            customer = existing.data[0]
            if not getattr(customer, 'deleted', False):
                # Guardar el ID recuperado
                type(user).objects.filter(pk=user.pk).update(
                    stripe_customer_id=customer.id
                )
                user.stripe_customer_id = customer.id
                return customer

        # 3. Crear cliente nuevo
        customer = stripe.Customer.create(
            email=user.email,
            name=getattr(user, 'full_name', '') or user.email,
            metadata={
                'user_id': str(user.id),
                'tenant_id': str(getattr(user, 'tenant_id', '') or ''),
            }
        )

        # Persistir el ID inmediatamente
        type(user).objects.filter(pk=user.pk).update(
            stripe_customer_id=customer.id
        )
        user.stripe_customer_id = customer.id
        return customer

    @staticmethod
    def create_subscription(user, price_id):
        """Crear suscripción en Stripe usando get_or_create_customer."""
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

    @staticmethod
    def cancel_subscription(subscription_id):
        """Cancelar suscripción en Stripe."""
        return stripe.Subscription.delete(subscription_id)

    @staticmethod
    def suspend_customer(customer_id):
        """Pausar cobro a cliente moroso (sin eliminar suscripción)."""
        subscriptions = stripe.Subscription.list(
            customer=customer_id, status='active'
        )
        for sub in subscriptions.data:
            stripe.Subscription.modify(
                sub.id,
                pause_collection={'behavior': 'void'}
            )
        return True
