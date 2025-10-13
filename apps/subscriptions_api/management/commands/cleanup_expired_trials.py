from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.tenants_api.models import Tenant
from apps.auth_api.models import User

class Command(BaseCommand):
    help = 'Desactivar cuentas con planes FREE expirados'

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
            # Desactivar tenants expirados
            expired_tenants.update(
                is_active=False,
                subscription_status='cancelled'
            )
            
            # Desactivar usuarios de esos tenants
            User.objects.filter(
                tenant__in=expired_tenants,
                is_active=True
            ).update(is_active=False)
            
            self.stdout.write(
                self.style.SUCCESS(f'Desactivados {count} tenants expirados')
            )