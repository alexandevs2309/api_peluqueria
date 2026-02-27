from django.core.management.base import BaseCommand
from apps.subscriptions_api.models import SubscriptionPlan

class Command(BaseCommand):
    help = 'Update existing subscription plans to new structure'

    def handle(self, *args, **options):
        # Actualizar planes existentes
        updates = {
            'basic': {
                'description': 'Plan Profesional para pequeñas peluquerías',
                'price': 29.99,
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
                    'priority_support': False
                }
            },
            'standard': {
                'description': 'Plan Negocio para peluquerías en crecimiento',
                'price': 69.99,
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
                    'role_permissions': True,
                    'api_access': False,
                    'priority_support': False
                }
            },
            'premium': {
                'description': 'Plan Empresarial para cadenas grandes',
                'price': 129.99,
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
                    'priority_support': True,
                    'sla_guaranteed': True
                }
            }
        }

        # Desactivar plan enterprise si existe
        try:
            enterprise = SubscriptionPlan.objects.get(name='enterprise')
            enterprise.is_active = False
            enterprise.save()
            self.stdout.write(self.style.WARNING('Desactivado plan: enterprise'))
        except SubscriptionPlan.DoesNotExist:
            pass

        # Actualizar planes
        for plan_name, data in updates.items():
            try:
                plan = SubscriptionPlan.objects.get(name=plan_name)
                for key, value in data.items():
                    setattr(plan, key, value)
                plan.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Actualizado plan: {plan.get_name_display()}')
                )
            except SubscriptionPlan.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Plan no encontrado: {plan_name}')
                )

        self.stdout.write(
            self.style.SUCCESS('Planes actualizados correctamente')
        )
