from rest_framework import viewsets, permissions, status, views
from rest_framework.decorators import action
from apps.audit_api.mixins import AuditLoggingMixin
from apps.core.permissions import IsSuperAdmin
from apps.core.tenant_permissions import TenantPermissionByAction
from .models import Invoice, PaymentAttempt
from .serializers import InvoiceSerializer, PaymentAttemptSerializer
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import UserSubscription
from apps.audit_api.utils import create_audit_log
from apps.subscriptions_api.utils import log_subscription_event
from apps.payments_api import manual as manual_payments
from apps.payments_api import emails as manual_emails
from django.db import transaction
from dateutil import parser
import logging

logger = logging.getLogger(__name__)


class InvoiceViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'billing_api.view_invoice',
        'retrieve': 'billing_api.view_invoice',
        'create': 'billing_api.add_invoice',
        'generate_for_tenant': 'billing_api.add_invoice',
        'update': 'billing_api.change_invoice',
        'partial_update': 'billing_api.change_invoice',
        'destroy': 'billing_api.delete_invoice',
        'mark_as_paid': 'billing_api.change_invoice',
        'pay': 'billing_api.change_invoice',
        'me': 'billing_api.view_invoice',
        'approve_manual_payment': 'billing_api.change_invoice',
        'reject_manual_payment': 'billing_api.change_invoice',
    }
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        queryset = Invoice.objects.select_related(
            'user', 'tenant', 'subscription', 'subscription__plan'
        )

        if self.request.user.is_superuser:
            tenant_id = self.request.query_params.get('tenant')
            if tenant_id:
                return queryset.filter(tenant_id=tenant_id)
            return queryset.all()

        tenant = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'tenant', None)
        if not tenant:
            return Invoice.objects.none()
        return queryset.filter(tenant=tenant)

    def update(self, request, *args, **kwargs):
        return Response(
            {'error': 'No se permite modificar ni eliminar facturas.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def partial_update(self, request, *args, **kwargs):
        return Response(
            {'error': 'No se permite modificar ni eliminar facturas.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {'error': 'No se permite modificar ni eliminar facturas.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    @action(detail=True, methods=['post'])
    def mark_as_paid(self, request, pk=None):
        """Deshabilitado: el estado paid solo puede venir de webhooks verificados."""
        invoice = self.get_object()
        logger.warning(
            "Blocked manual invoice mark_as_paid invoice_id=%s user_id=%s",
            invoice.id,
            request.user.id,
        )
        return Response(
            {
                'error': 'Manual invoice settlement is disabled.',
                'detail': 'Invoices are marked as paid only by verified provider webhooks.'
            },
            status=status.HTTP_403_FORBIDDEN
        )

    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError

        subscription = serializer.validated_data.get('subscription')

        if not subscription:
            raise ValidationError("La factura debe estar asociada a una suscripción válida.")

        # Validar multi-tenant: subscription debe pertenecer al usuario o su tenant
        if subscription.user != self.request.user:
            if not (hasattr(self.request.user, 'tenant') and
                    hasattr(subscription.user, 'tenant') and
                    getattr(self.request, 'tenant', self.request.user.tenant) == subscription.user.tenant):
                raise ValidationError("No tiene permiso para crear facturas para esta suscripción.")

        plan = subscription.plan

        if not plan:
            raise ValidationError("La suscripción no tiene un plan asociado.")

        calculated_amount = plan.price

        serializer.save(
            user=self.request.user,
            amount=calculated_amount,
            tenant=getattr(self.request, 'tenant', None) or getattr(self.request.user, 'tenant', None)
        )

    @action(detail=True, methods=['post'], url_path='pay')
    def pay(self, request, pk=None):
        """Deshabilitado: no se permite pagar facturas por simulación local."""
        invoice = self.get_object()
        logger.warning(
            "Blocked simulated invoice payment invoice_id=%s user_id=%s",
            invoice.id,
            request.user.id,
        )
        return Response(
            {
                'error': 'Direct invoice payment is disabled.',
                'detail': 'Use the provider checkout flow and verified billing webhooks instead.'
            },
            status=status.HTTP_403_FORBIDDEN
        )

    @action(detail=False, methods=['post'], url_path='generate-for-tenant')
    def generate_for_tenant(self, request):
        if not request.user.is_superuser:
            return Response(
                {'detail': 'Solo el superadministrador puede generar facturas manuales.'},
                status=status.HTTP_403_FORBIDDEN
            )

        tenant_id = request.data.get('tenant_id')
        due_date = request.data.get('due_date')
        description = request.data.get('description', '')

        if not tenant_id or not due_date:
            return Response(
                {'detail': 'tenant_id y due_date son requeridos.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return Response({'detail': 'Tenant no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        subscription = UserSubscription.objects.select_related('plan', 'user').filter(
            user__tenant=tenant,
            is_active=True
        ).order_by('-start_date', '-id').first()

        if not subscription or not subscription.plan:
            return Response(
                {'detail': 'El tenant no tiene una suscripción activa con plan válido.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = InvoiceSerializer(data={
            'subscription': subscription.id,
            'due_date': due_date,
            'description': description
        }, context={})
        serializer.is_valid(raise_exception=True)

        invoice = Invoice.objects.create(
            user=subscription.user,
            subscription=subscription,
            tenant=tenant,
            amount=subscription.plan.price,
            due_date=serializer.validated_data['due_date'],
            description=description or f'Factura manual de suscripción - {subscription.plan.get_name_display()}',
            status='pending'
        )

        output = self.get_serializer(invoice)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Lista las facturas del usuario autenticado (tenant-scoped)."""
        queryset = self.get_queryset().filter(user=request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def _audit_payment_decision(self, request, action, invoice, extra_data=None):
        payment = invoice.payment
        if not payment:
            return

        proof = payment.proofs.order_by('-created_at', '-id').first()
        bank_reference = proof.bank_reference if proof else None

        description = (
            f"Pago manual {'aprobado' if action == 'PAYMENT_APPROVED' else 'rechazado'} "
            f"- factura #{invoice.id} monto {invoice.amount} "
            f"comprobante {proof.id if proof else 'N/A'}"
        )

        log = create_audit_log(
            user=request.user,
            action=action,
            description=description,
            content_object=payment,
            request=request,
            source='PAYMENTS',
            extra_data={
                'tenant_id': invoice.tenant_id or (payment.tenant_id if payment else None),
                'invoice_id': str(invoice.id),
                'payment_id': str(payment.id),
                'amount': str(invoice.amount),
                'decision': action.replace('PAYMENT_', '').lower(),
                'bank_reference': bank_reference,
                **(extra_data or {}),
            },
        )
        if log:
            log.tenant_id = invoice.tenant_id or (payment.tenant_id if payment else None)
            log.save(update_fields=['tenant'])

    @action(detail=True, methods=['post'], url_path='approve-manual-payment')
    def approve_manual_payment(self, request, pk=None):
        invoice = self.get_object()
        decision_note = request.data.get('decision_note') or request.data.get('reason') or ''
        with transaction.atomic():
            locked = Invoice.objects.select_for_update().select_related(
                'payment__provider', 'subscription__plan', 'user', 'tenant'
            ).get(pk=invoice.pk)
            result = manual_payments.approve_manual_payment(locked, request.user, decision_note=decision_note)
            if not result['ok']:
                return Response({'error': result['error']}, status=result['status'])

            data = result['data']
            self._audit_payment_decision(request, 'PAYMENT_APPROVED', locked, data)

            tenant = locked.tenant or locked.payment.tenant
            access_until_str = data.get('access_until')
            access_until = None
            if access_until_str:
                from dateutil import parser
                try:
                    access_until = parser.isoparse(access_until_str)
                except Exception:
                    access_until = None

            def _send():
                proof = locked.payment.proofs.order_by('-created_at', '-id').first()
                manual_emails.send_manual_payment_approved_email(
                    locked.user, tenant, locked, proof, access_until
                )
            transaction.on_commit(_send)

        return Response(data, status=200)

    @action(detail=True, methods=['post'], url_path='reject-manual-payment')
    def reject_manual_payment(self, request, pk=None):
        invoice = self.get_object()
        reason = (request.data.get('decision_note') or request.data.get('reason') or '').strip()
        with transaction.atomic():
            locked = Invoice.objects.select_for_update().select_related(
                'payment__provider', 'subscription__plan', 'user', 'tenant'
            ).get(pk=invoice.pk)
            result = manual_payments.reject_manual_payment(locked, request.user, reason)
            if not result['ok']:
                return Response({'error': result['error']}, status=result['status'])

            data = result['data']
            self._audit_payment_decision(request, 'PAYMENT_REJECTED', locked, data)

            tenant = locked.tenant or locked.payment.tenant
            proof = locked.payment.proofs.order_by('-created_at', '-id').first()
            def _send():
                if proof:
                    manual_emails.send_manual_payment_rejected_email(
                        locked.user, tenant, locked, proof
                    )
            transaction.on_commit(_send)

        return Response(data, status=200)


class PaymentAttemptViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    serializer_class = PaymentAttemptSerializer
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'billing_api.view_paymentattempt',
        'retrieve': 'billing_api.view_paymentattempt',
        'create': 'billing_api.add_paymentattempt',
        'update': 'billing_api.change_paymentattempt',
        'partial_update': 'billing_api.change_paymentattempt',
        'destroy': 'billing_api.delete_paymentattempt',
    }

    def get_queryset(self):
        if self.request.user.is_superuser:
            return PaymentAttempt.objects.all()
        tenant = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'tenant', None)
        if not tenant:
            return PaymentAttempt.objects.none()
        return PaymentAttempt.objects.filter(invoice__tenant=tenant)

class BillingStatsView(views.APIView):
    """Estadísticas de facturación para SuperAdmin"""
    permission_classes = [IsSuperAdmin]
    
    def get(self, request):
        from django.core.cache import cache
        
        cache_key = 'billing_stats_global'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        try:
            # Período de análisis
            end_date = timezone.now()
            start_date = end_date - timedelta(days=30)
            
            # Estadísticas generales
            total_revenue = Invoice.objects.filter(is_paid=True).aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            pending_payments = Invoice.objects.filter(is_paid=False).aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            overdue_invoices = Invoice.objects.filter(
                is_paid=False,
                due_date__lt=timezone.now()
            ).count()
            
            # Estadísticas del período
            period_invoices = Invoice.objects.filter(
                issued_at__gte=start_date,
                issued_at__lte=end_date
            )
            
            period_revenue = period_invoices.filter(is_paid=True).aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            # Facturas por estado
            invoice_stats = {
                'total': Invoice.objects.count(),
                'paid': Invoice.objects.filter(is_paid=True).count(),
                'pending': Invoice.objects.filter(is_paid=False, due_date__gte=timezone.now()).count(),
                'overdue': overdue_invoices
            }

            active_subscriptions = UserSubscription.objects.filter(
                is_active=True,
                user__tenant__is_active=True
            ).count()
            
            # Top tenants por revenue usando agregación única
            top_tenants_data = Invoice.objects.filter(
                is_paid=True,
                user__tenant__is_active=True
            ).values(
                'user__tenant__id',
                'user__tenant__name'
            ).annotate(
                revenue=Sum('amount'),
                invoice_count=Count('id')
            ).order_by('-revenue')[:5]
            
            top_tenants = [
                {
                    'tenant_name': item['user__tenant__name'],
                    'revenue': float(item['revenue']),
                    'invoice_count': item['invoice_count']
                }
                for item in top_tenants_data
            ]
            
            # Revenue por mes (últimos 6 meses)
            monthly_revenue = []
            for i in range(6):
                month_start = (timezone.now() - timedelta(days=30*i)).replace(day=1)
                month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                
                month_total = Invoice.objects.filter(
                    issued_at__gte=month_start,
                    issued_at__lte=month_end,
                    is_paid=True
                ).aggregate(total=Sum('amount'))['total'] or 0
                
                monthly_revenue.insert(0, {
                    'month': month_start.strftime('%b %Y'),
                    'revenue': float(month_total)
                })
            
            data = {
                'total_revenue': float(total_revenue),
                'pending_payments': float(pending_payments),
                'overdue_invoices': overdue_invoices,
                'active_subscriptions': active_subscriptions,
                'period_revenue': float(period_revenue),
                'invoice_stats': invoice_stats,
                'top_tenants': top_tenants,
                'monthly_revenue': monthly_revenue,
                'average_invoice_amount': float(total_revenue / invoice_stats['total']) if invoice_stats['total'] > 0 else 0
            }
            
            cache.set(cache_key, data, 120)
            
            return Response(data)
            
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Error al obtener estadísticas de facturación'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
