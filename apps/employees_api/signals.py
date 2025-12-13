import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.pos_api.models import Sale

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Sale)
def create_earning_on_sale_completion(sender, instance, created, **kwargs):
    """
    Signal para crear earning automáticamente cuando se completa una venta
    """
    # Solo procesar si la venta está completada y tiene empleado
    if instance.status == 'completed' and instance.employee:
        from apps.pos_api.handlers import create_earnings_from_sale
        
        logger.info(f"Creando earnings para sale {instance.id}")
        result = create_earnings_from_sale(instance)
        logger.info(f"Resultado: {result}")
    else:
        logger.debug(f"Sale {instance.id} no cumple condiciones para crear earning")