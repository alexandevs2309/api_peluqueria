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
                'is_public': False,
                'features': {
                    'appointments': True,
                    'reports': True,
                    'cash_register': True,
                    'client_history': True,
                    'inventory': False,

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
                'description': 'Entrada seria para barberias pequenas que necesitan citas, caja, clientes y reportes sin complicarse.',
                'price': 29.00,
                'duration_month': 1,
                'stripe_price_id': '',
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
                'commercial_benefits': [
                    'Entrada seria para operar con orden',
                    'Ideal para equipos pequenos'
                ],
                'is_active': True
            },
            {
                'name': 'standard',
                'description': 'El plan recomendado para negocios en crecimiento que necesitan inventario, reportes avanzados y mas capacidad.',
                'price': 59.00,
                'duration_month': 1,
                'stripe_price_id': '',
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
                'commercial_benefits': [
                    'Plan recomendado para la mayoria de barberias',
                    'Mas control operativo sin dar un salto grande de precio'
                ],
                'is_active': True
            },
            {
                'name': 'premium',
                'description': 'Para equipos grandes que necesitan multi-sucursal, permisos avanzados y branding.',
                'price': 99.00,
                'duration_month': 1,
                'stripe_price_id': '',
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
                    'Pensado para operaciones con varias areas o sucursales',
                    'Permisos avanzados, branding y mas capacidad'
                ],
                'is_active': True
            },
            {
                'name': 'enterprise',
                'description': 'Para cadenas y operaciones que necesitan escala ilimitada, soporte prioritario y acompanamiento.',
                'price': 149.00,
                'duration_month': 1,
                'stripe_price_id': '',
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
                    'Escala sin limite de empleados ni usuarios',
                    'Soporte prioritario y acompanamiento comercial',
                    'Ideal para cadenas y operaciones con necesidades custom'
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
