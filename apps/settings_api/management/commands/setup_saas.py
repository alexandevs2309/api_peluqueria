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

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Configurando sistema SaaS...'))

        if options['reset']:
            self.stdout.write('⚠️  Reseteando configuraciones...')
            SystemSettings.objects.all().delete()

        # 1. Crear configuraciones del sistema
        self.create_system_settings()
        
        # 2. Crear roles si no existen
        self.create_roles()
        
        # 3. Crear planes de suscripción
        self.create_subscription_plans()
        
        # 4. Crear super admin si no existe
        self.create_super_admin()

        self.stdout.write(self.style.SUCCESS('✅ Sistema SaaS configurado correctamente!'))
        self.stdout.write('')
        self.stdout.write('📋 Resumen:')
        self.stdout.write(f'   • Roles creados: {Role.objects.count()}')
        self.stdout.write(f'   • Planes disponibles: {SubscriptionPlan.objects.count()}')
        self.stdout.write(f'   • Tenants registrados: {Tenant.objects.count()}')
        self.stdout.write('')
        self.stdout.write('🔐 Credenciales Super Admin:')
        self.stdout.write('   Email: super@admin.com')
        self.stdout.write('   Password: SuperAdmin123!')

    def create_system_settings(self):
        """Crear configuraciones globales del sistema"""
        settings = SystemSettings.get_settings()
        
        # Actualizar con valores por defecto
        settings.platform_name = 'BarberSaaS Pro'
        settings.support_email = 'soporte@barbersaas.com'
        settings.max_tenants = 500
        settings.trial_days = 14
        settings.platform_commission_rate = 3.5
        
        # Habilitar integraciones principales
        settings.stripe_enabled = True
        settings.sendgrid_enabled = True
        settings.aws_s3_enabled = True
        settings.auto_suspend_expired = True
        
        settings.save()
        self.stdout.write('✓ Configuraciones del sistema creadas')

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

    def create_subscription_plans(self):
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

        for plan_data in plans_data:
            plan, created = SubscriptionPlan.objects.get_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(f'✓ Plan creado: {plan.get_name_display()} - ${plan.price}/mes')

    def create_super_admin(self):
        """Crear usuario Super Admin"""
        if not User.objects.filter(email='super@admin.com').exists():
            super_admin = User.objects.create_user(
                email='super@admin.com',
                password='SuperAdmin123!',
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