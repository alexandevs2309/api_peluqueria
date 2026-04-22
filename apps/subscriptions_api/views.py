from rest_framework import viewsets
import logging
from rest_framework.response import Response
from rest_framework import status
from .models import SubscriptionAuditLog, UserSubscription, SubscriptionPlan, Subscription
from .serializers import  SubscriptionAuditLogSerializer, SubscriptionPlanSerializer , UserSubscriptionSerializer, OnboardingSerializer, PublicSubscriptionPlanSerializer
from .permissions import IsSuperuserOrReadOnly
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from django.utils import timezone
from rest_framework.views import APIView
from django.utils import timezone
from .utils import get_user_active_subscription, log_subscription_event
from django.db import transaction
from django.conf import settings
from stripe.error import StripeError
import stripe
from dateutil.relativedelta import relativedelta
from apps.tenants_api.models import Tenant
from apps.auth_api.models import User
from apps.roles_api.models import Role, UserRole
from rest_framework.throttling import UserRateThrottle
from apps.core.tenant_permissions import TenantPermissionByAction, tenant_permission
from apps.core.permissions import IsSuperAdmin

stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
logger = logging.getLogger(__name__)


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
    }
    filterset_fields = ['is_active']
    search_fields = ['name', ]
    ordering_fields = ['price', 'duration_month']
    
    def get_permissions(self):
        # Permitir acceso público para listar planes
        if self.action == 'list':
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
        plans = self.get_queryset().filter(is_active=True).order_by('price')
        serializer = PublicSubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data)


    

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
        'current': 'subscriptions_api.view_usersubscription',
    }

    def get_queryset(self):
        queryset = UserSubscription.objects.select_related('user', 'plan').all()

        if self.request.user.is_superuser:
            tenant_id = self.request.query_params.get('tenant')
            if tenant_id:
                return queryset.filter(user__tenant_id=tenant_id)
            return queryset

        return queryset.filter(user=self.request.user)
    
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
        
        try:
            subscription = self.get_object()

            if not subscription.is_active:
                return Response(
                    {'detail': 'La suscripción ya está inactiva.'}, 
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
                    stripe.Subscription.modify(
                        subscription.stripe_subscription_id,
                        cancel_at_period_end=True
                    )
                    stripe_cancelled = True
                except stripe.error.StripeError as e:
                    # ✅ Fallar antes de modificar DB
                    return Response(
                        {'detail': f'Error cancelando en Stripe: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            # ✅ 2. Solo actualizar DB si Stripe tuvo éxito
            with transaction.atomic():
                subscription.is_active = False
                subscription.save(update_fields=['is_active'])

                log_subscription_event(
                    user=request.user,
                    subscription=subscription,
                    action='cancelled',
                    description=f'Suscripción al plan "{subscription.plan.name}" cancelada. Stripe: {stripe_cancelled}'
                )

            return Response(
                {
                    'detail': 'Suscripción cancelada correctamente.',
                    'stripe_cancelled': stripe_cancelled,
                    'note': 'Tendrás acceso hasta el final del período pagado' if stripe_cancelled else 'Acceso cancelado inmediatamente'
                }, 
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {'detail': f'Error al cancelar la suscripción: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        try:
            subscription = UserSubscription.objects.get(
                user=request.user,
                is_active=True,
                end_date__gte=timezone.now()
            )
            serializer = UserSubscriptionSerializer(subscription)
            return Response(serializer.data)
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
        return SubscriptionAuditLog.objects.filter(user=self.request.user)


    

class MyActiveSubscriptionView(APIView):
    permission_classes = [tenant_permission('subscriptions_api.view_usersubscription')]

    def get(self, request):
        subscription = get_user_active_subscription(request.user)
        if not subscription:
            return Response({"detail": "No tienes una suscripción activa."}, status=404)
        
        serializer = UserSubscriptionSerializer(subscription)
        return Response(serializer.data)

class MyEntitlementsView(APIView):
    permission_classes = [tenant_permission('subscriptions_api.view_usersubscription')]

    def get(self, request):
        # Para Super-Admin, devolver entitlements limitados (no exponer capacidades)
        if request.user.is_superuser or request.user.role == 'SuperAdmin':
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
                if hasattr(request.user, "tenant") and request.user.tenant is not None:
                    from apps.employees_api.models import Employee
                    employee_count = Employee.objects.filter(tenant=request.user.tenant).count()
                    
                    # Si el tenant tiene un plan, usar ese plan
                    if request.user.tenant.subscription_plan:
                        plan = request.user.tenant.subscription_plan
                        tenant = request.user.tenant
                        
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
            
            # Plan gratuito básico
            return Response({
                "plan": "free",
                "plan_display": "Plan Gratuito",
                "features": {},
                "limits": {"max_employees": 1},
                "usage": {"employees": employee_count},
                "duration_month": 0
            })

        plan = sub.plan
        # Calcula usage de empleados
        employee_count = 0
        try:
            if hasattr(request.user, "tenant") and request.user.tenant is not None:
                from apps.employees_api.models import Employee
                employee_count = Employee.objects.filter(tenant=request.user.tenant).count()
        except Exception:
            employee_count = 0
        
        usage = {
            "employees": employee_count
        }
        limits = {
            "max_employees": plan.max_employees,  # 0 = ilimitado
        }
        # Información del tenant para trial
        tenant = request.user.tenant
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
                role='ClientAdmin',
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
            
            # ✅ Requerir stripe_price_id explícito para evitar cobros a precio incorrecto
            if not plan.stripe_price_id:
                return Response({
                    'error': f'Plan {plan.name} missing stripe_price_id configuration'
                }, status=status.HTTP_400_BAD_REQUEST)
            stripe_price_id = plan.stripe_price_id
            
            # 4. Crear suscripción Stripe
            stripe_subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{'price': stripe_price_id}],
                payment_behavior='error_if_incomplete',  # ✅ Fallar si no puede cobrar
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
                is_active=True
            )

            # 6. Asignar rol ClientAdmin
            admin_role = Role.objects.get(name='Client-Admin')
            UserRole.objects.create(user=user, role=admin_role)

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
    
    @action(detail=False, methods=['post'])
    def activate_subscription(self, request):
        """Activar suscripción después de pago"""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant found'}, status=400)
        
        # Aquí validarías el pago con Stripe/PayPal
        # payment_verified = validate_payment(request.data)
        
        # Por ahora, activar directamente
        tenant.activate_subscription()
        
        return Response({
            'message': 'Subscription activated successfully',
            'status': tenant.subscription_status,
            'access_level': tenant.get_access_level()
        })

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

    def _apply_paid_access(self, tenant, user, plan, months, auto_renew=False, access_until_override=None):
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
        tenant.save(update_fields=[
            'subscription_plan',
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
            auto_renew=auto_renew
        )
        return access_until

    def _handle_auto_renew_payment(self, tenant, user, plan, payment_method_id, customer_id):
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

        stripe_price_id = plan.stripe_price_id
        if not stripe_price_id:
            return Response({
                'error': f'Plan {plan.name} missing stripe_price_id configuration'
            }, status=status.HTTP_400_BAD_REQUEST)

        stripe_subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{'price': stripe_price_id}],
            default_payment_method=payment_method_id,
            payment_behavior='default_incomplete',
            metadata={
                'user_id': str(user.id),
                'tenant_id': str(tenant.id),
                'plan_id': str(plan.id)
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
                tenant, user, plan, months=1,
                auto_renew=True,
                access_until_override=access_until_override
            )

            Subscription.objects.filter(tenant=tenant, is_active=True).update(is_active=False)
            Subscription.objects.update_or_create(
                tenant=tenant,
                plan=plan,
                defaults={
                    'stripe_subscription_id': stripe_subscription.id,
                    'is_active': True
                }
            )

            from apps.billing_api.models import Invoice
            first_invoice = stripe_subscription.get('latest_invoice') or {}
            first_payment_intent = first_invoice.get('payment_intent') or {}
            amount_paid = first_invoice.get('amount_paid') or int(plan.price * 100)
            Invoice.objects.create(
                user=user,
                amount=amount_paid / 100,
                due_date=timezone.now(),
                is_paid=True,
                paid_at=timezone.now(),
                payment_method='stripe',
                status='paid',
                stripe_payment_intent_id=first_payment_intent.get('id'),
                description=f"Auto-renew subscription - {plan.get_name_display()}"
            )

        return Response({
            'message': 'Auto-renew subscription activated successfully',
            'plan': plan.name,
            'status': tenant.subscription_status,
            'access_level': tenant.get_access_level(),
            'months': 1,
            'access_until': access_until,
            'auto_renew': True,
            'stripe_subscription_id': stripe_subscription.id
        })
    
    def get(self, request):
        """Obtener información de renovación"""
        # SuperAdmin no necesita renovar suscripción
        if request.user.is_superuser or request.user.role == 'SuperAdmin':
            return Response({
                'tenant_name': 'Sistema Administrativo',
                'current_status': 'active',
                'trial_end_date': None,
                'access_level': 'full',
                'days_in_grace': 0,
                'available_plans': [],
                'is_superadmin': True
            }, status=200)
            
        tenant = request.user.tenant
        if not tenant:
            return Response({'error': 'No tenant found'}, status=400)
        
        # Obtener planes disponibles
        plans = SubscriptionPlan.objects.filter(is_active=True)
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
        if request.user.is_superuser or request.user.role == 'SuperAdmin':
            return Response({'error': 'SuperAdmin does not need subscription renewal'}, status=400)
            
        tenant = request.user.tenant
        if not tenant:
            return Response({'error': 'No tenant found'}, status=400)
        
        plan_id = request.data.get('plan_id')
        payment_method_id = request.data.get('payment_method_id')
        payment_intent_id = request.data.get('payment_intent_id')
        months = self._parse_months(request.data.get('months'))
        auto_renew_raw = request.data.get('auto_renew', False)
        auto_renew = str(auto_renew_raw).lower() in {'1', 'true', 'yes', 'on'}
        
        if not plan_id:
            return Response({'error': 'Plan ID required'}, status=400)
        
        if not payment_method_id and not payment_intent_id:
            return Response({'error': 'Payment method or payment intent required'}, status=400)
        if months is None:
            return Response({'error': 'Months must be an integer between 1 and 24'}, status=400)
        if auto_renew and months != 1:
            return Response({'error': 'Auto-renew currently supports only 1 month per cycle'}, status=400)
        
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({'error': 'Invalid plan'}, status=400)
        
        # En desarrollo permitimos activación manual para no bloquear onboarding.
        # Producción siempre requiere Stripe.
        if settings.DEBUG and payment_method_id in {'manual', 'manual_entry', 'test'}:
            if auto_renew:
                return Response({'error': 'Auto-renew requires a real Stripe payment method'}, status=400)
            with transaction.atomic():
                access_until = self._apply_paid_access(tenant, request.user, plan, months)

                from apps.billing_api.models import Invoice
                Invoice.objects.create(
                    user=request.user,
                    amount=plan.price * months,
                    due_date=timezone.now(),
                    is_paid=True,
                    paid_at=timezone.now(),
                    payment_method='transfer',
                    status='paid',
                    description=f"Subscription renewal (manual dev) - {plan.get_name_display()} x{months}m"
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
                        access_until_override=access_until_override
                    )

                    if auto_renew and stripe_subscription_id:
                        Subscription.objects.filter(tenant=tenant, is_active=True).update(is_active=False)
                        Subscription.objects.update_or_create(
                            tenant=tenant,
                            plan=plan,
                            defaults={
                                'stripe_subscription_id': stripe_subscription_id,
                                'is_active': True
                            }
                        )

                    amount = (payment_intent.amount or int(plan.price * months * 100)) / 100
                    Invoice.objects.create(
                        user=request.user,
                        amount=amount,
                        due_date=timezone.now(),
                        is_paid=True,
                        paid_at=timezone.now(),
                        payment_method='stripe',
                        status='paid',
                        stripe_payment_intent_id=payment_intent.id,
                        description=f"Subscription renewal - {plan.get_name_display()} x{months}m"
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
                return self._handle_auto_renew_payment(tenant, request.user, plan, payment_method_id, customer.id)
            
            # Crear PaymentIntent y cobrar inmediatamente
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:4200').rstrip('/')
            return_url = request.data.get('return_url') or f"{frontend_url}/client/payment"

            payment_intent = stripe.PaymentIntent.create(
                amount=int(plan.price * months * 100),  # Centavos
                currency='usd',
                customer=customer.id,
                payment_method=payment_method_id,
                confirm=True,  # ✅ Cobrar inmediatamente
                return_url=return_url,
                metadata={
                    'user_id': str(request.user.id),
                    'tenant_id': str(tenant.id),
                    'plan_id': str(plan.id),
                    'months': str(months)
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
                access_until = self._apply_paid_access(tenant, request.user, plan, months)
                
                # Crear factura local
                from apps.billing_api.models import Invoice
                Invoice.objects.create(
                    user=request.user,
                    amount=plan.price * months,
                    due_date=timezone.now(),
                    is_paid=True,
                    paid_at=timezone.now(),
                    payment_method='stripe',
                    status='paid',
                    stripe_payment_intent_id=payment_intent.id,
                    description=f"Subscription renewal - {plan.get_name_display()} x{months}m"
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
