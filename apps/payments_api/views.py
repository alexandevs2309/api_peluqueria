import json
import hmac
from decimal import Decimal, InvalidOperation

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse, JsonResponse, FileResponse, Http404
from django.conf import settings
from django.db import transaction, IntegrityError
from django.utils import timezone
import mimetypes
import logging

import stripe

from apps.core.tenant_permissions import TenantPermissionByAction
from .models import Payment, PaymentProvider, PaymentProof, AzulTransaction
from .services import StripeService, AzulService
from .azul_provider import AzulProvider
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
def azul_card_checkout(request):
    """Cobro con tarjeta usando Azul Data Vault (CR-11).

    El PAN/CVV se envían sólo al tokenizador del proveedor, nunca se persisten
    ni se registran. El cobro se realiza con el token y el `Payment` queda en
    `pending` hasta que Azul confirma; los rechazos, cancelaciones y expiraciones
    se reflejan en el estado. La clave de idempotencia evita doble cargo.
    """
    user = request.user
    tenant = getattr(request, 'tenant', None) or getattr(user, 'tenant', None)
    if not tenant:
        return Response({'error': 'Tenant no encontrado'}, status=status.HTTP_400_BAD_REQUEST)

    data = request.data
    order_number = str(data.get('order_number') or '').strip()
    currency = str(data.get('currency') or 'DOP').upper()
    card_number = ''.join(ch for ch in str(data.get('card_number') or '') if ch.isdigit())
    card_expiry = str(data.get('card_expiry') or '').strip()
    card_cvv = ''.join(ch for ch in str(data.get('card_cvv') or '') if ch.isdigit())
    card_holder = str(data.get('card_holder') or '').strip()
    idempotency_key = (
        request.META.get('HTTP_IDEMPOTENCY_KEY') or data.get('idempotency_key') or ''
    ).strip()[:128] or None

    if not idempotency_key:
        return Response({'error': 'idempotency_key es requerida'}, status=status.HTTP_400_BAD_REQUEST)
    if not order_number:
        order_number = f'CARD-{tenant.id}-{user.id}-{int(__import__("time").time() * 1000)}'

    try:
        amount = Decimal(str(data.get('amount'))).quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError, ValueError):
        return Response({'error': 'amount inválido'}, status=status.HTTP_400_BAD_REQUEST)
    if amount <= 0:
        return Response({'error': 'amount debe ser mayor a 0'}, status=status.HTTP_400_BAD_REQUEST)
    if currency not in {'DOP', 'USD', 'EUR'}:
        return Response({'error': 'currency no soportada'}, status=status.HTTP_400_BAD_REQUEST)
    if not (13 <= len(card_number) <= 19) or not (3 <= len(card_cvv) <= 4) or not card_holder:
        return Response({'error': 'Datos de tarjeta inválidos'}, status=status.HTTP_400_BAD_REQUEST)

    # Expiry MM/YY, no vencida (zona horaria RD).
    try:
        exp_month, exp_year = (int(p) for p in card_expiry.split('/'))
        if not (1 <= exp_month <= 12):
            raise ValueError
        exp_year += 2000 if exp_year < 100 else 0
    except (ValueError, TypeError):
        return Response({'error': 'Vencimiento inválido'}, status=status.HTTP_400_BAD_REQUEST)
    from django.utils import timezone as dj_timezone
    now = dj_timezone.now()
    if exp_year < now.year or (exp_year == now.year and exp_month < now.month):
        return Response({'error': 'La tarjeta está vencida'}, status=status.HTTP_402_PAYMENT_REQUIRED)

    provider = AzulProvider(tenant=tenant)
    if not provider.is_configured:
        return Response(
            {'error': 'Azul no está configurado'}, status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    with transaction.atomic():
        try:
            with transaction.atomic():
                attempt = AzulTransaction.objects.create(
                    tenant=tenant, user=user, source='card', order_number=order_number,
                    idempotency_key=idempotency_key, amount=amount, currency=currency,
                    status='pending', response_code='',
                )
        except IntegrityError:
            existing = AzulTransaction.objects.get(
                tenant=tenant, idempotency_key=idempotency_key
            )
            return Response({
                'success': existing.status == 'completed',
                'status': existing.status,
                'order_number': existing.order_number,
                'payment_id': str(existing.payment_id) if existing.payment_id else None,
                'idempotent': True,
            })

        provider_obj, _ = PaymentProvider.objects.get_or_create(name='azul')
        payment = Payment.objects.create(
            tenant=tenant, user=user, provider=provider_obj, amount=amount,
            currency=currency, status='pending',
            metadata={
                'azul_order_number': order_number,
                'source': 'azul_card',
                'plan_id': str(data.get('plan_id') or ''),
                'months': data.get('months') or 1,
            },
        )
        attempt.payment = payment
        attempt.save(update_fields=['payment'])

    metadata = {'tenant_id': str(tenant.id), 'user_id': str(user.id),
                'plan_id': str(data.get('plan_id') or '')}

    vault = provider.create_vault_token(
        card_number=card_number,
        card_expiry=card_expiry,
        customer_email=str(data.get('customer_email') or user.email),
        metadata=metadata,
    )
    if not vault.get('success'):
        attempt.status = 'failed'
        attempt.last_error = 'tokenization_failed'
        attempt.save(update_fields=['status', 'last_error', 'updated_at'])
        Payment.objects.filter(pk=payment.pk, status='pending').update(status='failed')
        return Response(
            {'success': False, 'status': 'failed', 'error': vault.get('error_message')},
            status=status.HTTP_402_PAYMENT_REQUIRED,
        )

    charge = provider.charge_with_vault(
        token_id=vault['token_id'], amount=amount, currency=currency,
        order_number=order_number, metadata=metadata,
    )

    if charge.success and charge.status == 'completed':
        payment_status, event_status, http_status = 'completed', 'completed', status.HTTP_200_OK
    elif charge.status in ('failed', 'declined'):
        payment_status, event_status, http_status = 'failed', 'failed', status.HTTP_402_PAYMENT_REQUIRED
    elif charge.status in ('cancelled', 'expired'):
        # CR-11: conservar el estado terminal exacto. Antes 'expired' se
        # aplanaba a 'cancelled' en Payment y en la respuesta al frontend.
        payment_status, event_status, http_status = charge.status, charge.status, status.HTTP_402_PAYMENT_REQUIRED
    else:
        payment_status, event_status, http_status = 'pending', 'pending', status.HTTP_202_ACCEPTED

    Payment.objects.filter(pk=payment.pk, status='pending').update(
        status=payment_status,
        completed_at=dj_timezone.now() if payment_status == 'completed' else None,
    )
    attempt.status = event_status
    attempt.txn_number = charge.transaction_id or ''
    attempt.response_code = str((charge.raw_response or {}).get('responseCode', '') or '')
    attempt.save(update_fields=['status', 'txn_number', 'response_code', 'updated_at'])
    payment.refresh_from_db()

    return Response({
        'success': payment_status == 'completed',
        'status': payment_status,
        'order_number': order_number,
        'payment_id': str(payment.id),
        'txn_number': charge.transaction_id or '',
        'amount': str(payment.amount),
        'currency': payment.currency,
    }, status=http_status)


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


from apps.settings_api.integration_service import IntegrationService


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_availability(request):
    """Indica que metodos de pago estan realmente operativos.

    El frontend lo usa para NO ofrecer formularios que no pueden cobrar
    (por ejemplo, tarjeta cuando Azul todavia no esta configurado).
    """
    try:
        card_configured = bool(AzulService().is_configured)
    except Exception:
        card_configured = False

    try:
        paypal_enabled = bool(IntegrationService.is_paypal_enabled())
    except Exception:
        paypal_enabled = False

    return Response({
        'card': card_configured,
        'card_provider': 'azul',
        'paypal': paypal_enabled,
        'transfer': True,
    })

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def azul_webhook(request):
    """Webhook público de Azul (CR-10).

    Seguridad en capas, sin inventar un HMAC propio:
      1. AUTH1/AUTH2 del protocolo Azul comparados en tiempo constante.
      2. La orden, el importe y el tenant se validan contra el Payment LOCAL.
      3. Confirmación server-to-server con `/verify` de Azul.
      4. Evento persistido con `txn_number` único por tenant (anti-replay).
    """
    logger.info('Azul webhook received from=%s', request.META.get('REMOTE_ADDR', 'unknown'))

    auth1 = request.META.get('HTTP_AUTH1', '')
    auth2 = request.META.get('HTTP_AUTH2', '')
    system = IntegrationService.get_system_settings()
    expected_auth1 = system.azul_auth1 or ''
    expected_auth2 = system.azul_auth2 or ''
    # Fail-closed: sin credenciales configuradas no se evalúan cabeceras vacías
    # como válidas. El webhook permanece deshabilitado hasta que se configuren.
    if (
        not expected_auth1
        or not expected_auth2
        or not hmac.compare_digest(auth1, expected_auth1)
        or not hmac.compare_digest(auth2, expected_auth2)
    ):
        logger.warning('Azul webhook: credenciales inválidas o no configuradas desde %s',
                       request.META.get('REMOTE_ADDR', 'unknown'))
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        data = json.loads(request.body) if request.body else {}
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    response_code = str(data.get('responseCode', ''))
    txn_number = str(data.get('txnNumber', '') or data.get('transactionId', ''))
    order_number = str(data.get('orderNumber', ''))
    if not txn_number or not order_number:
        return JsonResponse({'error': 'txnNumber y orderNumber requeridos'}, status=400)

    logger.info('Azul webhook txn=%s code=%s order=%s', txn_number, response_code, order_number)

    # El Payment local es la autoridad de orden, importe y tenant.
    payment = Payment.objects.filter(
        metadata__azul_order_number=order_number
    ).select_related('tenant').first()
    if payment is None:
        by_txn = Payment.objects.filter(provider_payment_id=txn_number).select_related('tenant').first()
        if by_txn and str(by_txn.metadata.get('azul_order_number', '')) == order_number:
            payment = by_txn
    if payment is None or payment.tenant_id is None:
        logger.warning('Azul webhook: orden/txn desconocidos order=%s txn=%s', order_number, txn_number)
        return JsonResponse({'received': False, 'error': 'unknown_order'}, status=404)

    # Importe: Azul reporta centavos; se tolera también formato de unidades.
    raw_amount = data.get('amount')
    if raw_amount not in (None, ''):
        try:
            reported = Decimal(str(raw_amount))
        except (InvalidOperation, TypeError, ValueError):
            return JsonResponse({'received': False, 'error': 'invalid_amount'}, status=400)
        if reported not in (payment.amount, payment.amount * 100):
            logger.warning('Azul webhook: importe discrepante payment=%s reported=%s', payment.id, reported)
            return JsonResponse({'received': False, 'error': 'amount_mismatch'}, status=400)

    # Confirmación real con el proveedor (mecanismo existente en el proyecto).
    verification = AzulService().verify_transaction(order_number)
    verified_txn = str(verification.get('txn_number', ''))
    if not verification.get('success') or (verified_txn and verified_txn != txn_number):
        logger.warning('Azul webhook: verificación fallida order=%s code=%s',
                       order_number, verification.get('response_code'))
        return JsonResponse({'received': False, 'error': 'verification_failed'}, status=400)

    if response_code == '00':
        new_status, event_status = 'completed', 'completed'
    elif response_code in {'04', '05', '14', '41', '43', '51', '54', '57', '61', '62'}:
        new_status, event_status = 'failed', 'failed'
    elif response_code in {'99', 'TF'}:
        new_status, event_status = 'cancelled', 'expired'
    else:
        new_status, event_status = 'pending', 'pending'

    with transaction.atomic():
        try:
            with transaction.atomic():
                AzulTransaction.objects.create(
                    tenant=payment.tenant,
                    user=payment.user,
                    payment=payment,
                    source='webhook',
                    order_number=order_number,
                    txn_number=txn_number,
                    amount=payment.amount,
                    currency=payment.currency,
                    status=event_status,
                    response_code=response_code,
                )
        except IntegrityError:
            logger.info('Azul webhook duplicado (replay) txn=%s', txn_number)
            return JsonResponse({'received': True, 'duplicate': True})

        if new_status in ('completed', 'failed', 'cancelled'):
            Payment.objects.filter(pk=payment.pk, status__in=['pending', 'processing']).update(
                status=new_status,
                completed_at=timezone.now() if new_status == 'completed' else None,
            )

    return JsonResponse({'received': True, 'status': new_status})


# ---------------------------------------------------------------------------
# Pagos manuales (transferencia bancaria)
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def manual_upload(request):
    """Sube un comprobante de pago manual para una Invoice pendiente del
    propio tenant del usuario autenticado.

    Body (multipart): invoice_id, bank_reference, amount_provided, file.
    Nunca se confía en tenant_id/amount/user_id provenientes del cliente:
    la Invoice es la única autoridad.
    """
    from apps.billing_api.models import Invoice
    from .manual import upload_manual_proof
    from . import emails as manual_emails
    from apps.core.tenant_permissions import resolve_request_tenant

    user = request.user
    tenant = resolve_request_tenant(request)
    if not tenant:
        return Response({'error': 'No se pudo determinar el tenant.'}, status=400)

    invoice_id = request.data.get('invoice_id')
    if not invoice_id:
        return Response({'error': 'invoice_id es requerido.'}, status=400)

    invoice = Invoice.objects.select_related(
        'payment__provider', 'subscription__plan', 'tenant'
    ).filter(id=invoice_id, tenant=tenant).first()
    if not invoice:
        return Response({'error': 'Factura no encontrada.'}, status=404)

    try:
        with transaction.atomic():
            result = upload_manual_proof(
                invoice,
                request.FILES.get('file'),
                request.data.get('bank_reference'),
                request.data.get('amount_provided'),
            )
            if not result['ok']:
                return Response({'error': result['error']}, status=result['status'])

            proof_id = result['data']['proof_id']
            proof = PaymentProof.objects.get(id=proof_id)

            def _notify():
                manual_emails.send_manual_payment_pending_email(
                    invoice.user, tenant, invoice, proof
                )
                # Avisar al administrador de la plataforma para que revise
                # y apruebe/rechace el pago. Sin esto el admin no se enteraba.
                manual_emails.send_admin_payment_pending_email(
                    invoice.user, tenant, invoice, proof
                )
            transaction.on_commit(_notify)

        result['data']['status'] = 'pending'
        return Response(result['data'], status=201)
    except Exception as exc:  # noqa: BLE001
        logger.error('manual_upload error for user=%s: %s', user.id, exc, exc_info=True)
        return Response({'error': 'Error al procesar el comprobante.'}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manual_proof_download(request, proof_id):
    """Descarga protegida de un comprobante.

    Solo el dueño del pago, un administrador del tenant con permisos de
    billing, o un superusuario pueden acceder. El archivo se fuerza como
    attachment (jamás se sirve inline).
    """
    from apps.roles_api.models import UserRole
    from apps.core.tenant_permissions import resolve_request_tenant

    user = request.user
    proof = PaymentProof.objects.select_related(
        'payment__tenant', 'payment__user'
    ).filter(id=proof_id).first()
    if not proof or not proof.file:
        raise Http404

    tenant = resolve_request_tenant(request)

    is_allowed = False
    if user.is_superuser:
        is_allowed = True
    else:
        same_tenant = tenant is not None and (
            proof.payment.tenant_id == tenant.id
        )
        is_owner = proof.payment.user_id == user.id
        is_admin = UserRole.objects.filter(
            user=user,
            tenant_id=proof.payment.tenant_id,
            role__permissions__content_type__app_label='billing_api',
            role__permissions__codename='view_invoice',
        ).exists()
        is_allowed = same_tenant and (is_owner or is_admin)

    if not is_allowed:
        return Response(
            {'error': 'No tienes acceso a este comprobante.'},
            status=403,
        )

    ctype = mimetypes.guess_type(proof.file_name or proof.file.name)[0] \
        or 'application/octet-stream'
    response = FileResponse(proof.file.open('rb'), content_type=ctype)
    response['Content-Disposition'] = f'attachment; filename="{proof.file_name or "comprobante"}"'
    return response


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
