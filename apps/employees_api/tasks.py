from celery import shared_task
from django.db.models import Sum, Count
from .earnings_models import Earning, FortnightSummary
from .models import Employee

@shared_task
def generate_fortnight_summaries(year, fortnight_number):
    """Genera resúmenes de quincena para todos los empleados"""
    
    employees = Employee.objects.filter(is_active=True)
    created_count = 0
    
    for employee in employees:
        # Obtener ganancias de la quincena
        earnings = Earning.objects.filter(
            employee=employee,
            fortnight_year=year,
            fortnight_number=fortnight_number
        )
        
        if not earnings.exists():
            continue
            
        # Calcular totales
        totals = earnings.aggregate(
            total_earnings=Sum('amount'),
            total_services=Count('id', filter=models.Q(earning_type='service')),
            total_commissions=Sum('amount', filter=models.Q(earning_type='commission')),
            total_tips=Sum('amount', filter=models.Q(earning_type='tip'))
        )
        
        # Crear o actualizar resumen
        summary, created = FortnightSummary.objects.get_or_create(
            employee=employee,
            fortnight_year=year,
            fortnight_number=fortnight_number,
            defaults={
                'total_earnings': totals['total_earnings'] or 0,
                'total_services': totals['total_services'] or 0,
                'total_commissions': totals['total_commissions'] or 0,
                'total_tips': totals['total_tips'] or 0,
            }
        )
        
        if not created:
            # Actualizar resumen existente
            summary.total_earnings = totals['total_earnings'] or 0
            summary.total_services = totals['total_services'] or 0
            summary.total_commissions = totals['total_commissions'] or 0
            summary.total_tips = totals['total_tips'] or 0
            summary.save()
            
        created_count += 1
    
    return f"Generados {created_count} resúmenes para la quincena {fortnight_number}/{year}"

@shared_task
def create_earning_from_sale(sale_id, employee_id, percentage=50):
    """Crea ganancia automática cuando se completa una venta"""
    from apps.pos_api.models import Sale
    
    try:
        sale = Sale.objects.get(id=sale_id)
        employee = Employee.objects.get(id=employee_id)
        
        # Calcular ganancia (porcentaje de la venta)
        earning_amount = (sale.total * percentage) / 100
        
        # Crear ganancia
        earning = Earning.objects.create(
            employee=employee,
            sale=sale,
            amount=earning_amount,
            earning_type='commission',
            percentage=percentage,
            description=f"Comisión por venta #{sale.id}",
            created_by=sale.user
        )
        
        return f"Ganancia creada: ${earning_amount} para {employee}"
        
    except Exception as e:
        return f"Error creando ganancia: {str(e)}"

@shared_task
def notify_new_earning(earning_id):
    """Notifica al empleado sobre nueva ganancia"""
    try:
        earning = Earning.objects.get(id=earning_id)
        
        # TODO: Implementar notificación real (WebSocket, email, etc.)
        # Por ahora solo log
        print(f"🎉 Nueva ganancia para {earning.employee}: ${earning.amount}")
        
        return f"Notificación enviada a {earning.employee}"
        
    except Exception as e:
        return f"Error enviando notificación: {str(e)}"