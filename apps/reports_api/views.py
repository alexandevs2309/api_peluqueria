from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import views, status
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from apps.tenants_api.models import Tenant
from apps.billing_api.models import Invoice
from apps.auth_api.models import User
from rest_framework import views, status
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from apps.tenants_api.models import Tenant
from apps.billing_api.models import Invoice
from apps.auth_api.models import User

class IsSuperAdmin:
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.roles.filter(name='Super-Admin').exists()
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def employee_report(request):
    """Reporte básico de empleados"""
    return Response({
        'total_employees': 0,
        'active_employees': 0,
        'employees_by_specialty': [],
        'top_performers': []
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sales_report(request):
    """Reporte básico de ventas"""
    return Response({
        'total_sales': 0,
        'monthly_sales': 0,
        'sales_by_day': [],
        'top_services': []
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Estadísticas para dashboard"""
    return Response({
        'total_clients': 0,
        'monthly_appointments': 0,
        'monthly_revenue': 0,
        'active_employees': 0
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reports_by_type(request):
    """Reportes por tipo (appointments, sales, etc.)"""
    report_type = request.GET.get('type', 'general')
    
    if report_type == 'appointments':
        return Response({
            'labels': ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'],
            'data': [0, 0, 0, 0, 0, 0]
        })
    elif report_type == 'sales':
        return Response({
            'labels': ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'],
            'data': [0, 0, 0, 0, 0, 0]
        })
    
    return Response({'data': []})

class AdminReportsView(views.APIView):
    """Reportes financieros para SuperAdmin"""
    permission_classes = [IsSuperAdmin]
    
    def get(self, request):
        try:
            period = request.GET.get('period', 'last_30_days')
            
            # Calcular fechas según período
            end_date = timezone.now()
            if period == 'last_7_days':
                start_date = end_date - timedelta(days=7)
            elif period == 'last_30_days':
                start_date = end_date - timedelta(days=30)
            elif period == 'last_3_months':
                start_date = end_date - timedelta(days=90)
            elif period == 'last_year':
                start_date = end_date - timedelta(days=365)
            else:
                start_date = end_date - timedelta(days=30)
            
            # Filtrar facturas del período
            invoices = Invoice.objects.filter(
                issued_at__gte=start_date,
                issued_at__lte=end_date
            )
            
            # Métricas principales
            total_revenue = invoices.filter(is_paid=True).aggregate(Sum('amount'))['amount__sum'] or 0
            pending_payments = invoices.filter(is_paid=False).aggregate(Sum('amount'))['amount__sum'] or 0
            overdue_invoices = invoices.filter(
                is_paid=False,
                due_date__lt=timezone.now()
            ).count()
            
            # Tendencia de ingresos (últimos 6 meses)
            revenue_trend = []
            for i in range(6):
                month_start = (timezone.now() - timedelta(days=30*i)).replace(day=1)
                month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                
                month_revenue = Invoice.objects.filter(
                    issued_at__gte=month_start,
                    issued_at__lte=month_end,
                    is_paid=True
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                
                revenue_trend.insert(0, {
                    'month': month_start.strftime('%b'),
                    'revenue': float(month_revenue)
                })
            
            # Top tenants por revenue
            top_tenants = []
            for tenant in Tenant.objects.filter(is_active=True)[:10]:
                tenant_revenue = invoices.filter(
                    user__tenant=tenant,
                    is_paid=True
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                
                if tenant_revenue > 0:
                    top_tenants.append({
                        'tenant_name': tenant.name,
                        'revenue': float(tenant_revenue),
                        'plan': tenant.subscription_plan.name if tenant.subscription_plan else 'FREE'
                    })
            
            top_tenants.sort(key=lambda x: x['revenue'], reverse=True)
            
            return Response({
                'period': period,
                'total_revenue': float(total_revenue),
                'pending_payments': float(pending_payments),
                'overdue_invoices': overdue_invoices,
                'revenue_trend': revenue_trend,
                'top_tenants': top_tenants[:5],
                'summary': {
                    'total_invoices': invoices.count(),
                    'paid_invoices': invoices.filter(is_paid=True).count(),
                    'average_invoice': float(total_revenue / invoices.count()) if invoices.count() > 0 else 0
                }
            })
            
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Error al generar reportes'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)