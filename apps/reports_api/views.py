from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db.models import Sum, Count, Avg, F
from django.db import models
from django.utils import timezone
from datetime import timedelta, datetime
from apps.pos_api.models import Sale
from apps.appointments_api.models import Appointment
from apps.employees_api.models import Employee
from apps.clients_api.models import Client
from apps.inventory_api.models import Product

class ReportsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        report_type = request.query_params.get('type', 'dashboard')  # Default a dashboard
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Fechas por defecto (último mes)
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        else:
            try:
                start_date = datetime.fromisoformat(start_date)
            except ValueError:
                start_date = timezone.now() - timedelta(days=30)
            
        if not end_date:
            end_date = timezone.now()
        else:
            try:
                end_date = datetime.fromisoformat(end_date)
            except ValueError:
                end_date = timezone.now()

        if report_type == 'dashboard':
            return self.dashboard_report(start_date, end_date)
        elif report_type == 'admin_dashboard':
            return self.admin_dashboard_report()
        elif report_type == 'chart_data':
            return self.get_real_chart_data()
        elif report_type == 'subscription_revenue':
            return self.subscription_revenue_report()
        elif report_type == 'tenant_growth':
            return self.tenant_growth_report()
        elif report_type == 'churn_analysis':
            return self.churn_analysis_report()
        elif report_type == 'plan_usage':
            return self.plan_usage_report()
        elif report_type == 'user_activity':
            return self.user_activity_report()
        elif report_type == 'sales':
            return self.sales_report(start_date, end_date)
        elif report_type == 'appointments':
            return self.appointments_report(start_date, end_date)
        elif report_type == 'employees':
            return self.employees_report(start_date, end_date)
        elif report_type == 'inventory':
            return self.inventory_report()
        else:
            # Si no se especifica tipo o es inválido, devolver dashboard por defecto
            return self.dashboard_report(start_date, end_date)

    def sales_report(self, start_date, end_date):
        sales = Sale.objects.filter(
            date_time__range=[start_date, end_date]
        )
        
        total_sales = sales.aggregate(
            total_amount=Sum('total'),
            total_count=Count('id'),
            avg_sale=Avg('total')
        )
        
        # Ventas por método de pago
        payment_methods = sales.values('payment_method').annotate(
            total=Sum('total'),
            count=Count('id')
        )
        
        # Ventas por empleado
        sales_by_employee = sales.values(
            'user__full_name'
        ).annotate(
            total=Sum('total'),
            count=Count('id')
        ).order_by('-total')
        
        # Ventas por día
        daily_sales = sales.extra(
            select={'day': 'DATE(date_time)'}
        ).values('day').annotate(
            total=Sum('total'),
            count=Count('id')
        ).order_by('day')
        
        return Response({
            'period': {'start': start_date, 'end': end_date},
            'summary': total_sales,
            'by_payment_method': list(payment_methods),
            'by_employee': list(sales_by_employee),
            'daily_sales': list(daily_sales)
        })

    def appointments_report(self, start_date, end_date):
        appointments = Appointment.objects.filter(
            date_time__range=[start_date, end_date]
        )
        
        summary = appointments.aggregate(
            total_count=Count('id')
        )
        
        # Por estado
        by_status = appointments.values('status').annotate(
            count=Count('id')
        )
        
        # Por estilista
        by_stylist = appointments.values(
            'stylist__full_name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Por servicio
        by_service = appointments.values(
            'service__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        return Response({
            'period': {'start': start_date, 'end': end_date},
            'summary': summary,
            'by_status': list(by_status),
            'by_stylist': list(by_stylist),
            'by_service': list(by_service)
        })

    def employees_report(self, start_date, end_date):
        employees = Employee.objects.filter(is_active=True)
        
        employee_stats = []
        for employee in employees:
            appointments = Appointment.objects.filter(
                stylist=employee.user,
                date_time__range=[start_date, end_date]
            )
            
            sales = Sale.objects.filter(
                user=employee.user,
                date_time__range=[start_date, end_date]
            )
            
            employee_stats.append({
                'name': employee.user.full_name,
                'specialty': employee.specialty,
                'appointments_count': appointments.count(),
                'completed_appointments': appointments.filter(status='completed').count(),
                'sales_count': sales.count(),
                'total_sales': sales.aggregate(total=Sum('total'))['total'] or 0
            })
        
        return Response({
            'period': {'start': start_date, 'end': end_date},
            'employees': employee_stats
        })

    def dashboard_report(self, start_date, end_date):
        # Resumen general para dashboard
        today = timezone.now().date()
        
        # Ventas de hoy
        today_sales = Sale.objects.filter(date_time__date=today)
        today_revenue = today_sales.aggregate(total=Sum('total'))['total'] or 0
        
        # Citas de hoy
        today_appointments = Appointment.objects.filter(date_time__date=today)
        
        # Clientes totales
        total_clients = Client.objects.filter(is_active=True).count()
        
        # Empleados activos
        active_employees = Employee.objects.filter(is_active=True).count()
        
        # Productos con stock bajo
        low_stock_products = Product.objects.filter(
            stock__lte=F('min_stock'),
            is_active=True
        ).count()
        
        return Response({
            'today': {
                'revenue': float(today_revenue),
                'sales_count': today_sales.count(),
                'appointments_count': today_appointments.count(),
                'completed_appointments': today_appointments.filter(status='completed').count()
            },
            'totals': {
                'clients': total_clients,
                'employees': active_employees,
                'low_stock_products': low_stock_products
            }
        })

    def inventory_report(self):
        # Productos con stock bajo
        low_stock = Product.objects.filter(
            stock__lte=F('min_stock'),
            is_active=True
        )
        
        # Productos más vendidos (necesitaría implementar tracking de ventas de productos)
        total_products = Product.objects.filter(is_active=True).count()
        
        return Response({
            'low_stock_products': [{
                'id': p.id,
                'name': p.name,
                'current_stock': p.stock,
                'min_stock': p.min_stock,
                'sku': p.sku
            } for p in low_stock],
            'total_products': total_products,
            'low_stock_count': low_stock.count()
        })

    def admin_dashboard_report(self):
        from apps.tenants_api.models import Tenant
        from apps.subscriptions_api.models import UserSubscription
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        today = timezone.now().date()
        
        # Métricas SaaS
        active_tenants = Tenant.objects.filter(is_active=True).count()
        total_users = User.objects.count()
        active_subscriptions = UserSubscription.objects.filter(is_active=True).count()
        
        # Ingresos por suscripciones activas
        subscription_revenue = UserSubscription.objects.filter(
            is_active=True
        ).aggregate(
            total=Sum('plan__price')
        )['total'] or 0
        
        return Response({
            'today': {
                'revenue': float(subscription_revenue),
                'new_tenants': Tenant.objects.filter(created_at__date=today).count(),
                'new_subscriptions': UserSubscription.objects.filter(start_date__date=today).count(),
                'active_users': User.objects.filter(last_login__date=today).count()
            },
            'totals': {
                'tenants': active_tenants,
                'users': total_users,
                'subscriptions': active_subscriptions,
                'revenue': float(subscription_revenue)
            }
        })

    def get_real_chart_data(self):
        try:
            from apps.subscriptions_api.models import UserSubscription, SubscriptionPlan
            from django.db.models import Count
            
            # Obtener todos los planes y sus nombres reales
            all_plans = SubscriptionPlan.objects.all()
            print(f'PLANES DISPONIBLES:')
            for plan in all_plans:
                print(f'  ID: {plan.id}, Nombre: "{plan.name}"')
            
            # Contar suscripciones por cada plan real
            plan_counts = {}
            for plan in all_plans:
                count = UserSubscription.objects.filter(plan=plan).count()
                plan_counts[plan.name] = count
                print(f'  Plan "{plan.name}": {count} suscripciones')
            
            # Mapear a los nombres específicos que quiere mostrar
            plan_data = {
                'free': 0,
                'Basic': 0,
                'Premium': 0,
                'Standar': 0,
                'Enterprice': 0
            }
            
            # Mapeo de nombres del backend a nombres del frontend
            name_mapping = {
                'free': 'free',
                'basic': 'Basic', 
                'Plan Basic': 'Basic',
                'premium': 'Premium',
                'Plan Premium': 'Premium', 
                'standard': 'Standar',
                'standar': 'Standar',
                'Plan Standar': 'Standar',
                'enterprise': 'Enterprice',
                'enterprice': 'Enterprice',
                'Plan Enterprice': 'Enterprice'
            }
            
            # Mapear nombres reales a nombres del frontend
            for plan_name, count in plan_counts.items():
                frontend_name = name_mapping.get(plan_name, None)
                if frontend_name and frontend_name in plan_data:
                    plan_data[frontend_name] = count
            
            print(f'PLAN DATA FINAL: {plan_data}')
            
            # Datos reales por mes basados en fechas de suscripción
            from django.db.models import Count
            from django.db.models.functions import Extract
            
            # Obtener suscripciones agrupadas por mes del año actual
            current_year = timezone.now().year
            monthly_subscriptions = UserSubscription.objects.filter(
                start_date__year=current_year
            ).annotate(
                month=Extract('start_date', 'month')
            ).values('month').annotate(
                count=Count('id')
            ).order_by('month')
            
            # Inicializar array con 12 meses en 0
            monthly_data = [0] * 12
            
            # Llenar con datos reales
            for item in monthly_subscriptions:
                month_index = item['month'] - 1  # Convertir mes (1-12) a índice (0-11)
                monthly_data[month_index] = item['count']
            
            return Response({
                'subscriptions_by_month': monthly_data,
                'month_labels': ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'],
                'plan_distribution': plan_data
            })
        except Exception as e:
            print(f'ERROR EN CHART DATA: {e}')
            return Response({
                'subscriptions_by_month': [0] * 12,
                'month_labels': ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'],
                'plan_distribution': {'free': 0, 'Basic': 0, 'Premium': 0, 'Standar': 0, 'Enterprice': 0}
            })

    def subscription_revenue_report(self):
        from apps.subscriptions_api.models import UserSubscription
        from django.db.models.functions import Extract
        
        current_year = timezone.now().year
        monthly_revenue = UserSubscription.objects.filter(
            start_date__year=current_year,
            is_active=True
        ).annotate(
            month=Extract('start_date', 'month')
        ).values('month').annotate(
            revenue=Sum('plan__price')
        ).order_by('month')
        
        revenue_data = [0] * 12
        for item in monthly_revenue:
            month_index = item['month'] - 1
            revenue_data[month_index] = float(item['revenue'] or 0)
        
        return Response({
            'monthly_revenue': revenue_data,
            'total_revenue': sum(revenue_data)
        })

    def tenant_growth_report(self):
        from apps.tenants_api.models import Tenant
        from django.db.models.functions import Extract
        
        current_year = timezone.now().year
        monthly_tenants = Tenant.objects.filter(
            created_at__year=current_year
        ).annotate(
            month=Extract('created_at', 'month')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        tenant_data = [0] * 12
        for item in monthly_tenants:
            month_index = item['month'] - 1
            tenant_data[month_index] = item['count']
        
        return Response({
            'monthly_tenants': tenant_data,
            'total_new_tenants': sum(tenant_data)
        })

    def churn_analysis_report(self):
        from apps.subscriptions_api.models import UserSubscription
        from apps.tenants_api.models import Tenant
        
        total_tenants = Tenant.objects.count()
        active_tenants = Tenant.objects.filter(is_active=True).count()
        inactive_tenants = total_tenants - active_tenants
        churn_rate = (inactive_tenants / total_tenants * 100) if total_tenants > 0 else 0
        
        return Response({
            'total_tenants': total_tenants,
            'active_tenants': active_tenants,
            'inactive_tenants': inactive_tenants,
            'churn_rate': round(churn_rate, 2)
        })

    def plan_usage_report(self):
        from apps.subscriptions_api.models import UserSubscription, SubscriptionPlan
        
        plan_usage = SubscriptionPlan.objects.annotate(
            active_subscriptions=Count('user_subscriptions', filter=models.Q(user_subscriptions__is_active=True))
        ).values('name', 'active_subscriptions')
        
        return Response({
            'plan_usage': list(plan_usage)
        })

    def user_activity_report(self):
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        active_today = User.objects.filter(last_login__date=today).count()
        active_week = User.objects.filter(last_login__date__gte=week_ago).count()
        total_users = User.objects.count()
        
        return Response({
            'active_today': active_today,
            'active_week': active_week,
            'total_users': total_users,
            'activity_rate': round((active_week / total_users * 100) if total_users > 0 else 0, 2)
        })

class SalesReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # Reporte detallado de ventas
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        employee_id = request.query_params.get('employee_id')
        
        sales = Sale.objects.all()
        
        if start_date:
            sales = sales.filter(date_time__gte=start_date)
        if end_date:
            sales = sales.filter(date_time__lte=end_date)
        if employee_id:
            sales = sales.filter(user_id=employee_id)
            
        sales_data = []
        for sale in sales.select_related('user', 'client'):
            sales_data.append({
                'id': sale.id,
                'date_time': sale.date_time,
                'employee': sale.user.full_name,
                'client': sale.client.full_name if sale.client else 'Cliente general',
                'total': float(sale.total),
                'payment_method': sale.payment_method,
                'items_count': sale.details.count()
            })
        
        return Response({
            'sales': sales_data,
            'total_amount': sum(s['total'] for s in sales_data),
            'count': len(sales_data)
        })