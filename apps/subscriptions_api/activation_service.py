from django.db import transaction
from django.utils import timezone
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import UserSubscription, SubscriptionPlan
import logging

logger = logging.getLogger(__name__)

class SubscriptionActivationService:
    """Servicio centralizado para reactivación de suscripciones tras pago"""
    
    @staticmethod
    @transaction.atomic
    def activate_subscription_after_payment(user, plan_id=None, payment_reference=None):
        """
        Punto único de reactivación de suscripción tras pago exitoso
        
        Args:
            user: Usuario que realizó el pago
            plan_id: ID del plan a activar (opcional, usa plan actual del tenant)
            payment_reference: Referencia del pago para auditoría
            
        Returns:
            dict: Resultado de la activación
        """
        try:
            # Validar tenant
            if not hasattr(user, 'tenant') or not user.tenant:
                raise ValueError("Usuario no tiene tenant asignado")
            
            tenant = user.tenant
            
            # Verificación de idempotencia - si ya está activo, no procesar
            if tenant.subscription_status == 'active' and tenant.is_active:
                logger.info(f"Subscription already active for user {user.id}, tenant {tenant.id}")
                return {
                    'success': True,
                    'tenant_id': tenant.id,
                    'subscription_status': tenant.subscription_status,
                    'access_level': tenant.get_access_level(),
                    'plan': tenant.subscription_plan.name if tenant.subscription_plan else None,
                    'already_active': True
                }
            
            # Determinar plan a activar
            if plan_id:
                plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
                tenant.subscription_plan = plan
            elif not tenant.subscription_plan:
                raise ValueError("No hay plan asignado al tenant")
            
            # Activar tenant
            tenant.subscription_status = 'active'
            tenant.trial_end_date = None
            tenant.trial_notifications_sent = {}
            tenant.is_active = True
            tenant.save()
            
            # Activar UserSubscription del owner
            UserSubscription.objects.filter(
                user=tenant.owner
            ).update(is_active=True)
            
            # Auditar reactivación de suscripción
            from apps.audit_api.utils import create_audit_log
            create_audit_log(
                user=user,
                action='SUBSCRIPTION_REACTIVATED',
                description=f'Suscripción reactivada tras pago - Tenant: {tenant.name} - Plan: {tenant.subscription_plan.name}',
                content_object=tenant,
                source='SUBSCRIPTIONS',
                extra_data={
                    'tenant_id': tenant.id,
                    'plan_name': tenant.subscription_plan.name,
                    'payment_reference': payment_reference,
                    'previous_status': 'suspended' if not tenant.is_active else 'trial'
                }
            )
            
            # Log de auditoría
            logger.info(f"Subscription activated for user {user.id}, tenant {tenant.id}, payment {payment_reference}")
            
            return {
                'success': True,
                'tenant_id': tenant.id,
                'subscription_status': tenant.subscription_status,
                'access_level': tenant.get_access_level(),
                'plan': tenant.subscription_plan.name if tenant.subscription_plan else None
            }
            
        except Exception as e:
            logger.error(f"Error activating subscription for user {user.id}: {str(e)}")
            raise