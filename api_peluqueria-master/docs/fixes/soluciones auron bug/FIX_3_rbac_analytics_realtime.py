# ============================================================
# FIX 3: apps/reports_api/analytics_views.py — RBAC completo
# PROBLEMA: Las 3 vistas usan @permission_classes([TenantPermissionByAction])
#            pero asignan permission_map DENTRO de la función DESPUÉS de que
#            DRF ya evaluó los permisos. Eso significa que permission_map
#            nunca se encuentra y TenantPermissionByAction retorna False
#            (deniega por defecto en has_permission cuando action no está en
#            permission_map) — PERO el código actual rompe de otra forma:
#            el attribute set en la función no es el view, es la función en
#            sí, lo cual DRF nunca lee.
#
# SOLUCIÓN REAL: Convertir a APIView subclasses con permission_map como
#                atributo de clase. Esto es lo que TenantPermissionByAction
#                espera via getattr(view, 'permission_map', {}).
#
# INSTRUCCIÓN: Reemplaza apps/reports_api/analytics_views.py completo.
# ============================================================

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status
from apps.core.tenant_permissions import TenantPermissionByAction
from apps.subscriptions_api.permissions import requires_feature, HasFeaturePermission
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from datetime import timedelta
from apps.clients_api.models import Client
from apps.employees_api.models import Employee
from apps.pos_api.models import Sale
from apps.appointments_api.models import Appointment
from apps.services_api.models import Service


class AdvancedAnalyticsView(APIView):
    """Analytics avanzados — solo Client-Admin/Manager con feature advanced_reports."""
    permission_classes = [TenantPermissionByAction, HasFeaturePermission]
    required_feature = 'advanced_reports'
    permission_map = {
        'GET': 'reports_api.view_advanced_analytics',
    }

    def get(self, request):
        tenant = request.user.tenant
        period = request.GET.get('period', '30')
        days = int(period)

        retention_data = calculate_client_retention(tenant, days)
        employee_performance = calculate_employee_performance(tenant, days)
        service_trends = calculate_service_trends(tenant, days)
        predictions = calculate_predictions(tenant, days)

        return Response({
            'period_days': days,
            'retention': retention_data,
            'employee_performance': employee_performance,
            'service_trends': service_trends,
            'predictions': predictions,
            'generated_at': timezone.now().isoformat()
        })


class BusinessIntelligenceView(APIView):
    """Business Intelligence — solo Client-Admin con feature advanced_reports."""
    permission_classes = [TenantPermissionByAction, HasFeaturePermission]
    required_feature = 'advanced_reports'
    permission_map = {
        'GET': 'reports_api.view_advanced_analytics',
    }

    def get(self, request):
        tenant = request.user.tenant
        business_kpis = {
            'customer_lifetime_value': calculate_clv(tenant),
            'average_revenue_per_user': calculate_arpu(tenant),
            'churn_rate': calculate_churn_rate(tenant),
            'growth_rate': calculate_growth_rate(tenant),
            'capacity_utilization': calculate_capacity_utilization(tenant),
        }
        return Response({
            'business_kpis': business_kpis,
            'seasonal_analysis': calculate_seasonal_patterns(tenant),
            'benchmarks': calculate_internal_benchmarks(tenant),
            'recommendations': generate_recommendations(business_kpis),
        })


class PredictiveAnalyticsView(APIView):
    """Análisis predictivo — solo Client-Admin con feature advanced_reports."""
    permission_classes = [TenantPermissionByAction, HasFeaturePermission]
    required_feature = 'advanced_reports'
    permission_map = {
        'GET': 'reports_api.view_advanced_analytics',
    }

    def get(self, request):
        tenant = request.user.tenant
        return Response({
            'demand_forecast': predict_demand(tenant),
            'revenue_forecast': predict_revenue(tenant),
            'at_risk_clients': identify_at_risk_clients(tenant),
            'growth_opportunities': identify_growth_opportunities(tenant),
        })


# ---- Mantener todas las funciones helper sin cambios (calculate_*, predict_*, etc.) ----
# (copiar las funciones existentes de analytics_views.py aquí sin modificación)


# ============================================================
# FIX 3b: apps/reports_api/realtime_views.py — RBAC completo
# PROBLEMA IDÉNTICO: permission_map asignado en la función, nunca leído.
# SOLUCIÓN: Convertir a APIView subclasses.
# ============================================================

# realtime_views.py — Versión corregida

from rest_framework.views import APIView
from rest_framework.response import Response
from apps.core.tenant_permissions import TenantPermissionByAction
from apps.subscriptions_api.permissions import HasFeaturePermission
from django.db.models import Count, Sum, F
from django.utils import timezone
from datetime import timedelta
from apps.pos_api.models import Sale
from apps.appointments_api.models import Appointment
from apps.clients_api.models import Client


class RealtimeMetricsView(APIView):
    """Métricas en tiempo real — Client-Admin/Manager."""
    permission_classes = [TenantPermissionByAction, HasFeaturePermission]
    required_feature = 'basic_reports'
    permission_map = {
        'GET': 'reports_api.view_kpi_dashboard',
    }

    def get(self, request):
        tenant = request.user.tenant
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        today_sales = Sale.objects.filter(
            user__tenant=tenant, date_time__gte=today_start
        ).aggregate(total=Sum('total'), count=Count('id'))

        today_appointments = Appointment.objects.filter(
            client__tenant=tenant, date_time__date=now.date()
        ).aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
            pending=Count('id', filter=Q(status='scheduled'))
        )

        yesterday_start = today_start - timedelta(days=1)
        yesterday_sales = Sale.objects.filter(
            user__tenant=tenant,
            date_time__gte=yesterday_start,
            date_time__lt=today_start
        ).aggregate(total=Sum('total'))['total'] or 0

        today_revenue = float(today_sales['total'] or 0)
        yesterday_revenue = float(yesterday_sales)
        revenue_change = (
            ((today_revenue - yesterday_revenue) / yesterday_revenue * 100)
            if yesterday_revenue > 0 else 0
        )

        next_2_hours = now + timedelta(hours=2)
        upcoming_appointments = Appointment.objects.filter(
            client__tenant=tenant,
            date_time__gte=now,
            date_time__lte=next_2_hours,
            status='scheduled'
        ).values('client__full_name', 'stylist__full_name', 'service__name', 'date_time')

        return Response({
            'timestamp': now.isoformat(),
            'today': {
                'revenue': today_revenue,
                'sales_count': today_sales['count'] or 0,
                'appointments_total': today_appointments['total'] or 0,
                'appointments_completed': today_appointments['completed'] or 0,
                'appointments_pending': today_appointments['pending'] or 0,
            },
            'comparison': {
                'revenue_change_percent': round(revenue_change, 2),
                'yesterday_revenue': yesterday_revenue,
            },
            'upcoming_appointments': list(upcoming_appointments),
        })


class LiveDashboardView(APIView):
    """Dashboard en vivo — Client-Admin/Manager."""
    permission_classes = [TenantPermissionByAction, HasFeaturePermission]
    required_feature = 'basic_reports'
    permission_map = {
        'GET': 'reports_api.view_kpi_dashboard',
    }

    def get(self, request):
        tenant = request.user.tenant
        now = timezone.now()

        hourly_data = []
        for i in range(24):
            hour_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=i)
            hour_end = hour_start + timedelta(hours=1)
            hour_sales = Sale.objects.filter(
                user__tenant=tenant,
                date_time__gte=hour_start,
                date_time__lt=hour_end
            ).aggregate(total=Sum('total'))['total'] or 0
            hourly_data.insert(0, {
                'hour': hour_start.strftime('%H:00'),
                'sales': float(hour_sales)
            })

        from apps.employees_api.models import Employee
        active_employees = []
        for emp in Employee.objects.filter(tenant=tenant, is_active=True):
            current_appointment = Appointment.objects.filter(
                stylist=emp.user,
                date_time__gte=now - timedelta(minutes=30),
                date_time__lte=now + timedelta(hours=2),
                status='scheduled'
            ).first()

            emp_status = 'available'
            next_client = None
            if current_appointment:
                emp_status = 'busy' if current_appointment.date_time <= now else 'scheduled'
                next_client = current_appointment.client.full_name

            active_employees.append({
                'name': emp.user.full_name or emp.user.email,
                'status': emp_status,
                'next_client': next_client,
                'next_appointment': (
                    current_appointment.date_time.isoformat()
                    if current_appointment else None
                ),
            })

        return Response({
            'hourly_sales': hourly_data,
            'employee_status': active_employees,
            'last_updated': now.isoformat(),
        })


class PerformanceAlertsView(APIView):
    """Alertas de rendimiento — Client-Admin/Manager."""
    permission_classes = [TenantPermissionByAction, HasFeaturePermission]
    required_feature = 'basic_reports'
    permission_map = {
        'GET': 'reports_api.view_kpi_dashboard',
    }

    def get(self, request):
        tenant = request.user.tenant
        alerts = []
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        today_sales = Sale.objects.filter(
            user__tenant=tenant, date_time__gte=today_start
        ).aggregate(total=Sum('total'))['total'] or 0

        last_month = today_start - timedelta(days=30)
        avg_daily_sales = Sale.objects.filter(
            user__tenant=tenant,
            date_time__gte=last_month,
            date_time__lt=today_start
        ).aggregate(total=Sum('total'))['total'] or 0

        daily_target = float(avg_daily_sales) / 30 if avg_daily_sales > 0 else 0

        if daily_target > 0:
            progress = float(today_sales) / daily_target * 100
            if progress < 50 and timezone.now().hour > 14:
                alerts.append({
                    'type': 'revenue_low',
                    'message': f'Ventas del día al {progress:.0f}% de la meta',
                    'severity': 'warning',
                    'action': 'Considerar promociones o llamar clientes',
                })
            elif progress > 120:
                alerts.append({
                    'type': 'revenue_high',
                    'message': f'¡Excelente día! {progress:.0f}% de la meta alcanzada',
                    'severity': 'success',
                    'action': 'Mantener el ritmo',
                })

        cancelled_today = Appointment.objects.filter(
            client__tenant=tenant,
            date_time__date=timezone.now().date(),
            status='cancelled'
        ).count()
        if cancelled_today > 2:
            alerts.append({
                'type': 'cancellations_high',
                'message': f'{cancelled_today} citas canceladas hoy',
                'severity': 'warning',
                'action': 'Revisar política de cancelaciones',
            })

        from apps.subscriptions_api.access_control import has_feature
        if has_feature(tenant, 'inventory'):
            from apps.inventory_api.models import Product
            low_stock_products = Product.objects.filter(
                tenant=tenant, stock__lte=F('min_stock'), is_active=True
            ).count()
            if low_stock_products > 0:
                alerts.append({
                    'type': 'inventory_low',
                    'message': f'{low_stock_products} productos con stock bajo',
                    'severity': 'info',
                    'action': 'Revisar inventario y hacer pedidos',
                })

        return Response({
            'alerts': alerts,
            'daily_progress': {
                'current': float(today_sales),
                'target': daily_target,
                'percentage': (float(today_sales) / daily_target * 100) if daily_target > 0 else 0,
            },
        })


# ============================================================
# FIX 3c: apps/reports_api/urls.py — Actualizar rutas a class-based views
# AGREGAR o REEMPLAZAR las rutas de analytics y realtime.
# ============================================================

# En reports_api/urls.py, reemplazar:
#
# urlpatterns = [
#     ...
#     # Analytics (antes eran @api_view functions — ahora son class-based views)
#     path('advanced-analytics/', AdvancedAnalyticsView.as_view(), name='advanced-analytics'),
#     path('business-intelligence/', BusinessIntelligenceView.as_view(), name='business-intelligence'),
#     path('predictive-analytics/', PredictiveAnalyticsView.as_view(), name='predictive-analytics'),
#     # Realtime
#     path('realtime/', RealtimeMetricsView.as_view(), name='realtime-metrics'),
#     path('live-dashboard/', LiveDashboardView.as_view(), name='live-dashboard'),
#     path('performance-alerts/', PerformanceAlertsView.as_view(), name='performance-alerts'),
# ]
