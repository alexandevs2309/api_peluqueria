from django.core.management.base import BaseCommand
from apps.audit_api.utils import migrate_existing_logs

class Command(BaseCommand):
    help = 'Migrar logs de auditoría existentes al sistema unificado'

    def handle(self, *args, **options):
        migrated_count = migrate_existing_logs()
        self.stdout.write(
            self.style.SUCCESS(f'Se migraron exitosamente {migrated_count} logs de auditoría')
        )
