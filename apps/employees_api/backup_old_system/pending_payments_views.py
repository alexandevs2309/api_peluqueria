"""
Endpoint para obtener ventas pendientes de pago por empleado
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum
from datetime import datetime, timedelta
from .models import Employee
from apps.pos_api.models import Sale


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pending_payments(request, employee_id):
    """
    GET /api/employees/{employee_id}/pending-payments/
    
    Retorna ventas pendientes de pago con sale_ids y montos calculados
    según la configuración del empleado (commission_rate, salary_type)
    """
    try:
        employee = Employee.objects.get(id=employee_id, tenant=request.user.tenant)
    except Employee.DoesNotExist:
        return Response({'error': 'Empleado no encontrado'}, status=404)
    
    # Obtener ventas completadas sin período asignado (no pagadas)
    pending_sales = Sale.objects.filter(
        employee=employee,
        status='completed',
        period__isnull=True  # No asignadas a ningún FortnightSummary pagado
    ).order_by('date_time')
    
    # Calcular monto por cada venta según configuración
    sales_data = []
    total_amount = 0
    
    for sale in pending_sales:
        # Calcular comisión según tipo de empleado
        if employee.salary_type == 'commission':
            amount = float(sale.total) * float(employee.commission_percentage) / 100
        elif employee.salary_type == 'mixed':
            # En mixto, solo comisión sobre ventas (sueldo fijo se paga aparte)
            amount = float(sale.total) * float(employee.commission_percentage) / 100
        else:  # fixed
            # Sueldo fijo no depende de ventas individuales
            amount = 0
        
        sales_data.append({
            'sale_id': sale.id,
            'date': sale.date_time.isoformat(),
            'total': float(sale.total),
            'commission_amount': round(amount, 2),
            'payment_method': sale.payment_method
        })
        total_amount += amount
    
    # Para sueldo fijo, calcular proporción de días trabajados
    if employee.salary_type in ['fixed', 'mixed']:
        # Calcular días trabajados en quincena actual
        today = datetime.now().date()
        day = today.day
        if day <= 15:
            days_worked = day
            total_days = 15
        else:
            days_worked = day - 15
            last_day = (datetime(today.year, today.month + 1, 1) - timedelta(days=1)).day
            total_days = last_day - 15
        
        # Salario quincenal proporcional
        monthly_salary = float(employee.contractual_monthly_salary or 0)
        fortnight_salary = monthly_salary / 2
        proportional_salary = (fortnight_salary / total_days) * days_worked
        
        if employee.salary_type == 'fixed':
            total_amount = proportional_salary
        else:  # mixed
            total_amount += proportional_salary
    
    return Response({
        'employee_id': employee.id,
        'employee_name': employee.user.full_name or employee.user.email,
        'salary_type': employee.salary_type,
        'commission_rate': float(employee.commission_percentage),
        'pending_sales': sales_data,
        'sale_ids': [s['sale_id'] for s in sales_data],
        'total_amount': round(total_amount, 2),
        'count': len(sales_data)
    })
