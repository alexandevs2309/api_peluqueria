"""
Migración segura para introducir soft deletes
apps/utils/management/commands/migrate_soft_deletes.py
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.apps import apps


class Command(BaseCommand):
    help = 'Migra modelos existentes a soft delete de forma segura'
    
    # Modelos que deben migrar a soft delete
    MODELS_TO_MIGRATE = [
        ('payroll_api', 'PayrollCalculation'),
        ('payroll_api', 'PayrollPayment'),
        ('pos_api', 'Sale'),
        ('clients_api', 'Client'),
        ('employees_api', 'Employee'),
    ]
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la migración sin aplicar cambios',
        )
        parser.add_argument(
            '--model',
            type=str,
            help='Migra solo un modelo específico (formato: app.Model)',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        specific_model = options.get('model')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('MODO DRY-RUN: No se aplicarán cambios')
            )
        
        models_to_process = self.MODELS_TO_MIGRATE
        
        if specific_model:
            app_label, model_name = specific_model.split('.')
            models_to_process = [(app_label, model_name)]
        
        for app_label, model_name in models_to_process:
            self.migrate_model(app_label, model_name, dry_run)
    
    @transaction.atomic
    def migrate_model(self, app_label: str, model_name: str, dry_run: bool):
        """Migra un modelo específico a soft delete."""
        try:
            Model = apps.get_model(app_label, model_name)
        except LookupError:
            self.stdout.write(
                self.style.ERROR(f'Modelo {app_label}.{model_name} no encontrado')
            )
            return
        
        # Verificar si ya tiene campos de soft delete
        if not hasattr(Model, 'is_deleted'):
            self.stdout.write(
                self.style.ERROR(
                    f'{model_name} no tiene campos de soft delete. '
                    'Ejecuta primero las migraciones de Django.'
                )
            )
            return
        
        # Contar registros
        total_records = Model.all_objects.count()
        deleted_records = Model.all_objects.filter(is_deleted=True).count()
        active_records = total_records - deleted_records
        
        self.stdout.write(
            f'\n{model_name}:'
            f'\n  Total: {total_records}'
            f'\n  Activos: {active_records}'
            f'\n  Eliminados: {deleted_records}'
        )
        
        if not dry_run:
            # Asegurar que registros existentes no estén marcados como eliminados
            updated = Model.all_objects.filter(
                is_deleted__isnull=True
            ).update(is_deleted=False)
            
            if updated > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✅ {updated} registros marcados como activos'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ {model_name} migrado correctamente')
        )