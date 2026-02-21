# Agregar a apps/billing_api/tasks.py

from celery import shared_task
from apps.billing_api.metrics import FinancialMetrics
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def calculate_daily_mrr(self):
    """
    Calcular MRR diario y verificar caídas
    Ejecuta cada 6 horas
    """
    try:
        mrr = FinancialMetrics.calculate_mrr()
        FinancialMetrics.check_mrr_drop()
        
        logger.info(f"MRR calculated: {mrr}")
        
        return {
            'status': 'success',
            'mrr': float(mrr),
        }
        
    except Exception as e:
        logger.error(f"Error calculating MRR: {str(e)}")
        raise self.retry(exc=e, countdown=300)
