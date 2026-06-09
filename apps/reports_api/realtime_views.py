from rest_framework.views import APIView
from rest_framework.response import Response
from apps.core.tenant_permissions import TenantPermissionByAction
from apps.subscriptions_api.permissions import HasFeaturePermission
from apps.subscriptions_api.access_control import has_feature
from django.db.models import Count, Sum, F, Q
from django.utils import timezone
from datetime import timedelta
from apps.pos_api.models import Sale
from apps.appointments_api.models import Appointment
from apps.clients_api.models import Client


def get_report_branch_id(request):
    branch_id = request.query_params.get('branch_id') or request.query_params.get('branch')
    user = request.user
    if user and getattr(user, 'is_authenticated', False) and not user.is_superuser:
        from apps.auth_api.role_utils import get_effective_role_api
        user_role = get_effective_role_api(user, tenant=getattr(request, 'tenant', user.tenant))
        if user_role != 'Client-Admin' and hasattr(user, 'employee_profile') and user.employee_profile:
            if user.employee_profile.branch_id:
                branch_id = user.employee_profile.branch_id
    return branch_id


class RealtimeMetricsView(APIView):
    """Métricas en tiempo real para dashboard"""
    permission_classes = [TenantPermissionByAction, HasFeaturePermission]
    required_feature = 'reports'
    permission_map = {
        'GET': 'reports_api.view_kpi_dashboard',
    }

    def get(self, request):
        tenant = request.user.tenant
        branch_id = get_report_branch_id(request)
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        sale_filter = {'user__tenant': tenant, 'date_time__gte': today_start}
        appointment_filter = {'client__tenant': tenant, 'date_time__date': now.date()}
        yesterday_filter = {'user__tenant': tenant, 'date_time__gte': today_start - timedelta(days=1), 'date_time__lt': today_start}
        upcoming_filter = {
            'client__tenant': tenant,
            'date_time__gte': now,
            'date_time__lte': now + timedelta(hours=2),
            'status': 'scheduled'
        }

        if branch_id:
            sale_filter['branch_id'] = branch_id
            appointment_filter['branch_id'] = branch_id
            yesterday_filter['branch_id'] = branch_id
            upcoming_filter['branch_id'] = branch_id

        today_sales = Sale.objects.filter(**sale_filter).aggregate(
            total=Sum('total'),
            count=Count('id')
        )

        today_appointments = Appointment.objects.filter(**appointment_filter).aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
            pending=Count('id', filter=Q(status='scheduled'))
        )

        yesterday_sales = Sale.objects.filter(**yesterday_filter).aggregate(total=Sum('total'))['total'] or 0

        today_revenue = float(today_sales['total'] or 0)
        yesterday_revenue = float(yesterday_sales)

        revenue_change = 0
        if yesterday_revenue > 0:
            revenue_change = ((today_revenue - yesterday_revenue) / yesterday_revenue) * 100

        upcoming_appointments = Appointment.objects.filter(**upcoming_filter).select_related('client', 'stylist', 'service').values(
            'client__full_name',
            'stylist__full_name',
            'service__name',
            'date_time'
        )

        return Response({
            'timestamp': now.isoformat(),
            'today': {
                'revenue': today_revenue,
                'sales_count': today_sales['count'] or 0,
                'appointments_total': today_appointments['total'] or 0,
                'appointments_completed': today_appointments['completed'] or 0,
                'appointments_pending': today_appointments['pending'] or 0
            },
            'comparison': {
                'revenue_change_percent': round(revenue_change, 2),
                'yesterday_revenue': yesterday_revenue
            },
            'upcoming_appointments': list(upcoming_appointments)
        })


class LiveDashboardView(APIView):
    """Datos para dashboard en vivo"""
    permission_classes = [TenantPermissionByAction, HasFeaturePermission]
    required_feature = 'reports'
    permission_map = {
        'GET': 'reports_api.view_kpi_dashboard',
    }

    def get(self, request):
        tenant = request.user.tenant
        branch_id = get_report_branch_id(request)
        hourly_data = []
        now = timezone.now()

        for i in range(24):
            hour_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=i)
            hour_end = hour_start + timedelta(hours=1)

            sale_filter = {
                'user__tenant': tenant,
                'date_time__gte': hour_start,
                'date_time__lt': hour_end
            }
            if branch_id:
                sale_filter['branch_id'] = branch_id

            hour_sales = Sale.objects.filter(**sale_filter).aggregate(total=Sum('total'))['total'] or 0

            hourly_data.insert(0, {
                'hour': hour_start.strftime('%H:00'),
                'sales': float(hour_sales)
            })

        active_employees = []
        from apps.employees_api.models import Employee

        emp_filter = {'tenant': tenant, 'is_active': True}
        if branch_id:
            emp_filter['branch_id'] = branch_id

        employees = Employee.objects.filter(**emp_filter)
        for emp in employees:
            apt_filter = {
                'stylist': emp.user,
                'date_time__gte': now - timedelta(minutes=30),
                'date_time__lte': now + timedelta(hours=2),
                'status': 'scheduled'
            }
            if branch_id:
                apt_filter['branch_id'] = branch_id

            current_appointment = Appointment.objects.filter(**apt_filter).first()

            status = 'available'
            next_client = None

            if current_appointment:
                if current_appointment.date_time <= now:
                    status = 'busy'
                else:
                    status = 'scheduled'
                next_client = current_appointment.client.full_name

            active_employees.append({
                'name': emp.user.full_name or emp.user.email,
                'status': status,
                'next_client': next_client,
                'next_appointment': current_appointment.date_time.isoformat() if current_appointment else None
            })

        return Response({
            'hourly_sales': hourly_data,
            'employee_status': active_employees,
            'last_updated': now.isoformat()
        })


class PerformanceAlertsView(APIView):
    """Alertas de rendimiento y oportunidades"""
    permission_classes = [TenantPermissionByAction, HasFeaturePermission]
    required_feature = 'reports'
    permission_map = {
        'GET': 'reports_api.view_kpi_dashboard',
    }

    def get(self, request):
        tenant = request.user.tenant
        branch_id = get_report_branch_id(request)
        alerts = []

        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        sale_today_filter = {'user__tenant': tenant, 'date_time__gte': today_start}
        last_month = today_start - timedelta(days=30)
        sale_avg_filter = {'user__tenant': tenant, 'date_time__gte': last_month, 'date_time__lt': today_start}
        appointment_cancelled_filter = {'client__tenant': tenant, 'date_time__date': timezone.now().date(), 'status': 'cancelled'}
        
        if branch_id:
            sale_today_filter['branch_id'] = branch_id
            sale_avg_filter['branch_id'] = branch_id
            appointment_cancelled_filter['branch_id'] = branch_id

        today_sales = Sale.objects.filter(**sale_today_filter).aggregate(total=Sum('total'))['total'] or 0
        avg_daily_sales = Sale.objects.filter(**sale_avg_filter).aggregate(total=Sum('total'))['total'] or 0

        daily_target = (float(avg_daily_sales) / 30) if avg_daily_sales > 0 else 0

        if daily_target > 0:
            progress = (float(today_sales) / daily_target) * 100

            if progress < 50 and timezone.now().hour > 14:
                alerts.append({
                    'type': 'revenue_low',
                    'message': f'Ventas del día al {progress:.0f}% de la meta',
                    'severity': 'warning',
                    'action': 'Considerar promociones o llamar clientes'
                })
            elif progress > 120:
                alerts.append({
                    'type': 'revenue_high',
                    'message': f'Excelente día! {progress:.0f}% de la meta alcanzada',
                    'severity': 'success',
                    'action': 'Mantener el ritmo'
                })

        cancelled_today = Appointment.objects.filter(**appointment_cancelled_filter).count()

        if cancelled_today > 2:
            alerts.append({
                'type': 'cancellations_high',
                'message': f'{cancelled_today} citas canceladas hoy',
                'severity': 'warning',
                'action': 'Revisar política de cancelaciones'
            })

        if has_feature(tenant, 'inventory'):
            from apps.inventory_api.models import Product
            product_filter = {
                'tenant': tenant,
                'stock__lte': F('min_stock'),
                'is_active': True
            }
            if branch_id:
                product_filter['branch_id'] = branch_id

            low_stock_products = Product.objects.filter(**product_filter).count()

            if low_stock_products > 0:
                alerts.append({
                    'type': 'inventory_low',
                    'message': f'{low_stock_products} productos con stock bajo',
                    'severity': 'info',
                    'action': 'Revisar inventario y hacer pedidos'
                })

        return Response({
            'alerts': alerts,
            'daily_progress': {
                'current': float(today_sales),
                'target': daily_target,
                'percentage': (float(today_sales) / daily_target * 100) if daily_target > 0 else 0
            }
        })
