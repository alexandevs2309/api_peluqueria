import os
from django.utils.crypto import get_random_string
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.roles_api.models import Role
from apps.settings_api.models import SystemSettings
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan

User = get_user_model()

class Command(BaseCommand):
    help = 'Configurar sistema SaaS con datos iniciales'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Resetear configuraciones existentes',
        )
        parser.add_argument(
            '--sync-defaults',
            action='store_true',
            help='Actualizar registros existentes con defaults del seed',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Configurando sistema SaaS...'))

        if options['reset']:
            self.stdout.write('⚠️  Reseteando configuraciones...')
            SystemSettings.objects.all().delete()

        # 1. Crear configuraciones del sistema
        self.create_system_settings(sync_defaults=options['sync_defaults'])
        
        # 2. Crear roles si no existen
        self.create_roles()
        
        # 3. Crear planes de suscripción
        self.create_subscription_plans(sync_defaults=options['sync_defaults'])
        
        # 4. Crear super admin si no existe
        self.create_super_admin()

        self.stdout.write(self.style.SUCCESS('✅ Sistema SaaS configurado correctamente!'))
        self.stdout.write('')
        self.stdout.write('📋 Resumen:')
        self.stdout.write(f'   • Roles creados: {Role.objects.count()}')
        self.stdout.write(f'   • Planes disponibles: {SubscriptionPlan.objects.count()}')
        self.stdout.write(f'   • Tenants registrados: {Tenant.objects.count()}')

    def create_system_settings(self, sync_defaults=False):
        """Crear configuraciones globales del sistema"""
        defaults = {
            'platform_name': 'BarberSaaS Pro',
            'support_email': 'soporte@barbersaas.com',
            'max_tenants': 500,
            'trial_days': 14,
            'platform_commission_rate': 3.5,
            'stripe_enabled': True,
            'sendgrid_enabled': True,
            'aws_s3_enabled': True,
            'auto_suspend_expired': True,
        }
        settings, created = SystemSettings.objects.get_or_create(pk=1, defaults=defaults)

        if created:
            self.stdout.write('✓ Configuraciones del sistema creadas')
            return

        if sync_defaults:
            for field, value in defaults.items():
                setattr(settings, field, value)
            settings.save(update_fields=list(defaults.keys()) + ['updated_at'])
            self.stdout.write('✓ Configuraciones del sistema sincronizadas con defaults')
            return

        self.stdout.write('✓ Configuraciones del sistema ya existen; branding manual preservado')

    def create_roles(self):
        """Crear roles del sistema"""
        roles_data = [
            # Roles globales (SaaS)
            {'name': 'Super-Admin', 'scope': 'GLOBAL', 'description': 'Administrador del SaaS'},
            {'name': 'Soporte', 'scope': 'GLOBAL', 'description': 'Equipo de soporte técnico'},
            
            # Roles por tenant (Peluquería)
            {'name': 'Client-Admin', 'scope': 'TENANT', 'description': 'Administrador de peluquería'},
            {'name': 'Cajera', 'scope': 'TENANT', 'description': 'Cajera/Recepcionista'},
            {'name': 'Client-Staff', 'scope': 'TENANT', 'description': 'Estilista/Peluquero'},
            {'name': 'Estilista', 'scope': 'TENANT', 'description': 'Estilista/Peluquero'},
            {'name': 'Manager', 'scope': 'TENANT', 'description': 'Encargado operativo'},
            {'name': 'Utility', 'scope': 'TENANT', 'description': 'Personal de apoyo'},
        ]

        for role_data in roles_data:
            role, created = Role.objects.get_or_create(
                name=role_data['name'],
                defaults={
                    'scope': role_data['scope'],
                    'description': role_data['description']
                }
            )
            if created:
                self.stdout.write(f'✓ Rol creado: {role.name}')

    def create_subscription_plans(self, sync_defaults=False):
        """Crear planes de suscripción"""
        plans_data = [
            {
                'name': 'basic',
                'description': 'Plan básico para peluquerías pequeñas',
                'price': 29.99,
                'duration_month': 1,
                'max_employees': 5,
                'features': {
                    'appointments': True,
                    'clients': True,
                    'pos': True,
                    'reports': 'basic',
                    'support': 'email'
                }
            },
            {
                'name': 'standard',
                'description': 'Plan estándar para peluquerías medianas',
                'price': 59.99,
                'duration_month': 1,
                'max_employees': 15,
                'features': {
                    'appointments': True,
                    'clients': True,
                    'pos': True,
                    'inventory': True,
                    'reports': 'advanced',
                    'support': 'priority'
                }
            },
            {
                'name': 'premium',
                'description': 'Plan premium para peluquerías grandes',
                'price': 99.99,
                'duration_month': 1,
                'max_employees': 50,
                'features': {
                    'appointments': True,
                    'clients': True,
                    'pos': True,
                    'inventory': True,
                    'multi_branch': True,
                    'reports': 'premium',
                    'support': '24/7'
                }
            }
        ]

        mutable_fields = ['description', 'price', 'duration_month', 'max_employees', 'features']

        for plan_data in plans_data:
            plan, created = SubscriptionPlan.objects.get_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(f'✓ Plan creado: {plan.get_name_display()} - ${plan.price}/mes')
            elif sync_defaults:
                updated = False
                for field in mutable_fields:
                    new_value = plan_data[field]
                    if getattr(plan, field) != new_value:
                        setattr(plan, field, new_value)
                        updated = True
                if updated:
                    plan.save(update_fields=mutable_fields + ['updated_at'])
                    self.stdout.write(f'✓ Plan sincronizado: {plan.get_name_display()}')
                else:
                    self.stdout.write(f'✓ Plan sin cambios: {plan.get_name_display()}')
            else:
                self.stdout.write(f'✓ Plan existente preservado: {plan.get_name_display()}')

    def create_super_admin(self):
        """Crear usuario Super Admin"""
        super_admin_email = os.getenv('SUPERADMIN_EMAIL')
        super_admin_password = os.getenv('SUPERADMIN_PASSWORD')

        if not super_admin_email:
            self.stdout.write(
                self.style.WARNING(
                    '⚠️ SUPERADMIN_EMAIL no definido. Se omite creación automática de super admin.'
                )
            )
            return

        if not super_admin_password:
            super_admin_password = get_random_string(24)
            self.stdout.write(
                self.style.WARNING(
                    '⚠️ SUPERADMIN_PASSWORD no definido. Se generó una contraseña aleatoria temporal.'
                )
            )

        if not User.objects.filter(email=super_admin_email).exists():
            super_admin = User.objects.create_user(
                email=super_admin_email,
                password=super_admin_password,
                full_name='Super Administrador',
                is_staff=True,
                is_superuser=True
            )
            
            # Asignar rol Super-Admin
            super_admin_role = Role.objects.get(name='Super-Admin')
            super_admin.roles.add(super_admin_role)
            
            self.stdout.write('✓ Super Admin creado')
        else:
            self.stdout.write('✓ Super Admin ya existe')
