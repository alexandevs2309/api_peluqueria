import logging
from decimal import Decimal
from django.db import transaction
from apps.employees_api.earnings_models import Earning

logger = logging.getLogger(__name__)

def create_earnings_from_sale(sale):
    """
    Crear earnings de forma idempotente desde una venta completada
    """
    # Validar precondiciones
    if not sale.employee or sale.status != 'completed':
        logger.debug(f"Sale {sale.id} no tiene empleado o no está completada")
        return {'status': 'skipped', 'reason': 'no_employee_or_not_completed'}
    
    # Validar que no se hayan generado earnings ya
    if sale.earnings_generated:
        logger.debug(f"Sale {sale.id} ya tiene earnings generados")
        return {'status': 'skipped', 'reason': 'earnings_already_generated'}
    
    # Validar que no estén revertidos
    if sale.earnings_reverted:
        logger.debug(f"Sale {sale.id} tiene earnings revertidos")
        return {'status': 'skipped', 'reason': 'earnings_reverted'}
    
    employee = sale.employee
    earnings_created = []
    
    with transaction.atomic():
        # Procesar cada detalle de la venta
        for detail in sale.details.all():
            external_id = f"sale-{sale.id}-item-{detail.id}"
            
            # Verificar idempotencia
            existing_earning = Earning.objects.filter(external_id=external_id).first()
            if existing_earning:
                logger.debug(f"Earning ya existe para external_id={external_id}")
                continue
            
            # Calcular earning basado en tipo de pago del empleado
            earning_amount = Decimal('0.00')
            
            if employee.salary_type == 'commission':
                earning_amount = (detail.price * employee.commission_percentage) / 100
            elif employee.salary_type == 'mixed':
                # Solo comisión para ventas individuales, sueldo se maneja en períodos
                earning_amount = (detail.price * employee.commission_percentage) / 100
            # Para 'fixed', no se crean earnings por venta individual
            
            if earning_amount > 0:
                earning = Earning.objects.create(
                    employee=employee,
                    sale=sale,
                    amount=earning_amount,
                    earning_type='commission',
                    percentage=employee.commission_percentage,
                    description=f'Comisión por {detail.name} - Venta #{sale.id}',
                    date_earned=sale.date_time,
                    external_id=external_id,
                    created_by=None  # Sistema automático
                )
                
                earnings_created.append({
                    'earning_id': earning.id,
                    'amount': float(earning_amount),
                    'external_id': external_id
                })
                
                logger.info(f"Earning creado: {earning.id} por ${earning_amount}")
        
        # Marcar que se generaron earnings
        if earnings_created:
            sale.mark_earnings_generated()
    
    result = {
        'status': 'created' if earnings_created else 'skipped',
        'earnings_created': len(earnings_created),
        'earnings': earnings_created
    }
    
    logger.info(f"Earnings processing result for sale {sale.id}: {result}")
    return result