from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from .models import SubscriptionAuditLog, UserSubscription, SubscriptionPlan, Subscription
from .serializers import  SubscriptionAuditLogSerializer, SubscriptionPlanSerializer , UserSubscriptionSerializer, OnboardingSerializer
from .permissions import IsSuperuserOrReadOnly
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.utils import timezone
from rest_framework.views import APIView
from .utils import get_user_active_subscription, log_subscription_event
from django.db import transaction
from django.conf import settings
from stripe.error import StripeError
import stripe
from apps.tenants_api.models import Tenant
from apps.auth_api.models import User
from apps.roles_api.models import Role, UserRole

stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)


class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active']
    search_fields = ['name', ]
    ordering_fields = ['price', 'duration_days']
    
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


    

class UserSubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = UserSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return UserSubscription.objects.all()
        return UserSubscription.objects.filter(user=self.request.user)
    
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
            log_subscription_event(user=updated.user, subscription=updated, action='plan_changed')


    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_subscription(self, request, pk=None):
        try:
            subscription = self.get_object()

            if not subscription.is_active:
                return Response(
                    {'detail': 'La suscripción ya está inactiva.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Verificar que la suscripción pertenezca al usuario (para usuarios no superusuarios)
            if not request.user.is_superuser and subscription.user != request.user:
                return Response(
                    {'detail': 'No tienes permiso para cancelar esta suscripción.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            subscription.is_active = False
            subscription.save()

            log_subscription_event(
                user=request.user,
                subscription=subscription,
                action='cancelled',
                description=f'Suscripción al plan "{subscription.plan.name}" cancelada anticipadamente.'
            )

            return Response(
                {'detail': 'Suscripción cancelada correctamente.'}, 
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
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SubscriptionAuditLog.objects.filter(user=self.request.user)


    

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
        # Para Super-Admin, devolver entitlements ilimitados
        if request.user.roles.filter(name='Super-Admin').exists():
            return Response({
                "plan": "Super-Admin",
                "plan_display": "Administrador del Sistema",
                "features": {"unlimited": True},
                "limits": {"max_employees": 0},  # 0 = ilimitado
                "usage": {"employees": 0},
                "duration_month": 0
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
                        return Response({
                            "plan": plan.name,
                            "plan_display": getattr(plan, 'get_name_display', lambda: plan.name)(),
                            "features": plan.features or {},
                            "limits": {"max_employees": plan.max_employees},
                            "usage": {"employees": employee_count},
                            "duration_month": getattr(plan, 'duration_month', 1)
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
        data = {
            "plan": plan.name,
            "plan_display": getattr(plan, 'get_name_display', lambda: plan.name)(),
            "features": plan.features or {},
            "limits": limits,
            "usage": usage,
            "duration_month": getattr(plan, 'duration_month', 1),
        }
        return Response(data)

class OnboardingView(APIView):
    permission_classes = []

    @transaction.atomic
    def post(self, request):
        serializer = OnboardingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
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
                is_active=True
            )
            user.set_password(data['password'])
            user.save()

            # Asignar owner tenant
            tenant.owner = user
            tenant.save()

            # 3. Crear suscripción Stripe
            plan = SubscriptionPlan.objects.get(id=data['plan_id'])
            stripe_subscription = stripe.Subscription.create(
                customer=data['stripe_customer_id'],
                items=[{'price': plan.name}],  # Asumir plan.name es price id
                expand=['latest_invoice.payment_intent']
            )

            # 4. Crear Subscription local
            subscription = Subscription.objects.create(
                tenant=tenant,
                plan=plan,
                stripe_subscription_id=stripe_subscription.id,
                is_active=True
            )

            # 5. Asignar rol ClientAdmin
            admin_role = Role.objects.get(name='Client-Admin')
            UserRole.objects.create(user=user, role=admin_role)

            return Response({'detail': 'Onboarding completado exitosamente.'}, status=status.HTTP_201_CREATED)

        except StripeError as e:
            transaction.set_rollback(True)
            return Response({'error': 'Error en Stripe: ' + str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            transaction.set_rollback(True)
            return Response({'error': 'Error interno: ' + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
