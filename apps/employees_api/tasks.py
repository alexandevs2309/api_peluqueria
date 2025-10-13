from celery import shared_task
from django.db.models import Sum, Count
from django.db import models
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
    from decimal import Decimal
    
    try:
        sale = Sale.objects.get(id=sale_id)
        employee = Employee.objects.get(id=employee_id)
        
        # Verificar que no existe ya una ganancia para esta venta
        existing_earning = Earning.objects.filter(sale=sale, employee=employee).first()
        if existing_earning:
            return f"Ganancia ya existe para venta #{sale_id}"
        
        # Calcular ganancia (porcentaje de la venta)
        earning_amount = (sale.total * Decimal(str(percentage))) / 100
        
        # Crear ganancia
        earning = Earning.objects.create(
            employee=employee,
            sale=sale,
            amount=earning_amount,
            earning_type='commission',
            percentage=Decimal(str(percentage)),
            description=f"Comisión por venta #{sale.id} - {sale.client.full_name if sale.client else 'Cliente anónimo'}",
            created_by=sale.user
        )
        
        # Notificar al empleado
        notify_new_earning.delay(earning.id)
        
        return f"Ganancia creada: ${earning_amount} para {employee}"
        
    except Exception as e:
        return f"Error creando ganancia: {str(e)}"

@shared_task
def notify_new_earning(earning_id):
    """Notifica al empleado sobre nueva ganancia"""
    try:
        earning = Earning.objects.get(id=earning_id)
        
        # Crear notificación en el sistema
        from apps.notifications_api.models import Notification, NotificationTemplate
        
        # Buscar template de ganancias o crear uno básico
        template, created = NotificationTemplate.objects.get_or_create(
            notification_type='earnings_available',
            type='push',
            defaults={
                'name': 'Nueva Ganancia',
                'subject': '💰 Nueva ganancia disponible',
                'body': 'Has ganado ${{amount}} por {{description}}. ¡Quincena actual: ${{fortnight_total}}!',
                'is_active': True
            }
        )
        
        # Calcular total de quincena actual
        current_year, current_fortnight = earning.fortnight_year, earning.fortnight_number
        fortnight_total = Earning.objects.filter(
            employee=earning.employee,
            fortnight_year=current_year,
            fortnight_number=current_fortnight
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        
        # Crear notificación
        notification = Notification.objects.create(
            recipient=earning.employee.user,
            template=template,
            subject=f'💰 Nueva ganancia: ${earning.amount}',
            message=f'Has ganado ${earning.amount} por {earning.description}. Quincena actual: ${fortnight_total}',
            metadata={
                'earning_id': earning.id,
                'amount': str(earning.amount),
                'fortnight_total': str(fortnight_total),
                'description': earning.description
            },
            priority='normal'
        )
        
        # Enviar notificación
        notification.send()
        
        return f"Notificación enviada a {earning.employee}: ${earning.amount}"
        
    except Exception as e:
        return f"Error enviando notificación: {str(e)}"