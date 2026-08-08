from django.core.management.base import BaseCommand
from apps.subscriptions_api.models import SubscriptionPlan

class Command(BaseCommand):
    help = 'Create or update default subscription plans with balanced SaaS packaging'

    def handle(self, *args, **options):
        plans = [
            {
                'name': 'basic',
                'description': 'Ideal para salones y barberías que inician y necesitan citas, caja, clientes y facturación sin complicarse.',
                'price': 29.99,
                'annual_price': 299.88,
                'duration_month': 1,
                'stripe_price_id': '',
                'stripe_annual_price_id': '',
                'max_employees': 4,
                'max_users': 8,
                'allows_multiple_branches': False,
                'features': {
                    'appointments': True,
                    'reports': False,
                    'cash_register': True,
                    'client_history': True,
                    'inventory': False,
                    'payroll': False,
                    'multi_location': False,
                    'custom_branding': False,
                    'whatsapp_notifications': False
                },
                'commercial_benefits': [
                    '1 Sucursal Principal',
                    'Hasta 4 Barberos/Estilistas',
                    'Agenda de Citas y Clientes',
                    'Punto de Venta (POS) y Caja Diaria',
                    'Soporte por Correo'
                ],
                'is_active': True
            },
            {
                'name': 'standard',
                'description': 'El plan más recomendado para negocios establecidos que necesitan control total de inventario, nómina con comisiones y métricas.',
                'price': 69.99,
                'annual_price': 699.88,
                'duration_month': 1,
                'stripe_price_id': '',
                'stripe_annual_price_id': '',
                'max_employees': 15,
                'max_users': 30,
                'allows_multiple_branches': False,
                'features': {
                    'appointments': True,
                    'reports': True,
                    'cash_register': True,
                    'client_history': True,
                    'inventory': True,
                    'payroll': True,
                    'multi_location': False,
                    'custom_branding': False,
                    'whatsapp_notifications': False
                },
                'commercial_benefits': [
                    '1 Sucursal Principal',
                    'Hasta 15 Barberos/Estilistas',
                    'Control Total de Inventario y Stock',
                    'Comisiones de Equipo y Nómina con TSS',
                    'Reportes Financieros y Rendimiento',
                    'Soporte Prioritario'
                ],
                'is_active': True
            },
            {
                'name': 'premium',
                'description': 'Para negocios en expansión con múltiples sucursales, recordatorios automáticos por WhatsApp y personalización de marca.',
                'price': 129.99,
                'annual_price': 1299.88,
                'duration_month': 1,
                'stripe_price_id': '',
                'stripe_annual_price_id': '',
                'max_employees': 35,
                'max_users': 70,
                'allows_multiple_branches': True,
                'features': {
                    'appointments': True,
                    'reports': True,
                    'cash_register': True,
                    'client_history': True,
                    'inventory': True,
                    'payroll': True,
                    'multi_location': True,
                    'custom_branding': True,
                    'export_reports': False,
                    'whatsapp_notifications': True
                },
                'commercial_benefits': [
                    'Hasta 3 Sucursales Incluidas',
                    'Hasta 35 Barberos/Estilistas',
                    'Todo lo del Plan Pro',
                    'Notificaciones y Recordatorios por WhatsApp',
                    'Personalización de Marca y Logo en Tickets',
                    'Soporte VIP por WhatsApp y Chat'
                ],
                'is_active': True
            },
            {
                'name': 'enterprise',
                'description': 'Para cadenas grandes y franquicias que requieren capacidad ilimitada, acceso a API/Webhooks y soporte dedicado 24/7.',
                'price': 199.00,
                'annual_price': 1990.00,
                'duration_month': 1,
                'stripe_price_id': '',
                'stripe_annual_price_id': '',
                'max_employees': 0,
                'max_users': 0,
                'allows_multiple_branches': True,
                'features': {
                    'appointments': True,
                    'reports': True,
                    'cash_register': True,
                    'client_history': True,
                    'inventory': True,
                    'payroll': True,
                    'multi_location': True,
                    'custom_branding': True,
                    'priority_support': True,
                    'export_reports': True,
                    'whatsapp_notifications': True,
                    'api_access': True
                },
                'commercial_benefits': [
                    'Sucursales y Barberos Ilimitados',
                    'Todo lo del Plan Business',
                    'Auditoría Avanzada y Acceso a API / Webhooks',
                    'Exportación Masiva de Datos Financieros',
                    'Acompañamiento y Soporte Dedicado 24/7'
                ],
                'is_active': True
            }
        ]

        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.update_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            action = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(f'{action} plan: {plan.name} (${plan.price}/mo, max_emp={plan.max_employees}, branches={plan.allows_multiple_branches})'))

        self.stdout.write(self.style.SUCCESS('Successfully updated all subscription plans with balanced configuration.'))
