from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import views, status
from apps.core.tenant_permissions import TenantPermissionByAction, tenant_permission
from apps.core.permissions import IsSuperAdmin
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from apps.tenants_api.models import Tenant
from apps.billing_api.models import Invoice
from apps.auth_api.models import User
from apps.subscriptions_api.permissions import requires_feature
from .pagination import ReportsPagination
from apps.settings_api.policy_utils import (
    get_platform_commission_rate,
    calculate_platform_commission,
    calculate_platform_net_revenue,
)

@api_view(['GET'])
@permission_classes([TenantPermissionByAction])
@requires_feature('basic_reports')
def employee_report(request):
    employee_report.permission_map = {'get': 'reports_api.view_employee_reports'}
    """Reporte básico de empleados"""
    from apps.employees_api.models import Employee
    from apps.pos_api.models import Sale
    
    tenant = request.user.tenant
    
    # Estadísticas básicas
    total_employees = Employee.objects.filter(tenant=tenant).count()
    active_employees = Employee.objects.filter(tenant=tenant, is_active=True).count()
    
    # Empleados por especialidad
    employees_by_specialty = Employee.objects.filter(
        tenant=tenant, is_active=True
    ).values('specialty').annotate(count=Count('id'))
    
    # Top performers REALES desde ventas
    top_performers = Sale.objects.filter(
        employee__tenant=tenant,
        employee__isnull=False
    ).values(
        'employee__user__full_name',
        'employee__specialty'
    ).annotate(
        total_sales=Sum('total'),
        sales_count=Count('id')
    ).order_by('-total_sales')[:5]
    
    top_performers_list = [{
        'employee_name': p['employee__user__full_name'],
        'sales': float(p['total_sales']),
        'sales_count': p['sales_count'],
        'specialty': p['employee__specialty'] or 'General'
    } for p in top_performers]
    
    return Response({
        'total_employees': total_employees,
        'active_employees': active_employees,
        'employees_by_specialty': list(employees_by_specialty),
        'top_performers': top_performers_list
    })

@api_view(['GET'])
@permission_classes([TenantPermissionByAction])
@requires_feature('basic_reports')
def sales_report(request):
    sales_report.permission_map = {'get': 'reports_api.view_sales_reports'}
    """Reporte básico de ventas"""
    from apps.pos_api.models import Sale, SaleDetail
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    tenant = request.user.tenant
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Ventas totales
    total_sales = Sale.objects.filter(user__tenant=tenant).aggregate(
        total=Sum('total')
    )['total'] or 0
    
    # Ventas del mes
    monthly_sales = Sale.objects.filter(
        user__tenant=tenant,
        date_time__gte=month_start
    ).aggregate(total=Sum('total'))['total'] or 0
    
    # Ventas por día (últimos 7 días)
    sales_by_day = []
    for i in range(7):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        day_sales = Sale.objects.filter(
            user__tenant=tenant,
            date_time__gte=day_start,
            date_time__lt=day_end
        ).aggregate(total=Sum('total'))['total'] or 0
        
        sales_by_day.insert(0, {
            'date': day.strftime('%Y-%m-%d'),
            'sales': float(day_sales)
        })
    
    # Servicios más vendidos REALES
    top_services = SaleDetail.objects.filter(
        sale__user__tenant=tenant,
        content_type__model='service'
    ).values('name').annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum('price')
    ).order_by('-total_revenue')[:5]
    
    return Response({
        'total_sales': float(total_sales),
        'monthly_sales': float(monthly_sales),
        'sales_by_day': sales_by_day,
        'top_services': list(top_services)
    })

@api_view(['GET'])
@permission_classes([tenant_permission('reports_api.view_kpi_dashboard')])
def dashboard_stats(request):
    """Estadísticas para dashboard"""
    from django.core.cache import cache
    from apps.clients_api.models import Client
    from apps.employees_api.models import Employee
    from apps.pos_api.models import Sale
    from apps.appointments_api.models import Appointment
    
    # Cache key basado en tenant
    cache_key = f'dashboard_stats_{getattr(request.user.tenant, "id", "none")}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return Response(cached_data)
    
    tenant = request.user.tenant
    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Estadísticas básicas que sabemos que funcionan
    total_clients = Client.objects.filter(tenant=tenant, is_active=True).count()
    active_employees = Employee.objects.filter(tenant=tenant, is_active=True).count()
    
    monthly_appointments = Appointment.objects.filter(
        client__tenant=tenant,
        date_time__gte=month_start
    ).count()

    monthly_revenue = Sale.objects.filter(
        user__tenant=tenant,
        date_time__gte=month_start
    ).aggregate(total=Sum('total'))['total'] or 0

    data = {
        'total_clients': total_clients,
        'monthly_appointments': monthly_appointments,
        'monthly_revenue': float(monthly_revenue),
        'active_employees': active_employees
    }
    
    # Cache por 60 segundos
    cache.set(cache_key, data, 60)
    
    return Response(data)

@api_view(['GET'])
@permission_classes([tenant_permission('reports_api.view_sales_reports')])
def reports_by_type(request):
    """Reportes por tipo (appointments, sales, etc.)"""
    report_type = request.GET.get('type', 'general')
    tenant = request.user.tenant
    
    if report_type == 'appointments':
        from apps.appointments_api.models import Appointment
        from django.db.models import Count
        from datetime import datetime, timedelta
        
        # Últimos 6 meses de citas
        data = []
        labels = []
        for i in range(6):
            month_start = (timezone.now() - timedelta(days=30*i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            count = Appointment.objects.filter(
                client__tenant=tenant,
                date_time__gte=month_start,
                date_time__lte=month_end
            ).count()
            
            data.insert(0, count)
            labels.insert(0, month_start.strftime('%b'))
        
        return Response({'labels': labels, 'data': data})
        
    elif report_type == 'sales':
        from apps.pos_api.models import Sale
        from django.db.models import Sum
        
        # Últimos 6 meses de ventas
        data = []
        labels = []
        for i in range(6):
            month_start = (timezone.now() - timedelta(days=30*i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            total = Sale.objects.filter(
                user__tenant=tenant,
                date_time__gte=month_start,
                date_time__lte=month_end
            ).aggregate(total=Sum('total'))['total'] or 0
            
            data.insert(0, float(total))
            labels.insert(0, month_start.strftime('%b'))
        
        return Response({'labels': labels, 'data': data})
    
    return Response({'data': []})

class AdminReportsView(views.APIView):
    """Reportes financieros para SuperAdmin"""
    permission_classes = [IsSuperAdmin]
    
    def get(self, request):
        try:
            period = request.GET.get('period', 'last_30_days')
            end_date = timezone.now()
            commission_rate = get_platform_commission_rate()

            # Calcular fechas según período (incluye rango custom real)
            if period == 'custom':
                start_raw = request.GET.get('start_date')
                end_raw = request.GET.get('end_date')
                if not start_raw or not end_raw:
                    return Response(
                        {'error': 'start_date y end_date son requeridos para período custom'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                try:
                    start_date = datetime.fromisoformat(start_raw).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    end_date = datetime.fromisoformat(end_raw).replace(
                        hour=23, minute=59, second=59, microsecond=999999
                    )
                    if timezone.is_naive(start_date):
                        start_date = timezone.make_aware(start_date)
                    if timezone.is_naive(end_date):
                        end_date = timezone.make_aware(end_date)
                except ValueError:
                    return Response(
                        {'error': 'Formato de fecha inválido. Use YYYY-MM-DD'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            elif period == 'last_7_days':
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
            platform_commission_amount = calculate_platform_commission(total_revenue)
            net_revenue = calculate_platform_net_revenue(total_revenue)
            pending_payments = invoices.filter(is_paid=False).aggregate(Sum('amount'))['amount__sum'] or 0
            overdue_invoices = invoices.filter(
                is_paid=False,
                due_date__lt=timezone.now()
            ).count()
            
            # Tendencia de ingresos REAL según el período seleccionado
            revenue_trend = []
            total_days = max(1, (end_date.date() - start_date.date()).days + 1)
            if total_days <= 45:
                cursor = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                while cursor <= end_date:
                    day_end = cursor + timedelta(days=1)
                    day_revenue = Invoice.objects.filter(
                        issued_at__gte=cursor,
                        issued_at__lt=day_end,
                        is_paid=True
                    ).aggregate(Sum('amount'))['amount__sum'] or 0
                    day_commission = calculate_platform_commission(day_revenue)
                    day_net_revenue = calculate_platform_net_revenue(day_revenue)
                    revenue_trend.append({
                        'label': cursor.strftime('%d %b'),
                        'revenue': float(day_revenue),
                        'commission_amount': float(day_commission),
                        'net_revenue': float(day_net_revenue)
                    })
                    cursor = day_end
            else:
                cursor = start_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                while cursor <= end_date:
                    next_month = (cursor + timedelta(days=32)).replace(day=1)
                    month_revenue = Invoice.objects.filter(
                        issued_at__gte=cursor,
                        issued_at__lt=next_month,
                        issued_at__lte=end_date,
                        is_paid=True
                    ).aggregate(Sum('amount'))['amount__sum'] or 0
                    month_commission = calculate_platform_commission(month_revenue)
                    month_net_revenue = calculate_platform_net_revenue(month_revenue)
                    revenue_trend.append({
                        'label': cursor.strftime('%b %Y'),
                        'revenue': float(month_revenue),
                        'commission_amount': float(month_commission),
                        'net_revenue': float(month_net_revenue)
                    })
                    cursor = next_month
            
            # Top tenants por revenue - OPTIMIZADO: Una sola query
            top_tenants_data = Invoice.objects.filter(
                issued_at__gte=start_date,
                issued_at__lte=end_date,
                is_paid=True
            ).values(
                'user__tenant__name',
                'user__tenant__subscription_plan__name'
            ).annotate(
                total_revenue=Sum('amount')
            ).order_by('-total_revenue')[:5]
            
            top_tenants = [{
                'tenant_name': item['user__tenant__name'],
                'revenue': float(item['total_revenue']),
                'commission_amount': float(calculate_platform_commission(item['total_revenue'])),
                'net_revenue': float(calculate_platform_net_revenue(item['total_revenue'])),
                'plan': item['user__tenant__subscription_plan__name'] or 'FREE'
            } for item in top_tenants_data]
            
            return Response({
                'period': period,
                'total_revenue': float(total_revenue),
                'commission_rate': float(commission_rate),
                'platform_commission_amount': float(platform_commission_amount),
                'net_revenue': float(net_revenue),
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


@api_view(['GET'])
@permission_classes([tenant_permission('reports_api.view_employee_reports')])
def appointments_calendar_data(request):
    """Datos para calendario de citas con paginación"""
    from apps.appointments_api.models import Appointment
    
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    
    if not start_date or not end_date:
        return Response({'error': 'start y end son requeridos'}, status=400)
    
    try:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except ValueError:
        return Response({'error': 'Formato de fecha inválido'}, status=400)
    
    appointments = Appointment.objects.filter(
        client__tenant=request.user.tenant,
        date_time__gte=start,
        date_time__lte=end
    ).select_related('client', 'stylist', 'service')
    
    # Aplicar paginación si hay muchos resultados
    if appointments.count() > 100:
        paginator = ReportsPagination()
        page = paginator.paginate_queryset(appointments, request)
        if page is not None:
            appointments = page
    
    events = []
    for apt in appointments:
        color = {
            'scheduled': '#3498db',
            'completed': '#2ecc71', 
            'cancelled': '#e74c3c'
        }.get(apt.status, '#95a5a6')
        
        events.append({
            'id': apt.id,
            'title': f"{apt.client.full_name} - {apt.service.name if apt.service else 'Sin servicio'}",
            'start': apt.date_time.isoformat(),
            'end': (apt.date_time + timedelta(minutes=apt.service.duration if apt.service else 30)).isoformat(),
            'backgroundColor': color,
            'borderColor': color,
            'extendedProps': {
                'client': apt.client.full_name,
                'stylist': apt.stylist.full_name if apt.stylist else 'Sin asignar',
                'service': apt.service.name if apt.service else 'Sin servicio',
                'status': apt.status,
                'phone': apt.client.phone or 'N/A'
            }
        })
    
    return Response(events)

@api_view(['GET'])
@permission_classes([TenantPermissionByAction])
def kpi_dashboard(request):
    kpi_dashboard.permission_map = {'get': 'reports_api.view_kpi_dashboard'}
    """KPIs principales para dashboard"""
    from django.core.cache import cache
    from apps.clients_api.models import Client
    from apps.employees_api.models import Employee
    from apps.pos_api.models import Sale
    from apps.appointments_api.models import Appointment
    from django.db.models import Sum, Count, Avg
    
    # Cache key basado en tenant
    cache_key = f'kpi_dashboard_{getattr(request.user.tenant, "id", "none")}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return Response(cached_data)
    
    tenant = request.user.tenant
    today = timezone.now().date()
    month_start = today.replace(day=1)
    week_start = today - timedelta(days=today.weekday())
    
    # KPIs del mes
    monthly_revenue = Sale.objects.filter(
        user__tenant=tenant,
        date_time__date__gte=month_start
    ).aggregate(total=Sum('total'))['total'] or 0
    
    monthly_appointments = Appointment.objects.filter(
        client__tenant=tenant,
        date_time__date__gte=month_start
    ).count()
    
    # KPIs de la semana
    weekly_revenue = Sale.objects.filter(
        user__tenant=tenant,
        date_time__date__gte=week_start
    ).aggregate(total=Sum('total'))['total'] or 0
    
    weekly_appointments = Appointment.objects.filter(
        client__tenant=tenant,
        date_time__date__gte=week_start
    ).count()
    
    # KPIs generales
    total_clients = Client.objects.filter(tenant=tenant, is_active=True).count()
    active_employees = Employee.objects.filter(tenant=tenant, is_active=True).count()
    
    # Ticket promedio
    avg_ticket = Sale.objects.filter(
        user__tenant=tenant,
        date_time__date__gte=month_start
    ).aggregate(avg=Avg('total'))['avg'] or 0
    
    data = {
        'monthly': {
            'revenue': float(monthly_revenue),
            'appointments': monthly_appointments,
            'avg_ticket': float(avg_ticket)
        },
        'weekly': {
            'revenue': float(weekly_revenue),
            'appointments': weekly_appointments
        },
        'totals': {
            'clients': total_clients,
            'employees': active_employees
        }
    }
    
    # Cache por 60 segundos
    cache.set(cache_key, data, 60)
    
    return Response(data)

@api_view(['GET'])
@permission_classes([tenant_permission('reports_api.view_kpi_dashboard')])
def services_performance(request):
    """Rendimiento de servicios con paginación"""
    from apps.pos_api.models import SaleDetail
    from apps.services_api.models import Service
    from django.db.models import Sum, Count
    
    tenant = request.user.tenant
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # Top servicios por ventas
    services_data = SaleDetail.objects.filter(
        sale__user__tenant=tenant,
        sale__date_time__gte=start_date,
        content_type__model='service'
    ).values('name').annotate(
        total_sales=Sum('price'),
        quantity_sold=Sum('quantity')
    ).order_by('-total_sales')
    
    # Aplicar paginación
    paginator = ReportsPagination()
    page = paginator.paginate_queryset(services_data, request)
    
    if page is not None:
        return paginator.get_paginated_response({
            'period_days': days,
            'services': list(page)
        })
    
    return Response({
        'period_days': days,
        'services': list(services_data)
    })

@api_view(['GET'])
@permission_classes([tenant_permission('reports_api.view_kpi_dashboard')])
def client_analytics(request):
    """Análisis de clientes"""
    from apps.clients_api.models import Client
    from apps.appointments_api.models import Appointment
    from django.db.models import Count, Q
    
    tenant = request.user.tenant
    
    # Clientes por género
    gender_stats = Client.objects.filter(tenant=tenant, is_active=True).values('gender').annotate(
        count=Count('id')
    )
    
    # Clientes nuevos vs recurrentes (este mes)
    month_start = timezone.now().replace(day=1)
    new_clients = Client.objects.filter(
        tenant=tenant,
        created_at__gte=month_start
    ).count()
    
    # Clientes con cumpleaños este mes
    current_month = timezone.now().month
    birthday_clients = Client.objects.filter(
        tenant=tenant,
        birthday__month=current_month,
        is_active=True
    ).count()
    
    return Response({
        'gender_distribution': list(gender_stats),
        'new_clients_this_month': new_clients,
        'birthday_clients': birthday_clients,
        'total_active': Client.objects.filter(tenant=tenant, is_active=True).count()
    })
