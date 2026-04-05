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
                'description': 'Plan Profesional para barberias pequenas',
                'price': 29.99,
                'duration_month': 1,
                'max_employees': 8,
                'max_users': 16,
                'allows_multiple_branches': False,
                'features': {
                    'appointments': True,
                    'basic_reports': True,
                    'cash_register': True,
                    'client_history': True,
                    'inventory': False,
                    'advanced_reports': False,
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
                'description': 'Plan Negocio para barberias en crecimiento',
                'price': 69.99,
                'duration_month': 1,
                'max_employees': 25,
                'max_users': 50,
                'allows_multiple_branches': True,
                'features': {
                    'appointments': True,
                    'basic_reports': True,
                    'cash_register': True,
                    'client_history': True,
                    'inventory': True,
                    'advanced_reports': True,
                    'multi_location': True,
                    'role_permissions': False,
                    'api_access': False,
                    'custom_branding': False
                },
                'commercial_benefits': [],
                'is_active': True
            },
            {
                'name': 'premium',
                'description': 'Plan Premium para operaciones grandes',
                'price': 129.99,
                'duration_month': 1,
                'max_employees': 0,
                'max_users': 0,
                'allows_multiple_branches': True,
                'features': {
                    'appointments': True,
                    'basic_reports': True,
                    'cash_register': True,
                    'client_history': True,
                    'inventory': True,
                    'advanced_reports': True,
                    'multi_location': True,
                    'role_permissions': True,
                    'api_access': True,
                    'custom_branding': True
                },
                'commercial_benefits': [
                    'Atencion prioritaria',
                    'Acompanamiento comercial'
                ],
                'is_active': True
            }
        ]

        for plan_data in plans:
            plan = SubscriptionPlan.objects.create(**plan_data)
            self.stdout.write(self.style.SUCCESS(f'Creado: {plan.get_name_display()} - ${plan.price}'))

        self.stdout.write(self.style.SUCCESS('Reset completo. Sistema listo para produccion.'))
