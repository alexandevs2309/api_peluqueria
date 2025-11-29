from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count, Sum, F
from django.utils import timezone
from datetime import timedelta
from apps.pos_api.models import Sale
from apps.appointments_api.models import Appointment
from apps.clients_api.models import Client

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def realtime_metrics(request):
    """Métricas en tiempo real para dashboard"""
    tenant = request.user.tenant
    now = timezone.now()
    
    # Métricas del día actual
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Ventas de hoy
    today_sales = Sale.objects.filter(
        user__tenant=tenant,
        date_time__gte=today_start
    ).aggregate(
        total=Sum('total'),
        count=Count('id')
    )
    
    # Citas de hoy
    today_appointments = Appointment.objects.filter(
        client__tenant=tenant,
        date_time__date=now.date()
    ).aggregate(
        total=Count('id'),
        completed=Count('id', filter={'status': 'completed'}),
        pending=Count('id', filter={'status': 'scheduled'})
    )
    
    # Comparación con ayer
    yesterday_start = today_start - timedelta(days=1)
    yesterday_sales = Sale.objects.filter(
        user__tenant=tenant,
        date_time__gte=yesterday_start,
        date_time__lt=today_start
    ).aggregate(total=Sum('total'))['total'] or 0
    
    # Cálculo de cambio porcentual
    today_revenue = float(today_sales['total'] or 0)
    yesterday_revenue = float(yesterday_sales)
    
    revenue_change = 0
    if yesterday_revenue > 0:
        revenue_change = ((today_revenue - yesterday_revenue) / yesterday_revenue) * 100
    
    # Próximas citas (siguientes 2 horas)
    next_2_hours = now + timedelta(hours=2)
    upcoming_appointments = Appointment.objects.filter(
        client__tenant=tenant,
        date_time__gte=now,
        date_time__lte=next_2_hours,
        status='scheduled'
    ).select_related('client', 'stylist', 'service').values(
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def live_dashboard_data(request):
    """Datos para dashboard en vivo"""
    tenant = request.user.tenant
    
    # Últimas 24 horas por hora
    hourly_data = []
    now = timezone.now()
    
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
    
    # Estado actual de empleados
    active_employees = []
    from apps.employees_api.models import Employee
    
    employees = Employee.objects.filter(tenant=tenant, is_active=True)
    for emp in employees:
        # Cita actual o próxima
        current_appointment = Appointment.objects.filter(
            stylist=emp.user,
            date_time__gte=now - timedelta(minutes=30),
            date_time__lte=now + timedelta(hours=2),
            status='scheduled'
        ).first()
        
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def performance_alerts(request):
    """Alertas de rendimiento y oportunidades"""
    tenant = request.user.tenant
    alerts = []
    
    # Verificar metas diarias
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_sales = Sale.objects.filter(
        user__tenant=tenant,
        date_time__gte=today_start
    ).aggregate(total=Sum('total'))['total'] or 0
    
    # Meta diaria básica (promedio del mes anterior)
    last_month = today_start - timedelta(days=30)
    avg_daily_sales = Sale.objects.filter(
        user__tenant=tenant,
        date_time__gte=last_month,
        date_time__lt=today_start
    ).aggregate(total=Sum('total'))['total'] or 0
    
    daily_target = (float(avg_daily_sales) / 30) if avg_daily_sales > 0 else 0
    
    if daily_target > 0:
        progress = (float(today_sales) / daily_target) * 100
        
        if progress < 50 and timezone.now().hour > 14:  # Después de las 2 PM
            alerts.append({
                'type': 'revenue_low',
                'message': f'Ventas del día al {progress:.0f}% de la meta',
                'severity': 'warning',
                'action': 'Considerar promociones o llamar clientes'
            })
        elif progress > 120:
            alerts.append({
                'type': 'revenue_high',
                'message': f'¡Excelente día! {progress:.0f}% de la meta alcanzada',
                'severity': 'success',
                'action': 'Mantener el ritmo'
            })
    
    # Verificar citas canceladas hoy
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
            'action': 'Revisar política de cancelaciones'
        })
    
    # Verificar stock bajo
    from apps.inventory_api.models import Product
    low_stock_products = Product.objects.filter(
        tenant=tenant,
        stock__lte=F('min_stock'),
        is_active=True
    ).count()
    
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