import logging
import uuid
from decimal import Decimal
from datetime import date, timedelta
from django.db import transaction
from apps.employees_api.earnings_models import Earning

logger = logging.getLogger(__name__)

def _update_active_settlement(employee, earning):
    """Recalcular settlement activo tras crear earning"""
    from apps.payroll_api.models import PayrollSettlement
    from apps.payroll_api.services import PayrollSettlementService
    
    logger.info(f"Iniciando actualización de settlement para empleado {employee.id}")
    
    try:
        # Calcular período actual basado en fecha del earning
        earning_date = earning.date_earned.date()
        year = earning_date.year
        month = earning_date.month
        day = earning_date.day
        
        logger.info(f"Fecha earning: {earning_date}, calculando período...")
        
        # Determinar índice de quincena
        fortnight_in_month = 1 if day <= 15 else 2
        period_index = (month - 1) * 2 + fortnight_in_month
        
        logger.info(f"Período calculado: {year}/{period_index}")
        
        # Calcular fechas del período
        if fortnight_in_month == 1:
            period_start = date(year, month, 1)
            period_end = date(year, month, 15)
        else:
            period_start = date(year, month, 16)
            # Último día del mes
            if month == 12:
                period_end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                period_end = date(year, month + 1, 1) - timedelta(days=1)
        
        # Buscar o crear settlement para este período
        settlement, created = PayrollSettlement.objects.get_or_create(
            employee=employee,
            period_year=year,
            period_index=period_index,
            frequency='biweekly',
            defaults={
                'settlement_id': uuid.uuid4(),
                'tenant': employee.tenant,
                'period_start': period_start,
                'period_end': period_end,
                'status': 'OPEN'
            }
        )
        
        logger.info(f"Settlement {'creado' if created else 'encontrado'}: {settlement.settlement_id}")
        
        # Recalcular si está abierto o listo
        if settlement.status in ['OPEN', 'READY']:
            logger.info(f"Recalculando settlement {settlement.settlement_id}...")
            # Recalcular usando servicio existente
            service = PayrollSettlementService()
            settlement = service.calculate_settlement(settlement)
            
            logger.info(f"Settlement recalculado - Gross: {settlement.gross_amount}")
            
            # Marcar como listo si tiene montos
            if settlement.gross_amount > 0:
                settlement.status = 'READY'
                settlement.save()
                logger.info(f"Settlement marcado como READY")
        else:
            logger.info(f"Settlement no se puede recalcular, status: {settlement.status}")
                
    except Exception as e:
        # Log error pero no fallar la venta
        logger.error(f"Error actualizando settlement para empleado {employee.id}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

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
                # CORRECCIÓN: Almacenar monto bruto de venta, NO comisión pre-calculada
                earning_amount = detail.price * detail.quantity
            elif employee.salary_type == 'mixed':
                # Solo comisión para ventas individuales, sueldo se maneja en períodos
                earning_amount = detail.price * detail.quantity
            # Para 'fixed', no se crean earnings por venta individual
            
            if earning_amount > 0:
                logger.info(f"🔍 CREANDO EARNING - Sale: {sale.id}, Detail: {detail.id}, Amount: ${earning_amount}, Employee: {employee.user.email} ({employee.commission_percentage}%)")
                
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
                
                logger.info(f"✅ EARNING CREADO - ID: {earning.id}, Amount: ${earning.amount}, External: {external_id}")
                
                earnings_created.append({
                    'earning_id': earning.id,
                    'amount': float(earning_amount),
                    'external_id': external_id
                })
                
                logger.info(f"Earning creado: {earning.id} por ${earning_amount}")
                
                # Actualizar settlement inmediatamente
                _update_active_settlement(employee, earning)
        
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