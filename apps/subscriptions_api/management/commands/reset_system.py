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
                'description': 'Plan básico para barberías individuales',
                'price': 29.99,
                'annual_price': 299.99,
                'max_employees': 3,
                'max_users': 5,
                'allows_multiple_branches': False,
                'features': {
                    'cash_register': True, 'appointments': True, 'inventory': True,
                    'reports': True, 'basic_reports': True, 'client_history': True,
                    'promotions': False, 'multi_location': False, 'advanced_reports': False,
                    'payroll': False, 'custom_branding': False, 'whatsapp_notifications': False,
                    'export_reports': False, 'priority_support': False,
                },
                'commercial_benefits': [],
                'is_active': True,
            },
            {
                'name': 'standard',
                'description': 'Plan Pro para negocios en crecimiento',
                'price': 59.99,
                'annual_price': 599.99,
                'max_employees': 10,
                'max_users': 15,
                'allows_multiple_branches': True,
                'features': {
                    'cash_register': True, 'appointments': True, 'inventory': True,
                    'reports': True, 'basic_reports': True, 'client_history': True,
                    'promotions': True, 'multi_location': True, 'advanced_reports': True,
                    'payroll': True, 'custom_branding': False, 'whatsapp_notifications': False,
                    'export_reports': False, 'priority_support': False,
                },
                'commercial_benefits': [],
                'is_active': True,
            },
            {
                'name': 'premium',
                'description': 'Plan Business para spas y salones consolidados',
                'price': 99.99,
                'annual_price': 999.99,
                'max_employees': 25,
                'max_users': 30,
                'allows_multiple_branches': True,
                'features': {
                    'cash_register': True, 'appointments': True, 'inventory': True,
                    'reports': True, 'basic_reports': True, 'client_history': True,
                    'promotions': True, 'multi_location': True, 'advanced_reports': True,
                    'payroll': True, 'custom_branding': True, 'whatsapp_notifications': True,
                    'export_reports': False, 'priority_support': False,
                },
                'commercial_benefits': [],
                'is_active': True,
            },
            {
                'name': 'enterprise',
                'description': 'Plan Enterprise ilimitado para cadenas y franquicias',
                'price': 199.99,
                'annual_price': 1999.99,
                'max_employees': 0,
                'max_users': 0,
                'allows_multiple_branches': True,
                'features': {
                    'cash_register': True, 'appointments': True, 'inventory': True,
                    'reports': True, 'basic_reports': True, 'client_history': True,
                    'promotions': True, 'multi_location': True, 'advanced_reports': True,
                    'payroll': True, 'custom_branding': True, 'whatsapp_notifications': True,
                    'export_reports': True, 'priority_support': True,
                },
                'commercial_benefits': [],
                'is_active': True,
            },
        ]

        for plan_data in plans:
            plan = SubscriptionPlan.objects.create(**plan_data)
            self.stdout.write(self.style.SUCCESS(f'Creado: {plan.get_name_display()} - ${plan.price}'))

        self.stdout.write(self.style.SUCCESS('Reset completo. Sistema listo para produccion.'))
