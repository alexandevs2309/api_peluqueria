from rest_framework import viewsets, permissions, status, views
from rest_framework.decorators import action
from apps.audit_api.mixins import AuditLoggingMixin
from apps.auth_api.permissions import IsSuperAdmin
from .models import Invoice, PaymentAttempt
from .serializers import InvoiceSerializer, PaymentAttemptSerializer
from .permissions import IsOwnerOrAdmin
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from apps.tenants_api.models import Tenant


class InvoiceViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated , IsOwnerOrAdmin]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        # ✅ ESTANDARIZADO: Usar is_superuser
        if hasattr(self.request.user, 'roles') and self.request.user.is_superuser:
            return Invoice.objects.select_related(
                'user', 'user__tenant', 'subscription', 'subscription__plan'
            ).all()
        elif self.request.user.is_superuser:
            return Invoice.objects.select_related(
                'user', 'user__tenant', 'subscription', 'subscription__plan'
            ).all()
        return Invoice.objects.select_related(
            'user', 'user__tenant', 'subscription', 'subscription__plan'
        ).filter(user=self.request.user)
    
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
        invoice = self.get_object()

        if invoice.is_paid:
            return Response(
                {'detail': 'Esta factura ya fue pagada.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Simulación del intento de pago
            PaymentAttempt.objects.create(
                invoice=invoice, 
                success=True, 
                message="Pago simulado exitoso."
            )

            invoice.is_paid = True
            invoice.paid_at = timezone.now()
            invoice.status = 'paid'
            invoice.save()
            
            return Response({
                'detail': 'Pago exitoso.',
                'invoice_id': invoice.id,
                'amount': str(invoice.amount)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'detail': f'Error al procesar el pago: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentAttemptViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    serializer_class = PaymentAttemptSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

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
    
    @action(detail=False, methods=['post'])
    def mark_invoice_paid(self, request):
        """Marcar factura como pagada (SuperAdmin)"""
        invoice_id = request.data.get('invoice_id')
        
        try:
            invoice = Invoice.objects.get(id=invoice_id)
            
            if invoice.is_paid:
                return Response({
                    'message': 'La factura ya está marcada como pagada'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            invoice.is_paid = True
            invoice.paid_at = timezone.now()
            invoice.status = 'paid'
            invoice.save()
            
            return Response({
                'message': f'Factura #{invoice.id} marcada como pagada'
            })
            
        except Invoice.DoesNotExist:
            return Response({
                'error': 'Factura no encontrada'
            }, status=status.HTTP_404_NOT_FOUND)
