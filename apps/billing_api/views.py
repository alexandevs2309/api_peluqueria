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
    }
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        queryset = Invoice.objects.select_related(
            'user', 'user__tenant', 'subscription', 'subscription__plan'
        )

        # ✅ ESTANDARIZADO: Usar is_superuser
        if hasattr(self.request.user, 'roles') and self.request.user.is_superuser:
            tenant_id = self.request.query_params.get('tenant')
            if tenant_id:
                return queryset.filter(user__tenant_id=tenant_id)
            return queryset.all()
        elif self.request.user.is_superuser:
            tenant_id = self.request.query_params.get('tenant')
            if tenant_id:
                return queryset.filter(user__tenant_id=tenant_id)
            return queryset.all()

        return queryset.filter(user=self.request.user)
    
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
        """Marcar factura como pagada (SuperAdmin o propietario)"""
        from django.db import transaction
        from django.contrib.contenttypes.models import ContentType
        from apps.audit_api.models import AuditLog
        
        with transaction.atomic():
            # 🔒 Bloqueo real de fila
            invoice = Invoice.objects.select_for_update().get(pk=pk)

            # Validación de ownership dentro del lock
            if not request.user.is_superuser:
                if invoice.user != request.user:
                    if not (hasattr(request.user, 'tenant') and invoice.user and invoice.user.tenant_id == request.user.tenant_id):
                        return Response(
                            {'error': 'No tienes permiso para modificar esta factura.'},
                            status=status.HTTP_403_FORBIDDEN
                        )
            
            # Validar doble pago dentro del lock
            if invoice.is_paid:
                return Response(
                    {'error': 'La factura ya está pagada.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar período cerrado
            if invoice.issued_at < timezone.now() - timedelta(days=90):
                return Response(
                    {'error': 'No se puede modificar una factura de período cerrado.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Aplicar cambios controlados
            invoice.is_paid = True
            invoice.paid_at = timezone.now()
            invoice.status = 'paid'
            
            invoice.save(update_fields=['is_paid', 'paid_at', 'status'])
            
            # Mantener auditoría obligatoria
            AuditLog.objects.create(
                user=request.user,
                action='MARK_PAID',
                description=f'Marcó factura #{invoice.id} como pagada',
                content_type=ContentType.objects.get_for_model(invoice),
                object_id=invoice.id,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                source='SYSTEM',
                extra_data={'amount': str(invoice.amount)}
            )
        
        return Response({'message': 'Factura marcada como pagada correctamente.'})
    
    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError
        
        subscription = serializer.validated_data.get('subscription')
        
        if not subscription:
            raise ValidationError("La factura debe estar asociada a una suscripción válida.")
        
        # Validar multi-tenant: subscription debe pertenecer al usuario o su tenant
        if subscription.user != self.request.user:
            if not (hasattr(self.request.user, 'tenant') and 
                    hasattr(subscription.user, 'tenant') and 
                    self.request.user.tenant == subscription.user.tenant):
                raise ValidationError("No tiene permiso para crear facturas para esta suscripción.")
        
        plan = subscription.plan
        
        if not plan:
            raise ValidationError("La suscripción no tiene un plan asociado.")
        
        calculated_amount = plan.price
        
        serializer.save(
            user=self.request.user,
            amount=calculated_amount
        )
    
    @action(detail=True, methods=['post'], url_path='pay')
    def pay(self, request, pk=None):
        from django.db import transaction
        
        try:
            with transaction.atomic():
                # 🔒 Lock de fila para prevenir race condition
                invoice = Invoice.objects.select_for_update().get(pk=pk)

                # Validar dentro del lock
                if not request.user.is_superuser:
                    if invoice.user != request.user:
                        if not (hasattr(request.user, 'tenant') and invoice.user and invoice.user.tenant_id == request.user.tenant_id):
                            return Response(
                                {'detail': 'No tienes permiso para modificar esta factura.'},
                                status=status.HTTP_403_FORBIDDEN
                            )

                if invoice.is_paid:
                    return Response(
                        {'detail': 'Esta factura ya fue pagada.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Simulación del intento de pago
                PaymentAttempt.objects.create(
                    invoice=invoice, 
                    success=True,
                    status='success',
                    message="Pago simulado exitoso."
                )

                invoice.is_paid = True
                invoice.paid_at = timezone.now()
                invoice.status = 'paid'
                invoice.save(update_fields=['is_paid', 'paid_at', 'status'])
            
            return Response({
                'detail': 'Pago exitoso.',
                'invoice_id': invoice.id,
                'amount': str(invoice.amount)
            }, status=status.HTTP_200_OK)
            
        except Invoice.DoesNotExist:
            return Response(
                {'detail': 'Factura no encontrada.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error al procesar el pago: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
            amount=subscription.plan.price,
            due_date=serializer.validated_data['due_date'],
            description=description or f'Factura manual de suscripción - {subscription.plan.get_name_display()}',
            status='pending'
        )

        output = self.get_serializer(invoice)
        return Response(output.data, status=status.HTTP_201_CREATED)


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
        return PaymentAttempt.objects.filter(invoice__user=self.request.user)

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
