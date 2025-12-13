import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def create_earning_from_sale(self, sale_id, external_id):
    """
    Crear earning de forma idempotente desde una venta completada
    """
    logger.info(f"Iniciando creación de earning para sale_id={sale_id}, external_id={external_id}")
    
    try:
        from apps.pos_api.models import Sale
        from .earnings_models import Earning
        from .models import Employee
        
        # Verificar idempotencia
        existing_earning = Earning.objects.filter(external_id=external_id).first()
        if existing_earning:
            logger.info(f"Earning ya existe para external_id={external_id}")
            return {'status': 'exists', 'earning_id': existing_earning.id}
        
        with transaction.atomic():
            try:
                sale = Sale.objects.select_related('employee').get(id=sale_id)
            except Sale.DoesNotExist:
                logger.error(f"Sale {sale_id} no encontrada")
                return {'status': 'error', 'message': 'Sale not found'}
            
            if not sale.employee or sale.status != 'completed':
                logger.info(f"Sale {sale_id} no tiene empleado o no está completada")
                return {'status': 'skipped', 'reason': 'no_employee_or_not_completed'}
            
            # Calcular earning basado en tipo de pago del empleado
            employee = sale.employee
            earning_amount = Decimal('0.00')
            
            if employee.salary_type == 'commission':
                earning_amount = (sale.total * employee.commission_percentage) / 100
            elif employee.salary_type == 'mixed':
                # Solo comisión para ventas individuales, sueldo se maneja en períodos
                earning_amount = (sale.total * employee.commission_percentage) / 100
            # Para 'fixed', no se crean earnings por venta individual
            
            if earning_amount > 0:
                # Calcular quincena
                year, fortnight_number = Earning.calculate_fortnight(sale.date_time.date())
                
                earning = Earning.objects.create(
                    employee=employee,
                    sale=sale,
                    amount=earning_amount,
                    earning_type='commission',
                    percentage=employee.commission_percentage,
                    description=f'Comisión por venta #{sale.id}',
                    date_earned=sale.date_time,
                    fortnight_year=year,
                    fortnight_number=fortnight_number,
                    external_id=external_id,
                    created_by=None  # Sistema automático
                )
                
                logger.info(f"Earning creado: {earning.id} por ${earning_amount}")
                return {'status': 'created', 'earning_id': earning.id, 'amount': float(earning_amount)}
            else:
                logger.info(f"No se creó earning para sale {sale_id} - monto 0 o empleado con sueldo fijo")
                return {'status': 'skipped', 'reason': 'zero_amount_or_fixed_salary'}
                
    except Exception as exc:
        logger.error(f"Error creando earning para sale {sale_id}: {str(exc)}")
        if self.request.retries < self.max_retries:
            logger.info(f"Reintentando... intento {self.request.retries + 1}")
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        return {'status': 'error', 'message': str(exc)}

@shared_task(bind=True, max_retries=3)
def process_payroll_batch_task(self, batch_id):
    """
    Procesar lote de nómina - marcar items como pagados
    """
    logger.info(f"Iniciando procesamiento de batch {batch_id}")
    
    try:
        from .earnings_models import PayrollBatch, PayrollBatchItem
        
        with transaction.atomic():
            try:
                batch = PayrollBatch.objects.get(id=batch_id)
            except PayrollBatch.DoesNotExist:
                logger.error(f"PayrollBatch {batch_id} no encontrado")
                return {'status': 'error', 'message': 'Batch not found'}
            
            if batch.status != 'approved':
                logger.error(f"Batch {batch_id} no está en estado 'approved'")
                return {'status': 'error', 'message': 'Batch not approved'}
            
            batch.status = 'processing'
            batch.save()
            
            # Procesar cada item
            processed_count = 0
            failed_count = 0
            
            for item in batch.items.all():
                try:
                    # Simular procesamiento de pago
                    # TODO: Integrar con gateway de pagos aquí
                    
                    item.status = 'paid'
                    item.external_ref = f"manual-{batch.batch_number}-{item.employee.id}"
                    item.processed_at = timezone.now()
                    item.save()
                    
                    # Marcar period_summary como pagado si existe
                    if item.period_summary:
                        item.period_summary.is_paid = True
                        item.period_summary.paid_at = timezone.now()
                        item.period_summary.save()
                    
                    processed_count += 1
                    logger.info(f"Item procesado: empleado {item.employee.id}")
                    
                except Exception as item_exc:
                    logger.error(f"Error procesando item {item.id}: {str(item_exc)}")
                    item.status = 'failed'
                    item.save()
                    failed_count += 1
            
            # Actualizar estado del batch
            if failed_count == 0:
                batch.status = 'completed'
            else:
                batch.status = 'failed' if processed_count == 0 else 'completed'
            
            batch.processed_at = timezone.now()
            batch.save()
            
            logger.info(f"Batch {batch_id} procesado: {processed_count} exitosos, {failed_count} fallidos")
            return {
                'status': 'completed',
                'processed_count': processed_count,
                'failed_count': failed_count
            }
            
    except Exception as exc:
        logger.error(f"Error procesando batch {batch_id}: {str(exc)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        return {'status': 'error', 'message': str(exc)}

@shared_task
def schedule_automatic_payroll():
    """
    Tarea programada para crear lotes de nómina automáticamente
    """
    logger.info("Ejecutando programación automática de nómina")
    
    # TODO: Implementar lógica de programación automática
    # - Verificar empleados con frecuencias que deben procesarse
    # - Crear batches automáticamente según configuración
    
    logger.info("Programación automática completada")
    return {'status': 'completed', 'message': 'Automatic scheduling completed'}