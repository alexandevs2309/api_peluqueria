from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Sale, SaleDetail
from .handlers import create_earnings_from_sale
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Sale)
def auto_create_earnings_on_sale(sender, instance, created, **kwargs):
    """
    Crear earnings cuando se completa una venta
    """
    if instance.status == 'completed' and instance.employee and instance.details.exists():
        try:
            result = create_earnings_from_sale(instance)
            logger.info(f"Auto-earnings for sale {instance.id}: {result}")
        except Exception as e:
            logger.error(f"Error creating auto-earnings for sale {instance.id}: {e}")

@receiver(post_save, sender=SaleDetail)
def auto_create_earnings_on_detail(sender, instance, created, **kwargs):
    """
    Crear earnings cuando se agrega un detalle a venta completada
    """
    sale = instance.sale
    if sale.status == 'completed' and sale.employee and not sale.earnings_generated:
        try:
            result = create_earnings_from_sale(sale)
            logger.info(f"Auto-earnings for sale {sale.id} after detail: {result}")
        except Exception as e:
            logger.error(f"Error creating auto-earnings for sale {sale.id}: {e}")