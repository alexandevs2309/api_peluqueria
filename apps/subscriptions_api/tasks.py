from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

@shared_task
def cleanup_expired_trials():
    """
    Tarea programada para limpiar cuentas con planes FREE expirados
    """
    try:
        call_command('cleanup_expired_trials')
        logger.info('Cleanup de trials expirados ejecutado exitosamente')
        return 'SUCCESS'
    except Exception as e:
        logger.error(f'Error en cleanup de trials: {str(e)}')
        return f'ERROR: {str(e)}'