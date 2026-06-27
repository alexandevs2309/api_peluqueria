import os
from decimal import Decimal
from rest_framework import viewsets
import logging
from rest_framework.response import Response
from rest_framework import status
from .models import SubscriptionAuditLog, UserSubscription, SubscriptionPlan, Subscription, PromotionalCredit
from .serializers import (SubscriptionAuditLogSerializer, SubscriptionPlanSerializer, UserSubscriptionSerializer, OnboardingSerializer, PublicSubscriptionPlanSerializer, PromotionalCreditSerializer)
from .permissions import IsSuperuserOrReadOnly
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from django.utils import timezone
from rest_framework.views import APIView
from django.utils import timezone
from .utils import get_user_active_subscription, log_subscription_event
from django.db import transaction
from django.conf import settings
from django.core.cache import cache
from stripe import StripeError
import stripe
from dateutil.relativedelta import relativedelta
from apps.tenants_api.models import Tenant
from apps.auth_api.models import User
from apps.roles_api.models import Role, UserRole
from apps.roles_api.default_permissions import ensure_role_default_permissions
from rest_framework.throttling import UserRateThrottle
from apps.core.tenant_permissions import TenantPermissionByAction, tenant_permission
from apps.core.permissions import IsSuperAdmin
from apps.auth_api.role_utils import get_effective_role_name
from apps.settings_api.integration_service import IntegrationService

stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
logger = logging.getLogger(__name__)


def send_purchase_confirmation(user, tenant, plan, amount, months, payment_method='stripe'):
    """Enviar confirmación de compra de plan"""
    from apps.auth_api.tasks import send_email_async
    from apps.emails.service import EmailRenderer
    from django.conf import settings as django_settings

    frontend_url = getattr(django_settings, 'FRONTEND_URL', 'http://localhost:4200').rstrip('/')
    login_url = f"{frontend_url}/auth/login"

    subject = f"¡Pago confirmado! - {plan.get_name_display()}"

    text_body = (
        f"Hola {user.full_name},\n\n"
        f"Tu pago ha sido procesado exitosamente.\n\n"
        f"Plan: {plan.get_name_display()}\n"
        f"Duración: {months} mes(es)\n"
        f"Monto: ${amount:,.2f}\n"
        f"Barbería: {tenant.name}\n"
        f"Método de pago: {payment_method}\n\n"
        f"Ya puedes disfrutar de todas las funcionalidades de tu plan.\n\n"
        f"Inicia sesión: {login_url}\n\n"
        f"El equipo de Auron Suite"
    )

    html_body = EmailRenderer.render('purchase_confirmation.html', {
        'business_name': tenant.name or 'Auron Suite',
        'title': subject,
        'user_full_name': user.full_name or user.email,
        'plan_name': plan.get_name_display(),
        'plan_duration': f'{months} mes(es)',
        'plan_amount': f'${amount:,.2f}',
        'tenant_name': tenant.name,
        'payment_method': payment_method,
        'cta_url': login_url,
        'cta_label': 'Ir a mi cuenta',
        'support_url': getattr(django_settings, 'SUPPORT_URL', ''),
    })

    logger.info("Sending purchase confirmation to user_id=%s plan=%s amount=%s", user.id, plan.id, amount)
    send_email_async.delay(subject, text_body, '', [user.email], html_message=html_body)


class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'subscriptions_api.view_subscriptionplan',
        'retrieve': 'subscriptions_api.view_subscriptionplan',
        'create': 'subscriptions_api.add_subscriptionplan',
        'update': 'subscriptions_api.change_subscriptionplan',
        'partial_update': 'subscriptions_api.change_subscriptionplan',
        'destroy': 'subscriptions_api.delete_subscriptionplan',
        'deactivate_plan': 'subscriptions_api.change_subscriptionplan',
        'public_catalog': 'subscriptions_api.view_subscriptionplan',
    }
    filterset_fields = ['is_active']
    search_fields = ['name', ]
    ordering_fields = ['price', 'duration_month']
    
    def get_permissions(self):
        # Permitir acceso público para listar planes y catálogo público
        if self.action in ['list', 'public_catalog']:
            from rest_framework.permissions import AllowAny
            return [AllowAny()]
        # Solo SuperAdmin puede crear/eliminar/modificar planes
        if self.action in ['create', 'destroy', 'update', 'partial_update']:
            from apps.core.permissions import IsSuperAdmin
            return [IsSuperAdmin()]
        return super().get_permissions()
    
    def update(self, request, *args, **kwargs):
        logger.debug("Subscription plan update requested by user_id=%s", request.user.id)
        
        # Bloquear solo las características
        blocked_fields = ['features', 'name']
        if hasattr(request.data, '_mutable'):
            request.data._mutable = True
        
        # Filtrar campos bloqueados
        for field in blocked_fields:
            if field in request.data:
                del request.data[field]
                
        try:
            return super().update(request, *args, **kwargs)
        except Exception as e:
            logger.exception("Subscription plan update failed user_id=%s", request.user.id)
            
            # Devolver error más específico
            from rest_framework.response import Response
            return Response({
                'error': str(e),
                'type': str(type(e)),
                'detail': 'Error updating subscription plan'
            }, status=400)
    
    def partial_update(self, request, *args, **kwargs):
        # Bloquear solo las características
        blocked_fields = ['features', 'name']
        if hasattr(request.data, '_mutable'):
            request.data._mutable = True
            
        # Filtrar campos bloqueados
        for field in blocked_fields:
            if field in request.data:
                del request.data[field]
                
        return super().partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Verificar suscripciones activas
        active_subs = instance.user_subscriptions.filter(is_active=True)
        if active_subs.exists():
            return Response({
                'error': 'No se puede eliminar un plan con suscripciones activas',
                'message': f'Este plan tiene {active_subs.count()} suscripciones activas. Desactívelo en su lugar.',
                'active_subscriptions': active_subs.count(),
                'suggestion': 'Desactive el plan en lugar de eliminarlo'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Solo eliminar si no hay suscripciones activas
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate_plan(self, request, pk=None):
        """Desactivar un plan de forma segura"""
        plan = self.get_object()
        
        if not plan.is_active:
            return Response({
                'message': 'El plan ya está desactivado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Desactivar el plan
        plan.is_active = False
        plan.save()
        
        # Contar suscripciones afectadas
        active_subs = plan.user_subscriptions.filter(is_active=True).count()
        
        return Response({
            'message': 'Plan desactivado correctamente',
            'plan_name': plan.name,
            'affected_subscriptions': active_subs,
            'note': 'Las suscripciones activas continuarán hasta su vencimiento'
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='public-catalog', permission_classes=[AllowAny])
    def public_catalog(self, request):
        cache_key = 'public_plan_catalog'
        cached = cache.get(cache_key)
        if cached is not None:
            resp = Response(cached)
            resp['Cache-Control'] = 'public, max-age=300'
            return resp
        plans = self.get_queryset().filter(is_active=True, is_public=True).order_by('price')
        serializer = PublicSubscriptionPlanSerializer(plans, many=True)
        cache.set(cache_key, serializer.data, 300)
        resp = Response(serializer.data)
        resp['Cache-Control'] = 'public, max-age=300'
        return resp


    

class UserSubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = UserSubscriptionSerializer
    permission_classes = [TenantPermissionByAction]
    filterset_fields = ['is_active', 'plan', 'user']
    ordering_fields = ['start_date', 'end_date', 'id']
    ordering = ['-start_date', '-id']
    permission_map = {
        'list': 'subscriptions_api.view_usersubscription',
        'retrieve': 'subscriptions_api.view_usersubscription',
        'create': 'subscriptions_api.add_usersubscription',
        'update': 'subscriptions_api.change_usersubscription',
        'partial_update': 'subscriptions_api.change_usersubscription',
        'destroy': 'subscriptions_api.delete_usersubscription',
        'cancel_subscription': 'subscriptions_api.change_usersubscription',
        'reactivate_subscription': 'subscriptions_api.change_usersubscription',
        'current': 'subscriptions_api.view_usersubscription',
    }

    def get_queryset(self):
        queryset = UserSubscription.objects.select_related('user', 'plan').all()

        if self.request.user.is_superuser:
            tenant_id = self.request.query_params.get('tenant')
            if tenant_id:
                return queryset.filter(user__tenant_id=tenant_id)
            return queryset

        tenant = getattr(self.request, 'tenant', self.request.user.tenant)
        return queryset.filter(user__tenant=tenant)

    def perform_create(self, serializer):
        user = self.request.user
        active_sub = UserSubscription.objects.filter(user=user, is_active=True).exists()
        if active_sub:
            raise serializer.ValidationError("Ya tienes una suscripción activa.")
        
        subscription = serializer.save(user=user)
        log_subscription_event(
            user=user,
            subscription=subscription,
            action='created',
            description=f'Suscripción creada para el plan "{subscription.plan.name}".'
        )

    def perform_update(self, serializer):
        original = self.get_object()
        if not original.is_active:
            raise serializers.ValidationError("No se puede actualizar una suscripción inactiva.")
        
        updated = serializer.save()
        if original.plan != updated.plan:
            log_subscription_event(
                user=updated.user,
                subscription=updated,
                action='plan_changed',
                description=f'Plan cambiado de {original.plan.name} a {updated.plan.name}.'
            )


    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_subscription(self, request, pk=None):
        from django.db import transaction
        from django.utils import timezone
        
        try:
            subscription = self.get_object()

            if not subscription.is_active:
                return Response(
                    {'detail': 'La suscripción ya está inactiva.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            if subscription.cancelled_at:
                return Response(
                    {'detail': 'La suscripción ya fue cancelada. Conservarás acceso hasta {}.'.format(
                        subscription.end_date.strftime('%d/%m/%Y') if subscription.end_date else 'el final del período'
                    )},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validar que la suscripción pertenezca al usuario (para usuarios no superusuarios)
            if not request.user.is_superuser and subscription.user != request.user:
                return Response(
                    {'detail': 'No tienes permiso para cancelar esta suscripción.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # ✅ 1. Cancelar en Stripe PRIMERO (fuera de transaction)
            stripe_cancelled = False
            if hasattr(subscription, 'stripe_subscription_id') and subscription.stripe_subscription_id:
                try:
                    import stripe
                    stripe.Subscription.modify(
                        subscription.stripe_subscription_id,
                        cancel_at_period_end=True
                    )
                    stripe_cancelled = True
                except stripe.error.StripeError as e:
                    return Response(
                        {'detail': f'Error cancelando en Stripe: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            # ✅ 2. Marcar como cancelada pero mantener acceso hasta end_date
            with transaction.atomic():
                subscription.cancelled_at = timezone.now()
                subscription.save(update_fields=['cancelled_at'])

                log_subscription_event(
                    user=request.user,
                    subscription=subscription,
                    action='cancelled',
                    description=f'Suscripción al plan "{subscription.plan.name}" cancelada. Acceso hasta {subscription.end_date.strftime("%d/%m/%Y") if subscription.end_date else "fin del período"}. Stripe: {stripe_cancelled}'
                )
            
            # Send cancellation email confirmation
            from apps.subscriptions_api.tasks import send_cancellation_confirmation_email
            try:
                send_cancellation_confirmation_email(request.user, tenant, subscription)
            except Exception as e:
                logger.error(f"Failed to send cancellation confirmation email: {e}")

            end_date_str = subscription.end_date.strftime('%d/%m/%Y') if subscription.end_date else 'el final del período'
            return Response(
                {
                    'detail': 'Suscripción cancelada correctamente.',
                    'cancelled_at': subscription.cancelled_at.isoformat(),
                    'access_until': end_date_str,
                    'stripe_cancelled': stripe_cancelled,
                    'note': f'Conservarás acceso hasta {end_date_str}. No te preocupes, no te seguiremos cobrando.'
                }, 
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {'detail': f'Error al cancelar la suscripción: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='reactivate')
    def reactivate_subscription(self, request, pk=None):
        try:
            subscription = self.get_object()

            if not subscription.is_active:
                return Response(
                    {'detail': 'La suscripción está inactiva. No se puede reactivar.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not subscription.cancelled_at:
                return Response(
                    {'detail': 'La suscripción no está cancelada.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if subscription.end_date and subscription.end_date < timezone.now():
                return Response(
                    {'detail': 'La suscripción ya expiró. Debes adquirir un nuevo plan.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not request.user.is_superuser and subscription.user != request.user:
                return Response(
                    {'detail': 'No tienes permiso para reactivar esta suscripción.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Reactivar en Stripe (quitar cancel_at_period_end)
            stripe_reactivated = False
            if hasattr(subscription, 'stripe_subscription_id') and subscription.stripe_subscription_id:
                try:
                    stripe.Subscription.modify(
                        subscription.stripe_subscription_id,
                        cancel_at_period_end=False
                    )
                    stripe_reactivated = True
                except stripe.error.StripeError as e:
                    return Response(
                        {'detail': f'Error reactivando en Stripe: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

            with transaction.atomic():
                subscription.cancelled_at = None
                subscription.save(update_fields=['cancelled_at'])

                log_subscription_event(
                    user=request.user,
                    subscription=subscription,
                    action='subscription_reactivated',
                    description=f'Suscripción al plan "{subscription.plan.name}" reactivada. Stripe: {stripe_reactivated}'
                )

            return Response(
                {
                    'detail': 'Suscripción reactivada correctamente.',
                    'stripe_reactivated': stripe_reactivated,
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {'detail': f'Error al reactivar la suscripción: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        try:
            now = timezone.now()
            subscription = UserSubscription.objects.get(
                user=request.user,
                is_active=True,
                end_date__gte=now,
            )
            serializer = UserSubscriptionSerializer(subscription)
            data = serializer.data
            data['is_cancelled'] = subscription.cancelled_at is not None
            data['cancelled_at'] = subscription.cancelled_at.isoformat() if subscription.cancelled_at else None
            data['access_until'] = subscription.end_date.isoformat() if subscription.end_date else None
            return Response(data)
        except UserSubscription.DoesNotExist:
            return Response({'detail': 'No active subscription'}, status=404)


class SubscriptionAuditLogViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionAuditLogSerializer
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'subscriptions_api.view_subscriptionauditlog',
        'retrieve': 'subscriptions_api.view_subscriptionauditlog',
        'create': 'subscriptions_api.add_subscriptionauditlog',
        'update': 'subscriptions_api.change_subscriptionauditlog',
        'partial_update': 'subscriptions_api.change_subscriptionauditlog',
        'destroy': 'subscriptions_api.delete_subscriptionauditlog',
    }

    def get_queryset(self):
        if self.request.user.is_superuser:
            return SubscriptionAuditLog.objects.all()
        tenant = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'tenant', None)
        if not tenant:
            return SubscriptionAuditLog.objects.none()
        # Mostrar logs de todos los usuarios del tenant
        return SubscriptionAuditLog.objects.filter(user__tenant=tenant)


    

class MyActiveSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        subscription = get_user_active_subscription(request.user)
        if not subscription:
            return Response({"detail": "No tienes una suscripción activa."}, status=404)
        
        serializer = UserSubscriptionSerializer(subscription)
        return Response(serializer.data)

class MyEntitlementsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Para Super-Admin, devolver entitlements limitados (no exponer capacidades)
        if get_effective_role_name(request.user, tenant=getattr(request, 'tenant', None)) == 'SuperAdmin':
            return Response({
                "plan": "admin",
                "plan_display": "Plan Administrativo",
                "features": {"management": True},
                "limits": {"max_employees": 999},  # No exponer "unlimited"
                "usage": {"employees": 0},
                "duration_month": 12
            })
        
        sub = get_user_active_subscription(request.user)
        if not sub:
            # Usuario sin suscripción - verificar si tiene tenant con plan
            employee_count = 0
            try:
                if hasattr(request.user, "tenant") and getattr(request, 'tenant', request.user.tenant) is not None:
                    from apps.employees_api.models import Employee
                    employee_count = Employee.objects.filter(tenant=getattr(request, 'tenant', request.user.tenant)).count()
                    
                    # Si el tenant tiene un plan, usar ese plan
                    if getattr(request, 'tenant', request.user.tenant).subscription_plan:
                        plan = getattr(request, 'tenant', request.user.tenant).subscription_plan
                        tenant = getattr(request, 'tenant', request.user.tenant)
                        
                        # Calcular días restantes de trial
                        trial_days_remaining = None
                        if tenant.subscription_status == 'trial' and tenant.trial_end_date:
                            trial_days_remaining = (tenant.trial_end_date - timezone.now().date()).days
                        
                        return Response({
                            "plan": plan.name,
                            "plan_display": getattr(plan, 'get_name_display', lambda: plan.name)(),
                            "features": plan.features or {},
                            "limits": {"max_employees": plan.max_employees},
                            "usage": {"employees": employee_count},
                            "duration_month": getattr(plan, 'duration_month', 1),
                            "subscription_status": tenant.subscription_status,
                            "trial_end_date": tenant.trial_end_date,
                            "trial_days_remaining": trial_days_remaining,
                            "is_trial": tenant.subscription_status == 'trial'
                        })
            except Exception:
                employee_count = 0
            
            # Sin suscripción activa — período trial
            return Response({
                "plan": "trial",
                "plan_display": "Trial",
                "features": {},
                "limits": {"max_employees": 1},
                "usage": {"employees": employee_count},
                "duration_month": 0,
                "is_trial": True
            })

        plan = sub.plan
        # Calcula usage de empleados
        employee_count = 0
        try:
            if hasattr(request.user, "tenant") and getattr(request, 'tenant', request.user.tenant) is not None:
                from apps.employees_api.models import Employee
                employee_count = Employee.objects.filter(tenant=getattr(request, 'tenant', request.user.tenant)).count()
        except Exception:
            employee_count = 0
        
        usage = {
            "employees": employee_count
        }
        limits = {
            "max_employees": plan.max_employees,  # 0 = ilimitado
        }
        # Información del tenant para trial
        tenant = getattr(request, 'tenant', request.user.tenant)
        trial_days_remaining = None
        if tenant and tenant.subscription_status == 'trial' and tenant.trial_end_date:
            trial_days_remaining = (tenant.trial_end_date - timezone.now().date()).days
        
        data = {
            "plan": plan.name,
            "plan_display": getattr(plan, 'get_name_display', lambda: plan.name)(),
            "features": plan.features or {},
            "limits": limits,
            "usage": usage,
            "duration_month": getattr(plan, 'duration_month', 1),
            "subscription_status": tenant.subscription_status if tenant else 'active',
            "trial_end_date": tenant.trial_end_date if tenant else None,
            "trial_days_remaining": trial_days_remaining,
            "is_trial": tenant.subscription_status == 'trial' if tenant else False
        }
        return Response(data)

class OnboardingView(APIView):
    permission_classes = [IsSuperAdmin]
    throttle_classes = [UserRateThrottle]   # Rate limiting

    @transaction.atomic
    def post(self, request):
        serializer = OnboardingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            # ✅ Validar que customer existe en Stripe
            try:
                customer = stripe.Customer.retrieve(data['stripe_customer_id'])
            except stripe.error.InvalidRequestError:
                return Response({
                    'error': 'Invalid Stripe customer ID'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # ✅ Validar que tiene método de pago
            if not customer.invoice_settings.default_payment_method:
                payment_methods = stripe.PaymentMethod.list(
                    customer=customer.id,
                    type='card'
                )
                if not payment_methods.data:
                    return Response({
                        'error': 'No payment method attached to customer'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # 1. Crear Tenant
            tenant = Tenant.objects.create(
                name=data['salon_name'],
                subdomain=data['salon_name'].lower().replace(' ', '')[:20],
                owner=None,  # se asigna luego
                country=data.get('country', None),
                is_active=True
            )

            # 2. Crear User ClientAdmin
            user = User.objects.create(
                email=data['owner_email'],
                full_name=data['owner_name'],
                tenant=tenant,
                role='Client-Admin',
                is_active=True,
                stripe_customer_id=customer.id  # ✅ Guardar customer_id
            )
            user.set_password(data['password'])
            user.save()

            # Asignar owner tenant
            tenant.owner = user
            tenant.save()

            # 3. Obtener plan y validar stripe_price_id
            plan = SubscriptionPlan.objects.get(id=data['plan_id'])
            billing_interval = data.get('billing_interval', 'month')
            
            # ✅ Requerir stripe_price_id/stripe_annual_price_id explícito para evitar cobros a precio incorrecto
            stripe_price_id = plan.stripe_annual_price_id if billing_interval == 'year' else plan.stripe_price_id
            if not stripe_price_id:
                return Response({
                    'error': f'Plan {plan.name} missing stripe price configuration for interval {billing_interval}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 4. Crear suscripción Stripe
            stripe_subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{'price': stripe_price_id}],
                payment_behavior='error_if_incomplete',  # ✅ Fallar si no puede cobrar
                metadata={
                    'user_id': str(user.id),
                    'tenant_id': str(tenant.id),
                    'plan_id': str(plan.id),
                    'billing_interval': billing_interval
                },
                expand=['latest_invoice.payment_intent']
            )
            
            # ✅ Validar que suscripción quedó activa
            if stripe_subscription.status not in ['active', 'trialing']:
                # Rollback automático por @transaction.atomic
                return Response({
                    'error': 'Subscription creation failed',
                    'status': stripe_subscription.status,
                    'message': 'Payment was not successful'
                }, status=status.HTTP_402_PAYMENT_REQUIRED)

            # 5. Crear Subscription local
            subscription = Subscription.objects.create(
                tenant=tenant,
                plan=plan,
                stripe_subscription_id=stripe_subscription.id,
                is_active=True,
                billing_interval=billing_interval
            )

            # 6. Asignar rol ClientAdmin
            admin_role = Role.objects.get(name='Client-Admin')
            ensure_role_default_permissions(admin_role)
            UserRole.objects.create(user=user, role=admin_role, tenant=tenant)

            return Response({
                'detail': 'Onboarding completado exitosamente.',
                'tenant_id': tenant.id,
                'user_id': user.id,
                'subscription_id': subscription.id,
                'stripe_subscription_status': stripe_subscription.status
            }, status=status.HTTP_201_CREATED)

        except StripeError as e:
            transaction.set_rollback(True)
            return Response({'error': 'Error en Stripe: ' + str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            transaction.set_rollback(True)
            return Response({'error': 'Error interno: ' + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class RenewSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def _parse_months(self, raw_months):
        try:
            months = int(raw_months or 1)
        except (TypeError, ValueError):
            return None
        if months < 1 or months > 24:
            return None
        return months

    def _apply_paid_access(self, tenant, user, plan, months, auto_renew=False, access_until_override=None, billing_interval='month'):
        now = timezone.now()
        base_time = now
        if tenant.access_until and tenant.access_until > now:
            base_time = tenant.access_until
        access_until = access_until_override or (base_time + relativedelta(months=months))

        tenant.subscription_plan = plan
        tenant.subscription_status = 'active'
        tenant.trial_end_date = None
        tenant.is_active = True
        tenant.access_until = access_until
        if plan:
            tenant.plan_type = plan.name
        tenant.save(update_fields=[
            'subscription_plan',
            'plan_type',
            'subscription_status',
            'trial_end_date',
            'is_active',
            'access_until',
            'updated_at'
        ])

        UserSubscription.objects.filter(user=user, is_active=True).update(
            is_active=False,
            end_date=now
        )
        UserSubscription.objects.create(
            user=user,
            plan=plan,
            start_date=base_time,
            end_date=access_until,
            is_active=True,
            auto_renew=auto_renew,
            billing_interval=billing_interval
        )
        return access_until

    def _create_paypal_order(self, request, tenant, plan, months, auto_renew, billing_interval='month'):
        if auto_renew:
            return self._create_paypal_subscription(request, tenant, plan, billing_interval)

        from apps.payments_api.services import PayPalService
        svc = PayPalService()
        result, err = svc.create_order(request.user, tenant, plan, months, billing_interval, auto_renew)
        if err:
            return Response(err, status=status.HTTP_502_BAD_GATEWAY)

        cache.set(
            PayPalService.order_cache_key(result['order_id']),
            {
                'user_id': request.user.id,
                'tenant_id': tenant.id,
                'plan_id': plan.id,
                'months': months,
                'auto_renew': auto_renew,
                'billing_interval': billing_interval,
                'amount': result['amount'],
            },
            timeout=60 * 60 * 24,
        )

        return Response({
            'provider': 'paypal',
            'order_id': result['order_id'],
            'approve_url': result['approve_url'],
            'sandbox': result['sandbox'],
        })

    def _create_paypal_subscription(self, request, tenant, plan, billing_interval):
        from apps.payments_api.services import PayPalService
        svc = PayPalService()
        result, err = svc.create_subscription(request.user, tenant, plan, billing_interval)
        if err:
            return Response(err, status=status.HTTP_502_BAD_GATEWAY)

        # Usar el cache para recordar qué plan intentó suscribirse y poder confirmarlo en caso de webhooks fallidos o lentos
        cache.set(
            PayPalService.order_cache_key(result['subscription_id']),
            {
                'user_id': request.user.id,
                'tenant_id': tenant.id,
                'plan_id': plan.id,
                'billing_interval': billing_interval,
            },
            timeout=60 * 60 * 24,
        )

        return Response({
            'provider': 'paypal_subscription',
            'subscription_id': result['subscription_id'],
            'approve_url': result['approve_url'],
            'sandbox': result['sandbox'],
        })

    def _capture_paypal_order(self, request, tenant, order_id):
        if not order_id:
            return Response({'error': 'PayPal order ID required'}, status=status.HTTP_400_BAD_REQUEST)

        from apps.payments_api.services import PayPalService
        svc = PayPalService()
        cache_key = PayPalService.capture_cache_key(order_id)

        cached_completion = cache.get(cache_key)
        if cached_completion:
            return Response(cached_completion)

        cached_order = cache.get(PayPalService.order_cache_key(order_id))
        if not cached_order:
            return Response({
                'error': 'PayPal order expired',
                'message': 'La orden no existe o expiro. Inicia el checkout nuevamente.'
            }, status=status.HTTP_410_GONE)

        if cached_order.get('user_id') != request.user.id or cached_order.get('tenant_id') != tenant.id:
            return Response({
                'error': 'PayPal order mismatch',
                'message': 'La orden PayPal no pertenece a esta cuenta.'
            }, status=status.HTTP_403_FORBIDDEN)

        capture, err = svc.capture_order(order_id)
        if err:
            return Response(err, status=status.HTTP_502_BAD_GATEWAY)

        try:
            plan = SubscriptionPlan.objects.get(id=cached_order['plan_id'], is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({'error': 'Invalid plan'}, status=status.HTTP_400_BAD_REQUEST)

        from apps.billing_api.models import Invoice

        with transaction.atomic():
            access_until = self._apply_paid_access(
                tenant,
                request.user,
                plan,
                cached_order['months'],
                auto_renew=False,
                billing_interval=cached_order.get('billing_interval', 'month')
            )

            payment = PayPalService.create_payment_record(
                user=request.user,
                tenant=tenant,
                amount=Decimal(cached_order['amount']),
                capture_id=capture['capture_id'],
                order_id=order_id,
                plan=plan,
                months=cached_order['months'],
            )

            Invoice.objects.create(
                user=request.user,
                tenant=tenant,
                amount=Decimal(cached_order['amount']),
                due_date=timezone.now(),
                is_paid=True,
                paid_at=timezone.now(),
                payment_method='paypal',
                status='paid',
                stripe_payment_intent_id=capture['capture_id'],
                paypal_order_id=order_id,
                payment=payment,
                description=f"Subscription renewal - {plan.get_name_display()} ({'Anual' if cached_order.get('billing_interval') == 'year' else 'Mensual'}) x{cached_order['months']}m (PayPal {order_id})"
            )

        response_payload = {
            'message': 'Subscription renewed successfully',
            'provider': 'paypal',
            'plan': plan.name,
            'status': tenant.subscription_status,
            'access_level': tenant.get_access_level(),
            'months': cached_order['months'],
            'access_until': access_until,
            'order_id': order_id,
            'capture_id': capture['capture_id'],
        }

        send_purchase_confirmation(
            request.user, tenant, plan,
            plan.price * cached_order['months'],
            cached_order['months'],
            payment_method='paypal'
        )

        cache.set(cache_key, response_payload, timeout=60 * 60 * 24 * 7)
        cache.delete(PayPalService.order_cache_key(order_id))
        return Response(response_payload)

    def _capture_paypal_subscription(self, request, tenant, subscription_id):
        if not subscription_id:
            return Response({'error': 'PayPal subscription ID required'}, status=status.HTTP_400_BAD_REQUEST)

        from apps.payments_api.services import PayPalService
        svc = PayPalService()
        cache_key = PayPalService.capture_cache_key(subscription_id)

        cached_completion = cache.get(cache_key)
        if cached_completion:
            return Response(cached_completion)

        cached_order = cache.get(PayPalService.order_cache_key(subscription_id))
        if not cached_order:
            return Response({
                'error': 'PayPal subscription expired or not found',
                'message': 'La suscripción no existe en nuestro registro. Inicia el checkout nuevamente.'
            }, status=status.HTTP_410_GONE)

        if cached_order.get('user_id') != request.user.id or cached_order.get('tenant_id') != tenant.id:
            return Response({
                'error': 'PayPal subscription mismatch',
                'message': 'La suscripción PayPal no pertenece a esta cuenta.'
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            plan = SubscriptionPlan.objects.get(id=cached_order['plan_id'], is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({'error': 'Invalid plan'}, status=status.HTTP_400_BAD_REQUEST)

        # En lugar de "capturar" un pago, en suscripciones de PayPal solo comprobamos el estado.
        # Si el usuario aprobó en frontend, PayPal empezará a cobrar y enviará webhooks.
        # Asumiremos la suscripción como exitosa preliminarmente y le daremos 1 día de gracia si no hay pago inmediato.
        # El webhook BILLING.SUBSCRIPTION.ACTIVATED o PAYMENT.SALE.COMPLETED actualizará permanentemente.
        with transaction.atomic():
            access_until = self._apply_paid_access(
                tenant,
                request.user,
                plan,
                1,  # Temporal grace period or actual period if webhook was fast
                auto_renew=True,
                billing_interval=cached_order.get('billing_interval', 'month')
            )

            Subscription.objects.filter(tenant=tenant, is_active=True).update(is_active=False)
            Subscription.objects.update_or_create(
                tenant=tenant,
                plan=plan,
                defaults={
                    'paypal_subscription_id': subscription_id,
                    'is_active': True,
                    'billing_interval': cached_order.get('billing_interval', 'month')
                }
            )

        response_payload = {
            'message': 'Subscription approved successfully',
            'provider': 'paypal_subscription',
            'plan': plan.name,
            'status': tenant.subscription_status,
            'access_level': tenant.get_access_level(),
            'access_until': access_until,
            'subscription_id': subscription_id
        }

        cache.set(cache_key, response_payload, timeout=60 * 60 * 24 * 7)
        cache.delete(PayPalService.order_cache_key(subscription_id))
        return Response(response_payload)

    def _handle_auto_renew_payment(self, tenant, user, plan, payment_method_id, customer_id, billing_interval='month', months=1):
        # Adjuntar método de pago y establecerlo por defecto para cobros automáticos.
        try:
            stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)
        except stripe.error.InvalidRequestError:
            # Ya adjunto u otro estado aceptable.
            pass

        stripe.Customer.modify(
            customer_id,
            invoice_settings={'default_payment_method': payment_method_id}
        )

        stripe_price_id = plan.stripe_annual_price_id if billing_interval == 'year' else plan.stripe_price_id
        if not stripe_price_id:
            return Response({
                'error': f'Plan {plan.name} missing stripe price configuration for interval {billing_interval}'
            }, status=status.HTTP_400_BAD_REQUEST)

        stripe_subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{'price': stripe_price_id}],
            default_payment_method=payment_method_id,
            payment_behavior='default_incomplete',
            metadata={
                'user_id': str(user.id),
                'tenant_id': str(tenant.id),
                'plan_id': str(plan.id),
                'billing_interval': billing_interval,
                'months': str(months)
            },
            expand=['latest_invoice.payment_intent']
        )

        latest_invoice = stripe_subscription.get('latest_invoice') or {}
        latest_payment_intent = latest_invoice.get('payment_intent') or {}
        if latest_payment_intent.get('status') == 'requires_action':
            return Response({
                'requires_action': True,
                'payment_intent_id': latest_payment_intent.get('id'),
                'client_secret': latest_payment_intent.get('client_secret'),
                'status': latest_payment_intent.get('status'),
                'auto_renew': True
            }, status=status.HTTP_200_OK)

        if stripe_subscription.status not in {'active', 'trialing'}:
            return Response({
                'error': 'Subscription activation failed',
                'status': stripe_subscription.status
            }, status=402)

        period_end_ts = stripe_subscription.get('current_period_end')
        access_until_override = timezone.datetime.fromtimestamp(
            period_end_ts, tz=timezone.utc
        ) if period_end_ts else None

        with transaction.atomic():
            access_until = self._apply_paid_access(
                tenant, user, plan, months=months,
                auto_renew=True,
                access_until_override=access_until_override,
                billing_interval=billing_interval
            )

            Subscription.objects.filter(tenant=tenant, is_active=True).update(is_active=False)
            Subscription.objects.update_or_create(
                tenant=tenant,
                plan=plan,
                defaults={
                    'stripe_subscription_id': stripe_subscription.id,
                    'is_active': True,
                    'billing_interval': billing_interval
                }
            )

            from apps.billing_api.models import Invoice
            first_invoice = stripe_subscription.get('latest_invoice') or {}
            first_payment_intent = first_invoice.get('payment_intent') or {}
            price_per_cycle = plan.annual_price if billing_interval == 'year' else plan.price
            if billing_interval == 'year' and not price_per_cycle:
                price_per_cycle = plan.price * 12 * Decimal('0.8')
            amount_paid = first_invoice.get('amount_paid') or int(price_per_cycle * 100)
            Invoice.objects.create(
                user=user,
                tenant=tenant,
                amount=amount_paid / 100,
                due_date=timezone.now(),
                is_paid=True,
                paid_at=timezone.now(),
                payment_method='stripe',
                status='paid',
                stripe_payment_intent_id=first_payment_intent.get('id'),
                description=f"Auto-renew subscription - {plan.get_name_display()} ({'Anual' if billing_interval == 'year' else 'Mensual'})"
            )

        send_purchase_confirmation(
            user, tenant, plan,
            amount_paid / 100 if isinstance(amount_paid, int) else plan.price,
            1,
            payment_method='stripe'
        )

        return Response({
            'message': 'Auto-renew subscription activated successfully',
            'plan': plan.name,
            'status': tenant.subscription_status,
            'access_level': tenant.get_access_level(),
            'months': months,
            'access_until': access_until,
            'auto_renew': True,
            'stripe_subscription_id': stripe_subscription.id
        })
    
    def get(self, request):
        """Obtener información de renovación"""
        # SuperAdmin no necesita renovar suscripción
        if get_effective_role_name(request.user, tenant=getattr(request, 'tenant', None)) == 'SuperAdmin':
            return Response({
                'tenant_name': 'Sistema Administrativo',
                'current_status': 'active',
                'trial_end_date': None,
                'access_level': 'full',
                'days_in_grace': 0,
                'available_plans': [],
                'is_superadmin': True
            }, status=200)
            
        tenant = getattr(request, 'tenant', None) or getattr(request.user, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant found'}, status=400)
        
        # Obtener planes disponibles
        plans = SubscriptionPlan.objects.filter(is_active=True, is_public=True)
        plans_data = SubscriptionPlanSerializer(plans, many=True).data
        access_level = tenant.get_access_level()
        days_in_grace = 0
        if tenant.subscription_status == 'past_due' and tenant.access_until:
            days_in_grace = max(0, 7 - (timezone.now() - tenant.access_until).days)
        
        return Response({
            'tenant_name': tenant.name,
            'current_status': tenant.subscription_status,
            'trial_end_date': tenant.trial_end_date,
            'access_until': tenant.access_until,
            'access_level': access_level,
            'days_in_grace': days_in_grace,
            'available_plans': plans_data
        })
    
    def post(self, request):
        """Renovar suscripción con pago real"""
        # SuperAdmin no necesita renovar suscripción
        if get_effective_role_name(request.user, tenant=getattr(request, 'tenant', None)) == 'SuperAdmin':
            return Response({'error': 'SuperAdmin does not need subscription renewal'}, status=400)
            
        tenant = getattr(request, 'tenant', None) or getattr(request.user, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant found'}, status=400)

        plan_id = request.data.get('plan_id')
        payment_method_id = request.data.get('payment_method_id')
        payment_intent_id = request.data.get('payment_intent_id')
        paypal_action = request.data.get('paypal_action')
        paypal_order_id = request.data.get('paypal_order_id')

        payment_provider = request.data.get('payment_provider')
        if not payment_provider:
            if paypal_action or paypal_order_id:
                payment_provider = 'paypal'
            else:
                payment_provider = 'stripe'

        billing_interval = str(request.data.get('billing_interval') or 'month').strip().lower()
        if billing_interval not in {'month', 'year'}:
            return Response({'error': 'billing_interval must be either "month" or "year"'}, status=400)

        months = self._parse_months(request.data.get('months'))
        if billing_interval == 'year':
            months = 12

        auto_renew_raw = request.data.get('auto_renew', False)
        auto_renew = str(auto_renew_raw).lower() in {'1', 'true', 'yes', 'on'}

        if payment_provider not in {'stripe', 'paypal'}:
            return Response({
                'error': 'Unsupported payment provider',
                'message': f'Proveedor no soportado: {payment_provider}'
            }, status=status.HTTP_400_BAD_REQUEST)

        if payment_provider == 'paypal' and paypal_action == 'capture_order':
            return self._capture_paypal_order(request, tenant, paypal_order_id)
            
        if payment_provider == 'paypal' and paypal_action == 'capture_subscription':
            subscription_id = request.data.get('subscription_id')
            return self._capture_paypal_subscription(request, tenant, subscription_id)

        if months is None:
            return Response({'error': 'Months must be an integer between 1 and 24'}, status=400)
        if auto_renew and months not in {1, 12}:
            return Response({'error': 'Auto-renew currently supports only 1 month or 12 months (1 year) per cycle'}, status=400)
        if not plan_id:
            return Response({'error': 'Plan ID required'}, status=400)
        
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({'error': 'Invalid plan'}, status=400)

        if payment_provider == 'paypal':
            logger.info(
                'PayPal renewal request user=%s tenant=%s plan=%s months=%s action=%s',
                request.user.id,
                tenant.id,
                plan.id,
                months,
                paypal_action,
            )
            return self._create_paypal_order(request, tenant, plan, months, auto_renew, billing_interval=billing_interval)

        if not payment_method_id and not payment_intent_id:
            return Response({'error': 'Payment method or payment intent required'}, status=400)
        
        # En desarrollo permitimos activación manual para no bloquear onboarding.
        # Producción siempre requiere Stripe.
        if settings.DEBUG and payment_method_id in {'manual', 'manual_entry', 'test'}:
            if auto_renew:
                return Response({'error': 'Auto-renew requires a real Stripe payment method'}, status=400)
            with transaction.atomic():
                access_until = self._apply_paid_access(tenant, request.user, plan, months, billing_interval=billing_interval)

                from apps.billing_api.models import Invoice
                price_per_cycle = plan.annual_price if billing_interval == 'year' else plan.price
                if billing_interval == 'year' and not price_per_cycle:
                    price_per_cycle = plan.price * 12 * Decimal('0.8')

                if billing_interval == 'year':
                    total_amount_val = price_per_cycle * months / 12
                else:
                    total_amount_val = price_per_cycle * months

                Invoice.objects.create(
                    user=request.user,
                    tenant=tenant,
                    amount=total_amount_val,
                    due_date=timezone.now(),
                    is_paid=True,
                    paid_at=timezone.now(),
                    payment_method='transfer',
                    status='paid',
                    description=f"Subscription renewal (manual dev) - {plan.get_name_display()} x{months}m"
                )

            send_purchase_confirmation(
                request.user, tenant, plan,
                total_amount_val,
                months,
                payment_method='transfer'
            )

            return Response({
                'message': 'Subscription renewed successfully (manual dev mode)',
                'plan': plan.name,
                'status': tenant.subscription_status,
                'access_level': tenant.get_access_level(),
                'months': months,
                'access_until': access_until,
                'auto_renew': False,
                'payment_mode': 'manual_dev'
            })

        # ✅ PAGO REAL con Stripe
        try:
            # Obtener o crear customer en Stripe
            if not hasattr(request.user, 'stripe_customer_id') or not request.user.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=request.user.email,
                    name=request.user.full_name,
                    metadata={'user_id': request.user.id, 'tenant_id': tenant.id}
                )
                request.user.stripe_customer_id = customer.id
                request.user.save(update_fields=['stripe_customer_id'])
            else:
                customer = stripe.Customer.retrieve(request.user.stripe_customer_id)

            if payment_intent_id:
                payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
                if payment_intent.customer and str(payment_intent.customer) != str(customer.id):
                    return Response({
                        'error': 'Payment intent does not belong to this customer'
                    }, status=status.HTTP_400_BAD_REQUEST)

                if payment_intent.status == 'requires_action':
                    return Response({
                        'error': 'Authentication still pending',
                        'message': 'Payment intent is still awaiting 3D Secure confirmation.',
                        'payment_intent_id': payment_intent.id,
                        'status': payment_intent.status
                    }, status=status.HTTP_409_CONFLICT)

                if payment_intent.status != 'succeeded':
                    return Response({
                        'error': 'Payment failed',
                        'status': payment_intent.status,
                        'message': 'Payment was not successful'
                    }, status=402)

                # Validar metadata para evitar fraude o desajustes
                metadata = payment_intent.metadata or {}
                if (
                    ('user_id' in metadata and str(metadata.get('user_id')) != str(request.user.id))
                    or ('tenant_id' in metadata and str(metadata.get('tenant_id')) != str(tenant.id))
                    or ('plan_id' in metadata and str(metadata.get('plan_id')) != str(plan.id))
                    or ('months' in metadata and str(metadata.get('months')) != str(months))
                    or ('billing_interval' in metadata and str(metadata.get('billing_interval')) != str(billing_interval))
                ):
                    return Response({
                        'error': 'Payment intent metadata mismatch'
                    }, status=status.HTTP_400_BAD_REQUEST)

                access_until_override = None
                stripe_subscription_id = payment_intent.get('subscription')
                if auto_renew and stripe_subscription_id:
                    try:
                        stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)
                        period_end_ts = stripe_subscription.get('current_period_end')
                        access_until_override = timezone.datetime.fromtimestamp(
                            period_end_ts, tz=timezone.utc
                        ) if period_end_ts else None
                    except stripe.error.StripeError:
                        access_until_override = None

                from apps.billing_api.models import Invoice
                with transaction.atomic():
                    existing_invoice = Invoice.objects.select_for_update().filter(
                        stripe_payment_intent_id=payment_intent.id
                    ).first()
                    if existing_invoice:
                        return Response({
                            'message': 'Payment already processed',
                            'plan': plan.name,
                            'status': tenant.subscription_status,
                            'access_level': tenant.get_access_level(),
                            'months': months,
                            'access_until': tenant.access_until,
                            'payment_intent_id': payment_intent.id
                        })

                    access_until = self._apply_paid_access(
                        tenant,
                        request.user,
                        plan,
                        months,
                        auto_renew=auto_renew,
                        access_until_override=access_until_override,
                        billing_interval=billing_interval
                    )

                    if auto_renew and stripe_subscription_id:
                        Subscription.objects.filter(tenant=tenant, is_active=True).update(is_active=False)
                        Subscription.objects.update_or_create(
                            tenant=tenant,
                            plan=plan,
                            defaults={
                                'stripe_subscription_id': stripe_subscription_id,
                                'is_active': True,
                                'billing_interval': billing_interval
                            }
                        )

                    price_per_cycle = plan.annual_price if billing_interval == 'year' else plan.price
                    if billing_interval == 'year' and not price_per_cycle:
                        price_per_cycle = plan.price * 12 * Decimal('0.8')

                    if billing_interval == 'year':
                        fallback_amount = (price_per_cycle * months) / 12
                    else:
                        fallback_amount = price_per_cycle * months

                    amount = (payment_intent.amount or int(fallback_amount * 100)) / 100
                    Invoice.objects.create(
                        user=request.user,
                        tenant=tenant,
                        amount=amount,
                        due_date=timezone.now(),
                        is_paid=True,
                        paid_at=timezone.now(),
                        payment_method='stripe',
                        status='paid',
                        stripe_payment_intent_id=payment_intent.id,
                        description=f"Subscription renewal - {plan.get_name_display()} ({'Anual' if billing_interval == 'year' else 'Mensual'}) x{months}m"
                    )

                send_purchase_confirmation(
                    request.user, tenant, plan,
                    amount,
                    months,
                    payment_method='stripe'
                )

                return Response({
                    'message': 'Subscription renewed successfully',
                    'plan': plan.name,
                    'status': tenant.subscription_status,
                    'access_level': tenant.get_access_level(),
                    'months': months,
                    'access_until': access_until,
                    'payment_intent_id': payment_intent.id
                })

            if auto_renew:
                return self._handle_auto_renew_payment(tenant, request.user, plan, payment_method_id, customer.id, billing_interval=billing_interval, months=months)
            
            price_per_cycle = plan.annual_price if billing_interval == 'year' else plan.price
            if billing_interval == 'year' and not price_per_cycle:
                price_per_cycle = plan.price * 12 * Decimal('0.8')

            if billing_interval == 'year':
                total_amount_val = price_per_cycle * months / 12
            else:
                total_amount_val = price_per_cycle * months

            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:4200').rstrip('/')
            return_url = request.data.get('return_url') or f"{frontend_url}/client/payment"

            payment_intent = stripe.PaymentIntent.create(
                amount=int(total_amount_val * 100),  # Centavos
                currency='usd',
                customer=customer.id,
                payment_method=payment_method_id,
                confirm=True,  # ✅ Cobrar inmediatamente
                return_url=return_url,
                metadata={
                    'user_id': str(request.user.id),
                    'tenant_id': str(tenant.id),
                    'plan_id': str(plan.id),
                    'months': str(months),
                    'billing_interval': billing_interval
                }
            )
            
            # ✅ Manejar 3D Secure / requires_action
            if payment_intent.status == 'requires_action':
                return Response({
                    'requires_action': True,
                    'payment_intent_id': payment_intent.id,
                    'client_secret': payment_intent.client_secret,
                    'status': payment_intent.status
                }, status=status.HTTP_200_OK)

            # ✅ Validar que el pago fue exitoso
            if payment_intent.status != 'succeeded':
                return Response({
                    'error': 'Payment failed',
                    'status': payment_intent.status,
                    'message': 'Payment was not successful'
                }, status=402)
            
            # Solo entonces activar nueva suscripción
            with transaction.atomic():
                access_until = self._apply_paid_access(tenant, request.user, plan, months, billing_interval=billing_interval)
                
                # Crear factura local
                from apps.billing_api.models import Invoice
                Invoice.objects.create(
                    user=request.user,
                    tenant=tenant,
                    amount=total_amount_val,
                    due_date=timezone.now(),
                    is_paid=True,
                    paid_at=timezone.now(),
                    payment_method='stripe',
                    status='paid',
                    stripe_payment_intent_id=payment_intent.id,
                    description=f"Subscription renewal - {plan.get_name_display()} ({'Anual' if billing_interval == 'year' else 'Mensual'}) x{months}m"
                )

            send_purchase_confirmation(
                request.user, tenant, plan,
                total_amount_val,
                months,
                payment_method='stripe'
            )

            return Response({
                'message': 'Subscription renewed successfully',
                'plan': plan.name,
                'status': tenant.subscription_status,
                'access_level': tenant.get_access_level(),
                'months': months,
                'access_until': access_until,
                'payment_intent_id': payment_intent.id
            })
            
        except stripe.error.CardError as e:
            return Response({
                'error': 'Card declined',
                'message': str(e.user_message)
            }, status=402)
        except stripe.error.StripeError as e:
            return Response({
                'error': 'Payment processing error',
                'message': str(e)
            }, status=500)
        except Exception as e:
            return Response({
                'error': 'Internal error',
                'message': str(e)
            }, status=500)


class PromotionalCreditViewSet(viewsets.ModelViewSet):
    queryset = PromotionalCredit.objects.all()
    serializer_class = PromotionalCreditSerializer
    permission_classes = [IsSuperAdmin]
    filterset_fields = ['campaign_tag', 'tenant']
    search_fields = ['campaign_tag', 'reason', 'tenant__name']
    ordering_fields = ['created_at', 'months', 'tenant__name']
    ordering = ['-created_at']
