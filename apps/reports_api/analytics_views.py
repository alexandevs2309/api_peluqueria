from rest_framework.views import APIView
from rest_framework.response import Response
from apps.core.tenant_permissions import TenantPermissionByAction
from apps.subscriptions_api.permissions import HasFeaturePermission
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from datetime import datetime, timedelta, date
from apps.clients_api.models import Client
from apps.employees_api.models import Employee
from apps.pos_api.models import Sale
from apps.appointments_api.models import Appointment
from apps.services_api.models import Service


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


class AdvancedAnalyticsView(APIView):
    """Analytics avanzados con métricas de negocio"""
    permission_classes = [TenantPermissionByAction, HasFeaturePermission]
    required_feature = 'reports'
    permission_map = {
        'GET': 'reports_api.view_advanced_analytics',
    }

    def get(self, request):
        tenant = request.user.tenant
        branch_id = get_report_branch_id(request)
        period = request.GET.get('period', '30')  # dias
        days = int(period)

        retention_data = calculate_client_retention(tenant, days, branch_id)
        employee_performance = calculate_employee_performance(tenant, days, branch_id)
        service_trends = calculate_service_trends(tenant, days, branch_id)
        predictions = calculate_predictions(tenant, days, branch_id)

        return Response({
            'period_days': days,
            'retention': retention_data,
            'employee_performance': employee_performance,
            'service_trends': service_trends,
            'predictions': predictions,
            'generated_at': timezone.now().isoformat()
        })


class BusinessIntelligenceView(APIView):
    """Business Intelligence con KPIs avanzados"""
    permission_classes = [TenantPermissionByAction, HasFeaturePermission]
    required_feature = 'reports'
    permission_map = {
        'GET': 'reports_api.view_advanced_analytics',
    }

    def get(self, request):
        tenant = request.user.tenant
        branch_id = get_report_branch_id(request)
        
        business_kpis = {
            'customer_lifetime_value': calculate_clv(tenant, branch_id),
            'average_revenue_per_user': calculate_arpu(tenant, branch_id),
            'churn_rate': calculate_churn_rate(tenant, branch_id),
            'growth_rate': calculate_growth_rate(tenant, branch_id),
            'capacity_utilization': calculate_capacity_utilization(tenant, branch_id)
        }

        seasonal_analysis = calculate_seasonal_patterns(tenant, branch_id)
        benchmarks = calculate_internal_benchmarks(tenant, branch_id)

        return Response({
            'business_kpis': business_kpis,
            'seasonal_analysis': seasonal_analysis,
            'benchmarks': benchmarks,
            'recommendations': generate_recommendations(business_kpis)
        })


class PredictiveAnalyticsView(APIView):
    """Analisis predictivo basico"""
    permission_classes = [TenantPermissionByAction, HasFeaturePermission]
    required_feature = 'reports'
    permission_map = {
        'GET': 'reports_api.view_advanced_analytics',
    }

    def get(self, request):
        tenant = request.user.tenant
        branch_id = get_report_branch_id(request)

        return Response({
            'demand_forecast': predict_demand(tenant, branch_id),
            'revenue_forecast': predict_revenue(tenant, branch_id),
            'at_risk_clients': identify_at_risk_clients(tenant, branch_id),
            'growth_opportunities': identify_growth_opportunities(tenant, branch_id)
        })


def calculate_client_retention(tenant, days, branch_id=None):
    """Calcular métricas de retención de clientes"""
    start_date = timezone.now() - timedelta(days=days)
    
    client_filter = {'tenant': tenant, 'last_visit__gte': start_date}
    new_client_filter = {'tenant': tenant, 'created_at__gte': start_date}
    recurring_filter = {'tenant': tenant, 'client_appointments__date_time__gte': start_date}
    
    if branch_id:
        client_filter['client_appointments__branch_id'] = branch_id
        new_client_filter['client_appointments__branch_id'] = branch_id
        recurring_filter['client_appointments__branch_id'] = branch_id
        
    # Clientes activos en el período
    active_clients = Client.objects.filter(**client_filter).distinct().count()
    
    # Clientes nuevos
    new_clients = Client.objects.filter(**new_client_filter).distinct().count()
    
    # Clientes recurrentes (más de 1 cita)
    recurring_clients = Client.objects.filter(**recurring_filter).annotate(
        appointment_count=Count('client_appointments')
    ).filter(appointment_count__gt=1).distinct().count()
    
    # Tasa de retención
    retention_rate = (recurring_clients / active_clients * 100) if active_clients > 0 else 0
    
    return {
        'active_clients': active_clients,
        'new_clients': new_clients,
        'recurring_clients': recurring_clients,
        'retention_rate': round(retention_rate, 2)
    }


def calculate_employee_performance(tenant, days, branch_id=None):
    """Análisis de rendimiento de empleados"""
    start_date = timezone.now() - timedelta(days=days)
    
    employee_filter = {'tenant': tenant, 'is_active': True}
    if branch_id:
        employee_filter['branch_id'] = branch_id
        
    employees = Employee.objects.filter(**employee_filter)
    performance_data = []
    
    for emp in employees:
        # Ventas del empleado
        sales_filter = {'employee': emp, 'date_time__gte': start_date}
        if branch_id:
            sales_filter['branch_id'] = branch_id
            
        sales = Sale.objects.filter(**sales_filter)
        
        # Citas del empleado
        appointments_filter = {'stylist': emp.user, 'date_time__gte': start_date}
        if branch_id:
            appointments_filter['branch_id'] = branch_id
            
        appointments = Appointment.objects.filter(**appointments_filter)
        
        total_sales = sales.aggregate(total=Sum('total'))['total'] or 0
        total_appointments = appointments.count()
        completed_appointments = appointments.filter(status='completed').count()
        
        # Tasa de conversión
        conversion_rate = (completed_appointments / total_appointments * 100) if total_appointments > 0 else 0
        
        # Promedio por cita
        avg_per_appointment = (total_sales / completed_appointments) if completed_appointments > 0 else 0
        
        performance_data.append({
            'employee_name': emp.user.full_name or emp.user.email,
            'total_sales': float(total_sales),
            'total_appointments': total_appointments,
            'completed_appointments': completed_appointments,
            'conversion_rate': round(conversion_rate, 2),
            'avg_per_appointment': round(float(avg_per_appointment), 2)
        })
    
    return sorted(performance_data, key=lambda x: x['total_sales'], reverse=True)


def calculate_service_trends(tenant, days, branch_id=None):
    """Análisis de tendencias de servicios"""
    start_date = timezone.now() - timedelta(days=days)
    
    services_filter = {
        'tenant': tenant,
        'appointments__date_time__gte': start_date
    }
    if branch_id:
        services_filter['appointments__branch_id'] = branch_id
        
    # Servicios más populares
    popular_services = Service.objects.filter(**services_filter).annotate(
        booking_count=Count('appointments'),
        revenue=Sum('appointments__sale__total')
    ).order_by('-booking_count')[:5]
    
    trends = []
    for service in popular_services:
        trends.append({
            'service_name': service.name,
            'bookings': service.booking_count,
            'revenue': float(service.revenue or 0),
            'avg_price': float(service.price)
        })
    
    return trends


def calculate_predictions(tenant, days, branch_id=None):
    """Predicciones básicas basadas en tendencias"""
    sales_filter = {
        'user__tenant': tenant,
        'date_time__gte': timezone.now() - timedelta(days=days*2)
    }
    if branch_id:
        sales_filter['branch_id'] = branch_id
        
    # Datos históricos
    historical_sales = Sale.objects.filter(**sales_filter).extra(
        select={'day': 'date(date_time)'}
    ).values('day').annotate(
        daily_total=Sum('total')
    ).order_by('day')
    
    if len(historical_sales) < 7:
        return {'message': 'Datos insuficientes para predicciones'}
    
    # Promedio de los últimos 7 días
    recent_avg = sum(float(day['daily_total']) for day in historical_sales[-7:]) / 7
    
    # Predicción simple para próximos 7 días
    next_week_prediction = recent_avg * 7
    
    return {
        'next_week_revenue': round(next_week_prediction, 2),
        'daily_average': round(recent_avg, 2),
        'confidence': 'medium'
    }


def calculate_clv(tenant, branch_id=None):
    """Customer Lifetime Value básico"""
    clients_filter = {'tenant': tenant, 'is_active': True}
    sales_filter = {'client__tenant': tenant}
    appointments_filter = {'client__tenant': tenant}
    
    if branch_id:
        clients_filter['client_appointments__branch_id'] = branch_id
        sales_filter['branch_id'] = branch_id
        appointments_filter['branch_id'] = branch_id
        
    clients = Client.objects.filter(**clients_filter).distinct()
    
    if not clients.exists():
        return 0
    
    # Promedio de gasto por cliente
    avg_spending = Sale.objects.filter(**sales_filter).aggregate(avg=Avg('total'))['avg'] or 0
    
    # Frecuencia promedio (citas por mes)
    avg_frequency = Appointment.objects.filter(**appointments_filter).count() / max(clients.count(), 1)
    
    # CLV básico (6 meses)
    clv = float(avg_spending) * avg_frequency * 6
    
    return round(clv, 2)


def calculate_arpu(tenant, branch_id=None):
    """Average Revenue Per User"""
    sales_filter = {'user__tenant': tenant}
    clients_filter = {'tenant': tenant, 'is_active': True}
    
    if branch_id:
        sales_filter['branch_id'] = branch_id
        clients_filter['client_appointments__branch_id'] = branch_id
        
    total_revenue = Sale.objects.filter(**sales_filter).aggregate(total=Sum('total'))['total'] or 0
    active_clients = Client.objects.filter(**clients_filter).distinct().count()
    
    arpu = float(total_revenue) / max(active_clients, 1)
    return round(arpu, 2)


def calculate_churn_rate(tenant, branch_id=None):
    """Tasa de abandono de clientes"""
    cutoff_date = timezone.now() - timedelta(days=60)
    
    clients_filter = {'tenant': tenant}
    inactive_filter = {'tenant': tenant, 'last_visit__lt': cutoff_date}
    
    if branch_id:
        clients_filter['client_appointments__branch_id'] = branch_id
        inactive_filter['client_appointments__branch_id'] = branch_id
        
    total_clients = Client.objects.filter(**clients_filter).distinct().count()
    inactive_clients = Client.objects.filter(**inactive_filter).distinct().count()
    
    churn_rate = (inactive_clients / max(total_clients, 1)) * 100
    return round(churn_rate, 2)


def calculate_growth_rate(tenant, branch_id=None):
    """Tasa de crecimiento mensual"""
    current_month = timezone.now().replace(day=1)
    last_month = (current_month - timedelta(days=1)).replace(day=1)
    
    current_filter = {'user__tenant': tenant, 'date_time__gte': current_month}
    last_filter = {'user__tenant': tenant, 'date_time__gte': last_month, 'date_time__lt': current_month}
    
    if branch_id:
        current_filter['branch_id'] = branch_id
        last_filter['branch_id'] = branch_id
        
    current_revenue = Sale.objects.filter(**current_filter).aggregate(total=Sum('total'))['total'] or 0
    last_revenue = Sale.objects.filter(**last_filter).aggregate(total=Sum('total'))['total'] or 0
    
    if last_revenue > 0:
        growth_rate = ((float(current_revenue) - float(last_revenue)) / float(last_revenue)) * 100
    else:
        growth_rate = 0
    
    return round(growth_rate, 2)


def calculate_capacity_utilization(tenant, branch_id=None):
    """Utilización de capacidad"""
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    
    appointments_filter = {
        'client__tenant': tenant,
        'date_time__date__gte': week_start,
        'status': 'completed'
    }
    if branch_id:
        appointments_filter['branch_id'] = branch_id
        
    total_appointments = Appointment.objects.filter(**appointments_filter).count()
    
    # Asumiendo 8 horas por día, 6 días por semana, citas de 30 min
    available_slots = 8 * 2 * 6
    
    utilization = (total_appointments / available_slots) * 100 if available_slots > 0 else 0
    return round(utilization, 2)


def calculate_seasonal_patterns(tenant, branch_id=None):
    """Análisis de patrones estacionales"""
    sales_filter = {'user__tenant': tenant}
    if branch_id:
        sales_filter['branch_id'] = branch_id
        
    daily_patterns = Sale.objects.filter(**sales_filter).extra(
        select={'weekday': 'EXTRACT(dow FROM date_time)'}
    ).values('weekday').annotate(
        avg_sales=Avg('total'),
        count=Count('id')
    ).order_by('weekday')
    
    day_names = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
    
    patterns = []
    for pattern in daily_patterns:
        day_index = int(pattern['weekday'])
        patterns.append({
            'day': day_names[day_index],
            'avg_sales': round(float(pattern['avg_sales'] or 0), 2),
            'transaction_count': pattern['count']
        })
    
    return patterns


def calculate_internal_benchmarks(tenant, branch_id=None):
    """Benchmarks internos"""
    sales_filter = {'user__tenant': tenant}
    employee_filter = {'tenant': tenant, 'sales__isnull': False}
    
    if branch_id:
        sales_filter['branch_id'] = branch_id
        employee_filter['branch_id'] = branch_id
        
    # Mejor mes del año
    best_month = Sale.objects.filter(**sales_filter).extra(
        select={'month': 'EXTRACT(month FROM date_time)'}
    ).values('month').annotate(
        total=Sum('total')
    ).order_by('-total').first()
    
    # Mejor empleado
    best_employee = Employee.objects.filter(**employee_filter).annotate(
        total_sales=Sum('sales__total')
    ).order_by('-total_sales').first()
    
    return {
        'best_month': best_month['month'] if best_month else None,
        'best_month_revenue': float(best_month['total']) if best_month else 0,
        'best_employee': best_employee.user.full_name if best_employee else None,
        'best_employee_sales': float(best_employee.total_sales) if best_employee else 0
    }


def generate_recommendations(kpis):
    """Generar recomendaciones basadas en KPIs"""
    recommendations = []
    
    if kpis['churn_rate'] > 20:
        recommendations.append({
            'type': 'retention',
            'message': 'Alta tasa de abandono. Implementar programa de fidelización.',
            'priority': 'high'
        })
    
    if kpis['capacity_utilization'] < 60:
        recommendations.append({
            'type': 'capacity',
            'message': 'Baja utilización. Considerar promociones o marketing.',
            'priority': 'medium'
        })
    
    if kpis['growth_rate'] < 0:
        recommendations.append({
            'type': 'growth',
            'message': 'Crecimiento negativo. Revisar estrategia de precios y servicios.',
            'priority': 'high'
        })
    
    return recommendations


def predict_demand(tenant, branch_id=None):
    """Predicción básica de demanda"""
    appointments_filter = {
        'client__tenant': tenant,
        'date_time__gte': timezone.now() - timedelta(days=30)
    }
    if branch_id:
        appointments_filter['branch_id'] = branch_id
        
    hourly_demand = Appointment.objects.filter(**appointments_filter).extra(
        select={'hour': 'EXTRACT(hour FROM date_time)'}
    ).values('hour').annotate(
        count=Count('id')
    ).order_by('hour')
    
    peak_hours = []
    for demand in hourly_demand:
        if demand['count'] > 0:
            peak_hours.append({
                'hour': f"{int(demand['hour'])}:00",
                'appointments': demand['count']
            })
    
    return sorted(peak_hours, key=lambda x: x['appointments'], reverse=True)[:5]


def predict_revenue(tenant, branch_id=None):
    """Predicción de ingresos"""
    sales_filter = {
        'user__tenant': tenant,
        'date_time__gte': timezone.now() - timedelta(days=30)
    }
    if branch_id:
        sales_filter['branch_id'] = branch_id
        
    daily_revenue = Sale.objects.filter(**sales_filter).extra(
        select={'day': 'date(date_time)'}
    ).values('day').annotate(
        total=Sum('total')
    ).order_by('day')
    
    if len(daily_revenue) < 7:
        return {'message': 'Datos insuficientes'}
    
    # Promedio de últimos 7 días
    recent_avg = sum(float(day['total']) for day in daily_revenue[-7:]) / 7
    
    return {
        'next_month_estimate': round(recent_avg * 30, 2),
        'weekly_average': round(recent_avg * 7, 2),
        'daily_average': round(recent_avg, 2)
    }


def identify_at_risk_clients(tenant, branch_id=None):
    """Identificar clientes en riesgo de abandono"""
    risk_period_start = timezone.now() - timedelta(days=60)
    risk_period_end = timezone.now() - timedelta(days=30)
    
    clients_filter = {
        'tenant': tenant,
        'last_visit__gte': risk_period_start,
        'last_visit__lte': risk_period_end,
        'is_active': True
    }
    if branch_id:
        clients_filter['client_appointments__branch_id'] = branch_id
        
    at_risk = Client.objects.filter(**clients_filter).distinct().values('full_name', 'email', 'phone', 'last_visit')[:10]
    
    return list(at_risk)


def identify_growth_opportunities(tenant, branch_id=None):
    """Identificar oportunidades de crecimiento"""
    opportunities = []
    
    # Servicios con baja demanda pero alta rentabilidad
    services_filter = {
        'tenant': tenant,
        'price__gt': 50
    }
    if branch_id:
        services_filter['appointments__branch_id'] = branch_id
        
    underperforming_services = Service.objects.filter(**services_filter).annotate(
        booking_count=Count('appointments')
    ).filter(booking_count__lt=5)
    
    if underperforming_services.exists():
        opportunities.append({
            'type': 'service_promotion',
            'message': f'{underperforming_services.count()} servicios premium necesitan promoción',
            'action': 'Crear campaña de marketing para servicios de alto valor'
        })
    
    # Horarios con baja ocupación
    appointments_filter = {'client__tenant': tenant}
    if branch_id:
        appointments_filter['branch_id'] = branch_id
        
    low_demand_hours = Appointment.objects.filter(**appointments_filter).extra(
        select={'hour': 'EXTRACT(hour FROM date_time)'}
    ).values('hour').annotate(
        count=Count('id')
    ).filter(count__lt=3)
    
    if low_demand_hours.exists():
        opportunities.append({
            'type': 'schedule_optimization',
            'message': f'{low_demand_hours.count()} horarios con baja demanda',
            'action': 'Ofrecer descuentos en horarios de baja demanda'
        })
    
    return opportunities
