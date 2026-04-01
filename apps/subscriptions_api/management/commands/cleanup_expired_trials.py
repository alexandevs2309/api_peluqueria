from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.tenants_api.models import Tenant

class Command(BaseCommand):
    help = 'Normaliza tenants con trial expirado al estado suspendido/inactivo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué se haría sin ejecutar cambios',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = timezone.now().date()
        
        # Encontrar tenants con trial expirado
        expired_tenants = Tenant.objects.filter(
            subscription_status='trial',
            trial_end_date__lt=today,
            is_active=True
        )
        
        count = expired_tenants.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Se desactivarían {count} tenants expirados')
            )
            for tenant in expired_tenants:
                self.stdout.write(f'  - {tenant.name} (expiró: {tenant.trial_end_date})')
        else:
            updated = 0
            for tenant in expired_tenants:
                if tenant.sync_subscription_state(save=True):
                    updated += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'Normalizados {updated} de {count} tenants expirados')
            )
