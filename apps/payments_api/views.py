import json
from decimal import Decimal

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse, JsonResponse
from django.conf import settings
import logging

import stripe

from apps.core.tenant_permissions import TenantPermissionByAction
from .models import Payment, PaymentProvider
from .services import StripeService, AzulService
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
        if self.request.user.is_superuser:
            return Payment.objects.all()
        tenant = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'tenant', None)
        if not tenant:
            return Payment.objects.none()
        return Payment.objects.filter(tenant=tenant)

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


# ---------------------------------------------------------------------------
# Azul — Payment processor primario para RD
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def azul_checkout(request):
    """Crear venta Azul para suscripción (checkout).

    Body: { order_number, amount, currency, customer_email, plan_id, months }
    """
    user = request.user
    tenant = getattr(request, 'tenant', None) or getattr(user, 'tenant', None)
    if not tenant:
        return Response({'error': 'Tenant no encontrado'}, status=status.HTTP_400_BAD_REQUEST)

    order_number = request.data.get('order_number', '')
    amount = request.data.get('amount')
    currency = request.data.get('currency', 'DOP')
    customer_email = request.data.get('customer_email', user.email)
    plan_id = request.data.get('plan_id', '')
    months = int(request.data.get('months', 1))

    if not amount:
        return Response({'error': 'amount es requerido'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        amount_decimal = Decimal(str(amount))
    except (ValueError, TypeError):
        return Response({'error': 'amount inválido'}, status=status.HTTP_400_BAD_REQUEST)

    if not order_number:
        order_number = f"SUB-{tenant.id}-{int(__import__('time').time() * 1000) % 100000}"

    service = AzulService()
    if not service.is_configured:
        return Response(
            {'error': 'Azul no está configurado. Ve a Configuración del Sistema para configurar Azul.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    result = service.create_checkout_sale(
        order_number=order_number,
        amount=amount_decimal,
        currency=currency,
        customer_email=customer_email,
        metadata={
            'tenant_id': str(tenant.id),
            'user_id': str(user.id),
            'plan_id': plan_id,
        },
    )

    if not result.get('success'):
        return Response(
            {'error': result.get('error', 'Error en el pago con Azul'), 'response_code': result.get('response_code')},
            status=status.HTTP_402_PAYMENT_REQUIRED,
        )

    # Crear registro de Payment
    payment = AzulService.create_payment_record(
        user=user,
        tenant=tenant,
        amount=amount_decimal,
        txn_number=result['txn_number'],
        order_number=order_number,
        plan=None,
        months=months,
    )

    return Response({
        'success': True,
        'txn_number': result['txn_number'],
        'auth_code': result['auth_code'],
        'payment_id': str(payment.id) if payment else None,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def azul_verify(request):
    """Verificar estado de una transacción Azul."""
    order_number = request.data.get('order_number', '')
    if not order_number:
        return Response({'error': 'order_number es requerido'}, status=status.HTTP_400_BAD_REQUEST)

    service = AzulService()
    if not service.is_configured:
        return Response({'error': 'Azul no configurado'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    result = service.verify_transaction(order_number)
    return Response(result)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def azul_webhook(request):
    """Webhook público para notificaciones de Azul.

    Azul envía POST con datos de la transacción cuando cambia el estado.
    """
    logger.info('Azul webhook received from=%s', request.META.get('REMOTE_ADDR', 'unknown'))

    try:
        data = json.loads(request.body) if request.body else {}
    except (json.JSONDecodeError, ValueError):
        data = {}

    response_code = data.get('responseCode', '')
    txn_number = data.get('txnNumber', '') or data.get('transactionId', '')
    order_number = data.get('orderNumber', '')

    logger.info('Azul webhook txn=%s code=%s order=%s', txn_number, response_code, order_number)

    if response_code == '00' and txn_number:
        try:
            from apps.payments_api.models import Payment
            payment = Payment.objects.filter(provider_payment_id=txn_number).first()
            if payment:
                payment.status = 'completed'
                payment.completed_at = __import__('django.utils.timezone', fromlist=['now']).now()
                payment.save(update_fields=['status', 'completed_at'])
                logger.info('Azul webhook: payment %s completed', payment.id)
            else:
                logger.info('Azul webhook: no local Payment found for txn %s', txn_number)
        except Exception as e:
            logger.exception('Azul webhook processing error: %s', e)

    return JsonResponse({'received': True})


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
