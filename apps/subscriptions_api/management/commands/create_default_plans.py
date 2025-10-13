from django.core.management.base import BaseCommand
from apps.subscriptions_api.models import SubscriptionPlan

class Command(BaseCommand):
    help = 'Create default subscription plans'

    def handle(self, *args, **options):
        plans = [
            {
                'name': 'free',
                'description': 'Plan gratuito de prueba por 7 días',
                'price': 0.00,
                'duration_month': 0,  # 0 = días, no meses
                'max_employees': 2,
                'max_users': 3,
                'features': {
                    'appointments': True,
                    'basic_reports': False,
                    'inventory': False,
                    'advanced_reports': False,
                    'multi_location': False,
                    'api_access': False,
                    'custom_branding': False,
                    'priority_support': False
                },
                'is_active': True
            },
            {
                'name': 'basic',
                'description': 'Plan básico para pequeñas barberías',
                'price': 29.99,
                'duration_month': 1,
                'max_employees': 5,
                'max_users': 10,
                'features': {
                    'appointments': True,
                    'basic_reports': True,
                    'inventory': False,
                    'advanced_reports': False,
                    'multi_location': False,
                    'api_access': False,
                    'custom_branding': False,
                    'priority_support': False
                },
                'is_active': True
            },
            {
                'name': 'standard',
                'description': 'Plan estándar para barberías en crecimiento',
                'price': 49.99,
                'duration_month': 1,
                'max_employees': 10,
                'max_users': 20,
                'features': {
                    'appointments': True,
                    'basic_reports': True,
                    'inventory': True,
                    'advanced_reports': False,
                    'multi_location': False,
                    'api_access': False,
                    'custom_branding': False,
                    'priority_support': False
                },
                'is_active': True
            },
            {
                'name': 'premium',
                'description': 'Plan premium con características avanzadas',
                'price': 79.99,
                'duration_month': 1,
                'max_employees': 25,
                'max_users': 50,
                'features': {
                    'appointments': True,
                    'basic_reports': True,
                    'inventory': True,
                    'advanced_reports': True,
                    'multi_location': True,
                    'api_access': False,
                    'custom_branding': True,
                    'priority_support': True
                },
                'is_active': True
            },
            {
                'name': 'enterprise',
                'description': 'Plan empresarial para cadenas grandes',
                'price': 149.99,
                'duration_month': 1,
                'max_employees': 0,  # Unlimited
                'max_users': 0,      # Unlimited
                'features': {
                    'appointments': True,
                    'basic_reports': True,
                    'inventory': True,
                    'advanced_reports': True,
                    'multi_location': True,
                    'api_access': True,
                    'custom_branding': True,
                    'priority_support': True
                },
                'is_active': True
            }
        ]

        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.get_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created plan: {plan.get_name_display()}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Plan already exists: {plan.get_name_display()}')
                )

        self.stdout.write(
            self.style.SUCCESS('Successfully created/verified all default plans')
        )