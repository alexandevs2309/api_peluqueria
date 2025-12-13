from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Employee

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def employee_pending_payments(request, employee_id):
    """Endpoint para obtener pagos pendientes de un empleado"""
    try:
        employee = Employee.objects.get(id=employee_id, tenant=request.user.tenant)
        
        # Buscar ventas pendientes
        from apps.pos_api.models import Sale
        pending_sales = Sale.objects.filter(
            employee=employee,
            status='completed',
            period__isnull=True
        ).order_by('date_time')
        
        sales_data = []
        total_amount = 0
        
        for sale in pending_sales:
            if employee.salary_type == 'commission':
                amount = float(sale.total) * float(employee.commission_percentage) / 100
            elif employee.salary_type == 'mixed':
                amount = float(sale.total) * float(employee.commission_percentage) / 100
            else:
                amount = 0
            
            sales_data.append({
                'sale_id': sale.id,
                'date': sale.date_time.isoformat(),
                'total': float(sale.total),
                'commission_amount': round(amount, 2)
            })
            total_amount += amount
        
        return Response({
            'employee_id': employee.id,
            'employee_name': employee.user.full_name or employee.user.email,
            'salary_type': employee.salary_type or 'commission',
            'commission_rate': float(employee.commission_percentage or 40),
            'pending_sales': sales_data,
            'sale_ids': [s['sale_id'] for s in sales_data],
            'total_amount': round(total_amount, 2),
            'count': len(sales_data)
        })
        
    except Employee.DoesNotExist:
        return Response({'error': 'Empleado no encontrado'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)