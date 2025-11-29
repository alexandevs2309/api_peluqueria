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
    from apps.employees_api.models import Employee
    
    tenant = request.user.tenant
    
    # Estadísticas básicas
    total_employees = Employee.objects.filter(tenant=tenant).count()
    active_employees = Employee.objects.filter(tenant=tenant, is_active=True).count()
    
    # Empleados por especialidad
    employees_by_specialty = Employee.objects.filter(
        tenant=tenant, is_active=True
    ).values('specialty').annotate(count=Count('id'))
    
    # Top performers simulados
    employees = Employee.objects.filter(tenant=tenant, is_active=True)[:5]
    top_performers = []
    for i, employee in enumerate(employees):
        top_performers.append({
            'employee_name': employee.user.full_name,
            'appointments': 25 - (i * 3),
            'sales': 2000.0 - (i * 200),
            'specialty': employee.specialty or 'General'
        })
    
    return Response({
        'total_employees': total_employees,
        'active_employees': active_employees,
        'employees_by_specialty': list(employees_by_specialty),
        'top_performers': top_performers
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sales_report(request):
    """Reporte básico de ventas"""
    from apps.pos_api.models import Sale
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
    
    # Servicios más vendidos (simulado por ahora)
    top_services = [
        {'service__name': 'Corte Clásico', 'total_sold': 45, 'total_revenue': 2250},
        {'service__name': 'Barba', 'total_sold': 32, 'total_revenue': 1600},
        {'service__name': 'Corte + Barba', 'total_sold': 28, 'total_revenue': 1680},
        {'service__name': 'Afeitado', 'total_sold': 15, 'total_revenue': 450},
        {'service__name': 'Tratamiento', 'total_sold': 8, 'total_revenue': 400}
    ]
    
    return Response({
        'total_sales': float(total_sales),
        'monthly_sales': float(monthly_sales),
        'sales_by_day': sales_by_day,
        'top_services': list(top_services)
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Estadísticas para dashboard"""
    from apps.clients_api.models import Client
    from apps.employees_api.models import Employee
    
    tenant = request.user.tenant
    
    # Estadísticas básicas que sabemos que funcionan
    total_clients = Client.objects.filter(tenant=tenant, is_active=True).count()
    active_employees = Employee.objects.filter(tenant=tenant, is_active=True).count()
    
    return Response({
        'total_clients': total_clients,
        'monthly_appointments': 25,  # Simulado por ahora
        'monthly_revenue': 15420.50,  # Simulado por ahora
        'active_employees': active_employees
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def appointments_calendar_data(request):
    """Datos para calendario de citas"""
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
@permission_classes([IsAuthenticated])
def kpi_dashboard(request):
    """KPIs principales para dashboard"""
    from apps.clients_api.models import Client
    from apps.employees_api.models import Employee
    from apps.pos_api.models import Sale
    from apps.appointments_api.models import Appointment
    from django.db.models import Sum, Count, Avg
    
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
    
    return Response({
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
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def services_performance(request):
    """Rendimiento de servicios"""
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
    ).order_by('-total_sales')[:10]
    
    return Response({
        'period_days': days,
        'top_services': list(services_data)
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
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