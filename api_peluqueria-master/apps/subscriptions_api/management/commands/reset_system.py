from django.core.management.base import BaseCommand

from apps.auth_api.models import User
from apps.subscriptions_api.models import Subscription, SubscriptionPlan, UserSubscription
from apps.tenants_api.models import Tenant

class Command(BaseCommand):
    help = 'Reset all tenants and subscription plans (DESTRUCTIVE)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion of all data',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.ERROR('ADVERTENCIA: Este comando eliminara TODOS los tenants y suscripciones.'))
            self.stdout.write(self.style.ERROR('Ejecuta con --confirm para proceder'))
            return

        UserSubscription.objects.all().delete()
        Subscription.objects.all().delete()
        self.stdout.write(self.style.WARNING('Suscripciones eliminadas'))

        users_count = User.objects.filter(is_superuser=False).count()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.WARNING(f'{users_count} usuarios eliminados'))

        tenants_count = Tenant.objects.count()
        Tenant.objects.all().delete()
        self.stdout.write(self.style.WARNING(f'{tenants_count} tenants eliminados'))

        SubscriptionPlan.objects.all().delete()
        self.stdout.write(self.style.WARNING('Planes viejos eliminados'))

        plans = [
            {
                'name': 'basic',
                'description': 'Entrada seria para barberias pequenas',
                'price': 29.00,
                'duration_month': 1,
                'max_employees': 5,
                'max_users': 10,
                'allows_multiple_branches': False,
                'features': {
                    'appointments': True,
                    'reports': True,
                    'cash_register': True,
                    'client_history': True,
                    'inventory': False,
                    
                    'multi_location': False,
                    'role_permissions': False,
                    'api_access': False,
                    'custom_branding': False
                },
                'commercial_benefits': [],
                'is_active': True
            },
            {
                'name': 'standard',
                'description': 'Plan Pro recomendado para barberias en crecimiento',
                'price': 59.00,
                'duration_month': 1,
                'max_employees': 15,
                'max_users': 30,
                'allows_multiple_branches': False,
                'features': {
                    'appointments': True,
                    'reports': True,
                    'cash_register': True,
                    'client_history': True,
                    'inventory': True,
                    
                    'multi_location': False,
                    'role_permissions': False,
                    'api_access': False,
                    'custom_branding': False
                },
                'commercial_benefits': [],
                'is_active': True
            },
            {
                'name': 'premium',
                'description': 'Plan Business para equipos grandes',
                'price': 99.00,
                'duration_month': 1,
                'max_employees': 50,
                'max_users': 100,
                'allows_multiple_branches': True,
                'features': {
                    'appointments': True,
                    'reports': True,
                    'cash_register': True,
                    'client_history': True,
                    'inventory': True,
                    
                    'multi_location': True,
                    'role_permissions': True,
                    'api_access': True,
                    'custom_branding': True
                },
                'commercial_benefits': [
                    'Permisos avanzados',
                    'Branding y multi-sucursal'
                ],
                'is_active': True
            },
            {
                'name': 'enterprise',
                'description': 'Plan Enterprise para cadenas y operaciones custom',
                'price': 149.00,
                'duration_month': 1,
                'max_employees': 0,
                'max_users': 0,
                'allows_multiple_branches': True,
                'features': {
                    'appointments': True,
                    'reports': True,
                    'cash_register': True,
                    'client_history': True,
                    'inventory': True,
                    
                    'multi_location': True,
                    'role_permissions': True,
                    'api_access': True,
                    'custom_branding': True,
                    'priority_support': True
                },
                'commercial_benefits': [
                    'Escala ilimitada',
                    'Soporte prioritario'
                ],
                'is_active': True
            }
        ]

        for plan_data in plans:
            plan = SubscriptionPlan.objects.create(**plan_data)
            self.stdout.write(self.style.SUCCESS(f'Creado: {plan.get_name_display()} - ${plan.price}'))

        self.stdout.write(self.style.SUCCESS('Reset completo. Sistema listo para produccion.'))
