from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.pos_api.models import CashRegister
from apps.tenants_api.models import Tenant


class Command(BaseCommand):
    help = 'Close old cash registers that are still open'

    def handle(self, *args, **options):
        today = timezone.localdate()
        total_count = 0

        # Iterar por tenant para cerrar cajas antiguas de cada uno
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
            self.stderr.write(self.style.ERROR(f'Error updating registers: {str(e)}'))
            return

        self.stdout.write(
            self.style.SUCCESS(f'Successfully closed {total_count} old cash registers')
        )
