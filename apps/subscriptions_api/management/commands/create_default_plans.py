from django.core.management.base import BaseCommand

from apps.subscriptions_api.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Create default subscription plans'

    def handle(self, *args, **options):
        plans = [
            {
                'name': 'trial',
                'description': 'Periodo de prueba gratuito por 7 dias',
                'price': 0.00,
                'duration_month': 0,
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
                'commercial_benefits': [],
                'is_active': True
            },
            {
                'name': 'free',
                'description': 'Plan gratuito de prueba por 7 dias',
                'price': 0.00,
                'duration_month': 0,
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
                'commercial_benefits': [],
                'is_active': True
            },
            {
                'name': 'basic',
                'description': 'Plan Profesional para barberias pequenas',
                'price': 29.99,
                'duration_month': 1,
                'stripe_price_id': '',
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
                'stripe_price_id': '',
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
                'stripe_price_id': '',
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
            plan, created = SubscriptionPlan.objects.get_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created plan: {plan.get_name_display()}'))
            else:
                self.stdout.write(self.style.WARNING(f'Plan already exists: {plan.get_name_display()}'))

        self.stdout.write(self.style.SUCCESS('Successfully created/verified all default plans'))
