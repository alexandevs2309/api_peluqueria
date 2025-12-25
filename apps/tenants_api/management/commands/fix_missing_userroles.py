"""
Management command para sanear UserRoles faltantes en tenants existentes.
Uso: python manage.py fix_missing_userroles [--dry-run]
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.tenants_api.models import Tenant
from apps.roles_api.models import Role, UserRole


class Command(BaseCommand):
    help = 'Crear UserRoles faltantes para owners de tenants activos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué se haría sin ejecutar cambios'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: No se harán cambios'))
        
        try:
            # Obtener role CLIENT_ADMIN
            client_admin_role = Role.objects.get(name='CLIENT_ADMIN')
        except Role.DoesNotExist:
            self.stdout.write(self.style.ERROR('ERROR: Role CLIENT_ADMIN no existe'))
            return

        # Detectar tenants activos con owner sin UserRole contextual
        tenants_to_fix = []
        
        for tenant in Tenant.objects.filter(is_active=True, owner__isnull=False):
            # Verificar si ya existe UserRole contextual
            existing_userrole = UserRole.objects.filter(
                user=tenant.owner,
                role=client_admin_role,
                tenant=tenant
            ).exists()
            
            if not existing_userrole:
                tenants_to_fix.append(tenant)

        self.stdout.write(f'Tenants encontrados que necesitan UserRole: {len(tenants_to_fix)}')
        
        if not tenants_to_fix:
            self.stdout.write(self.style.SUCCESS('No hay tenants que necesiten corrección'))
            return

        # Mostrar detalles
        for tenant in tenants_to_fix:
            self.stdout.write(f'  - {tenant.name} (ID: {tenant.id}) → Owner: {tenant.owner.email}')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY-RUN: No se crearon UserRoles'))
            return

        # Confirmar ejecución
        confirm = input('\n¿Continuar con la creación de UserRoles? (yes/no): ')
        if confirm.lower() != 'yes':
            self.stdout.write('Operación cancelada')
            return

        # Crear UserRoles faltantes
        created_count = 0
        
        with transaction.atomic():
            for tenant in tenants_to_fix:
                try:
                    user_role, created = UserRole.objects.get_or_create(
                        user=tenant.owner,
                        role=client_admin_role,
                        tenant=tenant
                    )
                    
                    if created:
                        created_count += 1
                        self.stdout.write(
                            f'✓ UserRole creado: {tenant.owner.email} → CLIENT_ADMIN @ {tenant.name}'
                        )
                    else:
                        self.stdout.write(
                            f'- UserRole ya existía: {tenant.owner.email} @ {tenant.name}'
                        )
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'ERROR creando UserRole para {tenant.name}: {str(e)}')
                    )

        self.stdout.write(
            self.style.SUCCESS(f'\nCompletado: {created_count} UserRoles creados exitosamente')
        )