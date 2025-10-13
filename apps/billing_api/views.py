from rest_framework import viewsets, permissions, status, views
from rest_framework.decorators import action
from apps.audit_api.mixins import AuditLoggingMixin
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

    def get_queryset(self):
        # SuperAdmin ve todas las facturas con relaciones optimizadas
        if hasattr(self.request.user, 'roles') and self.request.user.roles.filter(name='Super-Admin').exists():
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
    
    @action(detail=True, methods=['post'])
    def mark_as_paid(self, request, pk=None):
        """Marcar factura como pagada (SuperAdmin o propietario)"""
        invoice = self.get_object()
        
        if invoice.is_paid:
            return Response({
                'message': 'Esta factura ya está pagada'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            invoice.is_paid = True
            invoice.paid_at = timezone.now()
            invoice.status = 'paid'
            invoice.save()
            
            return Response({
                'message': 'Factura marcada como pagada correctamente',
                'invoice_id': invoice.id,
                'paid_at': invoice.paid_at.isoformat()
            })
        except Exception as e:
            return Response({
                'error': f'Error al marcar como pagada: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def perform_create(self, serializer):
        from apps.subscriptions_api.models import UserSubscription
        active_sub = UserSubscription.objects.filter(user=self.request.user, is_active=True).first()
        serializer.save(user=self.request.user, subscription=active_sub)
    
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

class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.roles.filter(name='Super-Admin').exists()
        )

class BillingStatsView(views.APIView):
    """Estadísticas de facturación para SuperAdmin"""
    permission_classes = [IsSuperAdmin]
    
    def get(self, request):
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
            
            # Top tenants por revenue
            top_tenants = []
            for tenant in Tenant.objects.filter(is_active=True):
                tenant_revenue = Invoice.objects.filter(
                    user__tenant=tenant,
                    is_paid=True
                ).aggregate(total=Sum('amount'))['total'] or 0
                
                if tenant_revenue > 0:
                    top_tenants.append({
                        'tenant_name': tenant.name,
                        'revenue': float(tenant_revenue),
                        'invoice_count': Invoice.objects.filter(user__tenant=tenant).count()
                    })
            
            top_tenants.sort(key=lambda x: x['revenue'], reverse=True)
            
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
            
            return Response({
                'total_revenue': float(total_revenue),
                'pending_payments': float(pending_payments),
                'overdue_invoices': overdue_invoices,
                'period_revenue': float(period_revenue),
                'invoice_stats': invoice_stats,
                'top_tenants': top_tenants[:5],
                'monthly_revenue': monthly_revenue,
                'average_invoice_amount': float(total_revenue / invoice_stats['total']) if invoice_stats['total'] > 0 else 0
            })
            
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
