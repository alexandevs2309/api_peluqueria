from celery import shared_task
from django.utils import timezone
from apps.pos_api.models import CashRegister
from apps.tenants_api.models import Tenant


@shared_task
def auto_close_old_cash_registers():
    """
    Tarea Celery diaria que cierra automáticamente las cajas que quedaron
    abiertas de días anteriores. Evita que queden cajas abiertas indefinidamente.
    """
    today = timezone.localdate()
    total_count = 0

    try:
        for tenant in Tenant.objects.filter(is_active=True, deleted_at__isnull=True):
            old_registers = CashRegister.objects.filter(
                tenant=tenant,
                is_open=True,
                opened_at__date__lt=today
            )
            count = old_registers.count()
            if count > 0:
                old_registers.update(
                    is_open=False,
                    closed_at=timezone.now(),
                    final_cash=0
                )
                total_count += count
    except Exception as e:
        return f"Error: {str(e)}"

    return f"Closed {total_count} old cash registers"
