"""
Management command para convertir usuario a SUPER_ADMIN del SaaS.
Uso: python manage.py create_superadmin <email>
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.roles_api.models import Role, UserRole

User = get_user_model()


class Command(BaseCommand):
    help = 'Convertir usuario a SUPER_ADMIN del SaaS'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email del usuario a convertir')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué se haría sin ejecutar cambios'
        )

    def handle(self, *args, **options):
        email = options['email']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: No se harán cambios'))

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Usuario con email {email} no existe'))
            return

        try:
            super_admin_role = Role.objects.get(name='SUPER_ADMIN')
        except Role.DoesNotExist:
            self.stdout.write(self.style.ERROR('Role SUPER_ADMIN no existe'))
            return

        # Mostrar estado actual
        self.stdout.write(f'Usuario: {user.email}')
        self.stdout.write(f'Role legacy actual: {user.role}')
        self.stdout.write(f'Tenant actual: {user.tenant}')
        
        current_userroles = UserRole.objects.filter(user=user)
        self.stdout.write(f'UserRoles actuales: {current_userroles.count()}')
        for ur in current_userroles:
            self.stdout.write(f'  - {ur.role.name} @ {ur.tenant or "GLOBAL"}')

        # Verificar si ya es SUPER_ADMIN
        existing_super_admin = UserRole.objects.filter(
            user=user,
            role=super_admin_role,
            tenant__isnull=True
        ).exists()

        if existing_super_admin and user.role == 'SUPER_ADMIN':
            self.stdout.write(self.style.SUCCESS('Usuario ya es SUPER_ADMIN correctamente'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('\nCambios que se harían:'))
            if not existing_super_admin:
                self.stdout.write('  + Crear UserRole SUPER_ADMIN (tenant=None)')
            if current_userroles.exclude(role=super_admin_role).exists():
                self.stdout.write('  - Eliminar UserRoles CLIENT_ADMIN/CLIENT_STAFF')
            if user.role != 'SUPER_ADMIN':
                self.stdout.write(f'  * Actualizar user.role: {user.role} → SUPER_ADMIN')
            return

        # Confirmar ejecución
        confirm = input(f'\n¿Convertir {email} a SUPER_ADMIN del SaaS? (yes/no): ')
        if confirm.lower() != 'yes':
            self.stdout.write('Operación cancelada')
            return

        # Ejecutar cambios
        with transaction.atomic():
            # 1. Eliminar UserRoles CLIENT_ADMIN/CLIENT_STAFF
            deleted_roles = UserRole.objects.filter(
                user=user,
                role__name__in=['CLIENT_ADMIN', 'CLIENT_STAFF']
            )
            
            if deleted_roles.exists():
                for ur in deleted_roles:
                    self.stdout.write(f'- Eliminando UserRole: {ur.role.name} @ {ur.tenant or "GLOBAL"}')
                deleted_roles.delete()

            # 2. Crear UserRole SUPER_ADMIN (tenant=None)
            super_admin_userrole, created = UserRole.objects.get_or_create(
                user=user,
                role=super_admin_role,
                tenant=None
            )
            
            if created:
                self.stdout.write('+ UserRole SUPER_ADMIN creado (tenant=None)')
            else:
                self.stdout.write('= UserRole SUPER_ADMIN ya existía')

            # 3. Actualizar user.role legacy
            if user.role != 'SUPER_ADMIN':
                old_role = user.role
                user.role = 'SUPER_ADMIN'
                user.save(update_fields=['role'])
                self.stdout.write(f'* user.role actualizado: {old_role} → SUPER_ADMIN')

        self.stdout.write(self.style.SUCCESS(f'\n✓ {email} convertido a SUPER_ADMIN exitosamente'))