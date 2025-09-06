from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from .models import SubscriptionAuditLog, UserSubscription, SubscriptionPlan
from .serializers import  SubscriptionAuditLogSerializer, SubscriptionPlanSerializer , UserSubscriptionSerializer
from .permissions import IsSuperuserOrReadOnly
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.utils import timezone
from rest_framework.views import APIView
from .utils import get_user_active_subscription, log_subscription_event


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
        sub = get_user_active_subscription(request.user)
        if not sub:
            return Response({"detail":"Sin suscripción activa"}, status=404)

        plan = sub.plan
        # Calcula "usage" de lo que te interese (ejemplo: empleados)
        employee_count = 0
        if hasattr(request.user, "tenant") and request.user.tenant is not None:
            employee_count = request.user.tenant.employees.count()
        
        usage = {
            "employees": employee_count
        }
        limits = {
            "max_employees": plan.max_employees,  # 0 = ilimitado
        }
        data = {
            "plan": plan.name,
            "plan_display": plan.get_name_display(),
            "features": plan.features or {},
            "limits": limits,
            "usage": usage,
            "duration_month": plan.duration_month,
        }
        return Response(data)