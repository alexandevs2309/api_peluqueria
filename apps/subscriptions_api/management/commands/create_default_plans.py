from django.core.management.base import BaseCommand

from apps.subscriptions_api.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Create default subscription plans'

    def handle(self, *args, **options):
        plans = [
            {
                'name': 'free',
                'description': 'Prueba gratis por 7 dias para conocer la plataforma antes de suscribirte.',
                'price': 0.00,
                'duration_month': 0,
                'max_employees': 3,
                'max_users': 3,
                'features': {
                    'appointments': True,
                    'basic_reports': True,
                    'cash_register': True,
                    'client_history': True,
                    'inventory': False,
                    'advanced_reports': False,
                    'multi_location': False,
                    'api_access': False,
                    'custom_branding': False,
                    'priority_support': False
                },
                'commercial_benefits': [
                    'Prueba gratis por 7 dias',
                    'Ideal para evaluar antes de pagar'
                ],
                'is_active': True
            },
            {
                'name': 'basic',
                'description': 'Para barberias pequenas que necesitan ordenar citas, cobros y seguimiento de clientes sin complicarse.',
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
                'commercial_benefits': [
                    'Ideal para empezar a operar con orden',
                    'Sin limite de tiempo y listo para uso diario'
                ],
                'is_active': True
            },
            {
                'name': 'standard',
                'description': 'El plan recomendado para negocios en crecimiento que necesitan mas control, visibilidad y operacion multi-sucursal.',
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
                'commercial_benefits': [
                    'La mejor relacion valor-precio para crecer',
                    'Mas control operativo para equipos y sucursales'
                ],
                'is_active': True
            },
            {
                'name': 'premium',
                'description': 'Para operaciones grandes que necesitan crecer sin topes fijos, reforzar su marca y recibir atencion prioritaria.',
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
                    'Acompanamiento comercial',
                    'Escala sin limite de empleados ni usuarios'
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
