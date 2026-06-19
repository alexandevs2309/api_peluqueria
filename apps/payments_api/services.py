try:
    import stripe
except ImportError:
    stripe = None

from django.conf import settings
from django.db.models import Q
import logging
from .models import Payment, PaymentProvider
from apps.subscriptions_api.models import UserSubscription, SubscriptionPlan
from apps.tenants_api.models import Tenant
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)

class StripeService:
    def __init__(self):
        if not stripe:
            raise Exception("Stripe library not installed. Run: pip install stripe")
        self.stripe = stripe
        provider = PaymentProvider.objects.filter(name='stripe', is_active=True).first()
        if provider:
            self.stripe.api_key = provider.get_api_key()
    
    def create_customer(self, user):
        """Crear cliente en Stripe"""
        try:
            customer = self.stripe.Customer.create(
                email=user.email,
                name=user.full_name,
                metadata={'user_id': user.id}
            )
            return customer
        except Exception as e:
            raise Exception(f"Error creating Stripe customer: {str(e)}")
    
    def create_subscription_payment(self, user, plan_id):
        """Crear pago para suscripción"""
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
            
            # Crear customer si no existe
            customer = self.create_customer(user)
            
            # Crear payment intent
            payment_intent = self.stripe.PaymentIntent.create(
                amount=int(plan.price * 100),  # Stripe usa centavos
                currency='usd',
                customer=customer.id,
                metadata={
                    'user_id': user.id,
                    'plan_id': plan.id,
                    'type': 'subscription'
                }
            )
            
            # Crear registro de pago
            payment = Payment.objects.create(
                user=user,
                provider=PaymentProvider.objects.get(name='stripe'),
                amount=plan.price,
                provider_payment_id=payment_intent.id,
                provider_customer_id=customer.id,
                metadata={
                    'plan_id': plan.id,
                    'plan_name': plan.name
                }
            )
            
            return {
                'payment_id': payment.id,
                'client_secret': payment_intent.client_secret,
                'amount': plan.price
            }
            
        except Exception as e:
            raise Exception(f"Error creating subscription payment: {str(e)}")

class OnboardingService:
    @staticmethod
    def complete_subscription_purchase(payment_id):
        """Completar proceso de compra y crear tenant automáticamente"""
        try:
            payment = Payment.objects.get(id=payment_id)
            
            if payment.status != 'completed':
                raise Exception("Payment not completed")
            
            user = payment.user
            plan_id = payment.metadata.get('plan_id')
            plan = SubscriptionPlan.objects.get(id=plan_id)
            
            # 1. Crear tenant automáticamente
            tenant = Tenant.objects.create(
                name=f"{user.full_name}'s Barbershop",
                owner=user.email,
                is_active=True
            )
            
            # 2. Asignar tenant al usuario
            user.tenant = tenant
            user.save()
            
            # 3. Crear suscripción
            subscription = UserSubscription.objects.create(
                user=user,
                plan=plan,
                is_active=True,
                auto_renew=True
            )
            
            # 4. Vincular pago con suscripción
            payment.subscription = subscription
            payment.save()
            
            # 5. Asignar rol Client-Admin
            from apps.roles_api.models import Role, UserRole
            from apps.roles_api.default_permissions import ensure_role_default_permissions
            client_admin_role = Role.objects.get(name='Client-Admin')
            ensure_role_default_permissions(client_admin_role)
            UserRole.objects.get_or_create(
                user=user,
                role=client_admin_role,
                tenant=tenant
            )
            
            return {
                'tenant': tenant,
                'subscription': subscription,
                'success': True
            }
            
        except Exception as e:
            raise Exception(f"Error completing onboarding: {str(e)}")

class NotificationService:
    @staticmethod
    def send_welcome_email(user, tenant):
        """Enviar email de bienvenida"""
        from apps.notifications_api.models import NotificationTemplate, Notification
        template = NotificationTemplate.objects.filter(
            Q(notification_type='welcome'),
            Q(type='email'),
            Q(tenant=tenant) | Q(tenant__isnull=True),
            is_active=True
        ).first()
        if template:
            notification = Notification.objects.create(
                recipient=user,
                template=template,
                subject=template.subject or f"¡Bienvenido a Auron Suite!",
                message=template.body,
                metadata={'tenant_id': str(tenant.id), 'user_name': user.full_name or user.email}
            )
            notification.send()
            logger.info("Welcome email sent user_id=%s tenant_id=%s notification_id=%s", user.id, tenant.id, notification.id)
        else:
            logger.warning("No active welcome email template found")
    
    @staticmethod
    def send_payment_confirmation(user, payment):
        """Enviar confirmación de pago"""
        from apps.notifications_api.models import NotificationTemplate, Notification
        template = NotificationTemplate.objects.filter(
            Q(notification_type='payment_received'),
            Q(type='email'),
            Q(tenant=user.tenant) | Q(tenant__isnull=True),
            is_active=True
        ).first()
        if template:
            notification = Notification.objects.create(
                recipient=user,
                template=template,
                subject=template.subject or "Pago recibido",
                message=template.body,
                metadata={
                    'payment_id': str(payment.id),
                    'amount': str(payment.amount),
                    'user_name': user.full_name or user.email
                }
            )
            notification.send()
            logger.info("Payment confirmation sent user_id=%s payment_id=%s notification_id=%s", user.id, payment.id, notification.id)
        else:
            logger.warning("No active payment_received email template found")
    
    @staticmethod
    def send_subscription_expiry_warning(user, subscription):
        """Enviar advertencia de expiración"""
        from apps.notifications_api.models import NotificationTemplate, Notification
        template = NotificationTemplate.objects.filter(
            Q(notification_type='subscription_expiring'),
            Q(type='email'),
            Q(tenant=user.tenant) | Q(tenant__isnull=True),
            is_active=True
        ).first()
        if template:
            notification = Notification.objects.create(
                recipient=user,
                template=template,
                subject=template.subject or "Suscripción próxima a vencer",
                message=template.body,
                metadata={
                    'subscription_id': str(subscription.id),
                    'plan_name': subscription.plan.name if subscription.plan else 'N/A',
                    'user_name': user.full_name or user.email
                }
            )
            notification.send()
            logger.info("Subscription expiry warning sent user_id=%s subscription_id=%s notification_id=%s", user.id, subscription.id, notification.id)
        else:
            logger.warning("No active subscription_expiring email template found")
