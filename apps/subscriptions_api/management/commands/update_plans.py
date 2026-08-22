from django.core.management.base import BaseCommand
from apps.subscriptions_api.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Update existing subscription plans (idempotent)'

    def handle(self, *args, **options):
        updates = {
            'basic': {
                'description': 'Plan básico para barberías individuales',
                'price': 29.99,
                'annual_price': 299.99,
                'max_employees': 3,
                'max_users': 5,
                'allows_multiple_branches': False,
                'features': {
                    'cash_register': True,
                    'appointments': True,
                    'inventory': True,
                    'reports': True,
                    'basic_reports': True,
                    'client_history': True,
                    'promotions': False,
                    'multi_location': False,
                    'advanced_reports': False,
                    'payroll': False,
                    'custom_branding': False,
                    'whatsapp_notifications': False,
                    'export_reports': False,
                    'priority_support': False,
                },
                'commercial_benefits': [
                    '1 Sucursal Principal',
                    'Hasta 3 Empleados',
                    'Punto de Venta (POS) y Caja Diaria',
                    'Agenda de Citas en Tiempo Real',
                    'Inventario de Productos',
                    'Reportes Básicos',
                    'Soporte por Correo',
                ],
            },
            'standard': {
                'description': 'Plan Pro para negocios en crecimiento',
                'price': 59.99,
                'annual_price': 599.99,
                'max_employees': 10,
                'max_users': 15,
                'allows_multiple_branches': True,
                'features': {
                    'cash_register': True,
                    'appointments': True,
                    'inventory': True,
                    'reports': True,
                    'basic_reports': True,
                    'client_history': True,
                    'promotions': True,
                    'multi_location': True,
                    'advanced_reports': True,
                    'payroll': True,
                    'custom_branding': False,
                    'whatsapp_notifications': False,
                    'export_reports': False,
                    'priority_support': False,
                },
                'commercial_benefits': [
                    'Sucursales Ilimitadas',
                    'Hasta 10 Empleados y 15 Usuarios',
                    'Multi-Sucursal',
                    'Promociones y Cupones',
                    'Reportes Avanzados y BI',
                    'Comisiones y Nómina TSS',
                    'Soporte Prioritario por Correo',
                ],
            },
            'premium': {
                'description': 'Plan Business para spas y salones consolidados',
                'price': 99.99,
                'annual_price': 999.99,
                'max_employees': 25,
                'max_users': 30,
                'allows_multiple_branches': True,
                'features': {
                    'cash_register': True,
                    'appointments': True,
                    'inventory': True,
                    'reports': True,
                    'basic_reports': True,
                    'client_history': True,
                    'promotions': True,
                    'multi_location': True,
                    'advanced_reports': True,
                    'payroll': True,
                    'custom_branding': True,
                    'whatsapp_notifications': True,
                    'export_reports': False,
                    'priority_support': False,
                },
                'commercial_benefits': [
                    'Todo lo del Plan Pro',
                    'Sucursales Ilimitadas',
                    'Hasta 25 Empleados y 30 Usuarios',
                    'Conexión WhatsApp mediante QR',
                    'Branding Personalizado (Logo y Colores)',
                    'Soporte Prioritario por Correo y WhatsApp',
                ],
            },
            'enterprise': {
                'description': 'Plan Enterprise ilimitado para cadenas y franquicias',
                'price': 199.99,
                'annual_price': 1999.99,
                'max_employees': 0,
                'max_users': 0,
                'allows_multiple_branches': True,
                'features': {
                    'cash_register': True,
                    'appointments': True,
                    'inventory': True,
                    'reports': True,
                    'basic_reports': True,
                    'client_history': True,
                    'promotions': True,
                    'multi_location': True,
                    'advanced_reports': True,
                    'payroll': True,
                    'custom_branding': True,
                    'whatsapp_notifications': True,
                    'export_reports': True,
                    'priority_support': True,
                },
                'commercial_benefits': [
                    'Todo lo del Plan Business',
                    'Sucursales y Empleados Ilimitados',
                    'Exportación Excel de Reportes',
                    'Auditoría Avanzada',
                    'Soporte Dedicado con Seguimiento Personalizado',
                ],
            },
        }

        for plan_name, plan_data in updates.items():
            try:
                plan = SubscriptionPlan.objects.get(name=plan_name)
                for key, value in plan_data.items():
                    setattr(plan, key, value)
                plan.save()
                self.stdout.write(self.style.SUCCESS(
                    f'Updated {plan.get_name_display()}'
                ))
            except SubscriptionPlan.DoesNotExist:
                plan = SubscriptionPlan.objects.create(
                    name=plan_name, is_active=True, **plan_data
                )
                self.stdout.write(self.style.SUCCESS(
                    f'Created {plan.get_name_display()}'
                ))
