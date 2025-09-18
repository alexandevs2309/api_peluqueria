from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.pos_api.models import CashRegister

class Command(BaseCommand):
    help = 'Close old cash registers that are still open'

    def handle(self, *args, **options):
        today = timezone.localdate()
        
        # Cerrar cajas abiertas de días anteriores
        old_registers = CashRegister.objects.filter(
            is_open=True,
            opened_at__date__lt=today
        )
        
        count = old_registers.count()
        old_registers.update(
            is_open=False,
            closed_at=timezone.now(),
            final_cash=0
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully closed {count} old cash registers')
        )