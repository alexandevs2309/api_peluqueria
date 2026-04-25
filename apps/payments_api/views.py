from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse
from django.conf import settings
import logging

import stripe

from apps.core.tenant_permissions import TenantPermissionByAction
from .models import Payment
from .services import StripeService
from .serializers import PaymentSerializer

logger = logging.getLogger(__name__)

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'payments_api.view_payment',
        'retrieve': 'payments_api.view_payment',
        'create': 'payments_api.add_payment',
        'update': 'payments_api.change_payment',
        'partial_update': 'payments_api.change_payment',
        'destroy': 'payments_api.delete_payment',
        'create_subscription_payment': 'payments_api.add_payment',
        'confirm_payment': 'payments_api.change_payment',
    }
    
    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        return Response(
            {
                'error': 'Direct payment creation is disabled.',
                'detail': 'Use create_subscription_payment instead.'
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def update(self, request, *args, **kwargs):
        return Response(
            {'error': 'Direct payment mutation is disabled.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def partial_update(self, request, *args, **kwargs):
        return Response(
            {'error': 'Direct payment mutation is disabled.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {'error': 'Direct payment deletion is disabled.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    @action(detail=False, methods=['post'])
    def create_subscription_payment(self, request):
        """Crear pago para suscripción"""
        try:
            plan_id = request.data.get('plan_id')
            if not plan_id:
                return Response({'error': 'plan_id is required'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            stripe_service = StripeService()
            payment_data = stripe_service.create_subscription_payment(
                request.user, plan_id
            )
            
            return Response(payment_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({'error': str(e)}, 
                          status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def confirm_payment(self, request, pk=None):
        """
        Endpoint legacy deshabilitado.
        La confirmación de pagos debe ocurrir únicamente vía webhook verificado.
        """
        payment = self.get_object()
        logger.warning(
            "Blocked legacy confirm_payment mutation payment_id=%s user_id=%s",
            payment.id,
            request.user.id,
        )
        return Response(
            {
                'error': 'Manual payment confirmation is disabled.',
                'detail': 'Payments are confirmed only by verified provider webhooks.'
            },
            status=status.HTTP_403_FORBIDDEN
        )

from django.views import View

class StripeWebhookView(View):
    """Compatibilidad legacy: delega al webhook idempotente de billing."""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request):
        logger.warning(
            "Legacy Stripe webhook path invoked; delegating to billing webhook path=%s",
            request.path,
        )
        from apps.billing_api.webhooks_idempotent import stripe_webhook
        return stripe_webhook(request)
