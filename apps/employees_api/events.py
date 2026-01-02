import redis
import json
import logging
from django.conf import settings
from decimal import Decimal

logger = logging.getLogger(__name__)

class EarningEventService:
    """Servicio para emitir eventos de earnings en tiempo real"""
    
    def __init__(self):
        self.redis_client = redis.Redis.from_url(
            settings.CACHES['default']['LOCATION'],
            decode_responses=True
        )
    
    def emit_earning_created(self, earning):
        """Emitir evento cuando se crea un earning"""
        try:
            event_data = {
                'type': 'EARNING_CREATED',
                'employee_id': earning.employee.id,
                'employee_name': earning.employee.user.full_name or earning.employee.user.email,
                'amount': float(earning.amount),
                'message': 'Tienes una nueva comisión disponible',
                'created_at': earning.created_at.isoformat(),
                'tenant_id': earning.employee.tenant.id
            }
            
            # Publicar en canal específico del tenant
            channel = f"tenant_{earning.employee.tenant.id}_earnings"
            self.redis_client.publish(channel, json.dumps(event_data))
            
            logger.info(f"Evento EARNING_CREATED emitido para empleado {earning.employee.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error emitiendo evento earning: {str(e)}")
            return False