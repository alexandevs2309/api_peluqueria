from django.core.management.base import BaseCommand

from apps.subscriptions_api.models import SubscriptionPlan

class Command(BaseCommand):
    help = 'Update existing subscription plans to new structure'

    def handle(self, *args, **options):
        updates = {
            'basic': {
                'description': 'Entrada seria para barberias pequenas que necesitan citas, caja, clientes y reportes sin complicarse.',
                'price': 29.99,
                'annual_price': 299.88,
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
                ]
            },
            'standard': {
                'description': 'El plan recomendado para negocios en crecimiento que necesitan inventario, reportes avanzados y mas capacidad.',
                'price': 59.99,
                'annual_price': 599.88,
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
                ]
            },
            'premium': {
                'description': 'Para equipos grandes que necesitan multi-sucursal, permisos avanzados y branding.',
                'price': 119.99,
                'annual_price': 1199.88,
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
                ]
            },
            'enterprise': {
                'description': 'Para cadenas y operaciones que necesitan escala ilimitada, soporte prioritario y acompanamiento.',
                'price': 199.99,
                'annual_price': 2039.88,
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
                ]
            }
        }

        for plan_name, data in updates.items():
            plan, created = SubscriptionPlan.objects.get_or_create(
                name=plan_name,
                defaults={**data, 'duration_month': 1, 'is_active': True, 'is_public': True}
            )
            if not created:
                for key, value in data.items():
                    setattr(plan, key, value)
                plan.is_active = True
                plan.is_public = True
                plan.save()
                self.stdout.write(self.style.SUCCESS(f'Actualizado plan: {plan.get_name_display()}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Creado plan: {plan.get_name_display()}'))

        self.stdout.write(self.style.SUCCESS('Planes actualizados correctamente'))
