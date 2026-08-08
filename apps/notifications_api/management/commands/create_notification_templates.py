from django.core.management.base import BaseCommand, CommandError
from apps.notifications_api.models import NotificationTemplate

class Command(BaseCommand):
    help = 'Crear templates básicos de notificaciones (globales o por tenant)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=int,
            help='ID del tenant para crear templates específicos (omite para templates globales)',
        )

    def handle(self, *args, **options):
        tenant_id = options.get('tenant')
        tenant = None
        if tenant_id:
            from apps.tenants_api.models import Tenant
            try:
                tenant = Tenant.objects.get(id=tenant_id)
            except Tenant.DoesNotExist:
                raise CommandError(f'Tenant con ID {tenant_id} no existe.')

        wa_templates = [
            {
                'name': 'WhatsApp - Confirmación de Cita',
                'type': 'whatsapp',
                'notification_type': 'appointment_confirmation',
                'subject': 'Cita Confirmada',
                'body': '''Hola {{client_name}},

Tu cita ha sido confirmada para el {{appointment_date}} a las {{appointment_time}}.

Estilista: {{stylist_name}}
Servicio: {{service_name}}

¡Te esperamos!''',
                'available_variables': {
                    'client_name': 'Nombre del cliente',
                    'appointment_date': 'Fecha de la cita',
                    'appointment_time': 'Hora de la cita',
                    'stylist_name': 'Nombre del estilista',
                    'service_name': 'Nombre del servicio'
                }
            },
            {
                'name': 'WhatsApp - Recordatorio de Cita',
                'type': 'whatsapp',
                'notification_type': 'appointment_reminder',
                'subject': 'Recordatorio de Cita',
                'body': '''Hola {{client_name}},

Te recordamos que tienes una cita mañana {{appointment_date}} a las {{appointment_time}}.

Estilista: {{stylist_name}}
Servicio: {{service_name}}

Si necesitas cancelar o reprogramar, contáctanos.''',
                'available_variables': {
                    'client_name': 'Nombre del cliente',
                    'appointment_date': 'Fecha de la cita',
                    'appointment_time': 'Hora de la cita',
                    'stylist_name': 'Nombre del estilista',
                    'service_name': 'Nombre del servicio'
                }
            },
            {
                'name': 'WhatsApp - Ganancias Disponibles',
                'type': 'whatsapp',
                'notification_type': 'earnings_available',
                'subject': 'Nueva venta registrada',
                'body': '''Hola {{employee_name}},

Se registró una venta por {{sale_amount}} el {{sale_date}}.

Tu comisión ({{commission_rate}}%) irá a tu próximo pago.

¡Sigue así!''',
                'available_variables': {
                    'employee_name': 'Nombre del empleado',
                    'sale_amount': 'Monto de la venta',
                    'sale_date': 'Fecha de la venta',
                    'commission_rate': 'Porcentaje de comisión'
                }
            },
            {
                'name': 'WhatsApp - Alerta de Stock Bajo',
                'type': 'whatsapp',
                'notification_type': 'stock_alert',
                'subject': 'Stock Bajo',
                'body': '''Alerta de inventario:

"{{product_name}}" tiene stock bajo.

Stock actual: {{current_stock}}
Stock mínimo: {{min_stock}}

Recomendamos hacer pedido pronto.''',
                'available_variables': {
                    'product_name': 'Nombre del producto',
                    'current_stock': 'Stock actual',
                    'min_stock': 'Stock mínimo',
                    'supplier': 'Proveedor'
                }
            },
            {
                'name': 'WhatsApp - Suscripción por Vencer',
                'type': 'whatsapp',
                'notification_type': 'subscription_expiring',
                'subject': 'Suscripción por vencer',
                'body': '''Hola {{tenant_name}},

Tu suscripción al plan {{plan_name}} vence el {{expiry_date}} ({{days_remaining}} días).

Renueva antes para evitar interrupción del servicio.''',
                'available_variables': {
                    'tenant_name': 'Nombre del negocio',
                    'plan_name': 'Nombre del plan',
                    'expiry_date': 'Fecha de vencimiento',
                    'days_remaining': 'Días restantes'
                }
            }
        ]

        templates = [
            {
                'name': 'Confirmación de Cita',
                'type': 'email',
                'notification_type': 'appointment_confirmation',
                'subject': 'Cita Confirmada - {{appointment_date}} {{appointment_time}}',
                'body': '''Hola {{client_name}},

Tu cita ha sido confirmada para el {{appointment_date}} a las {{appointment_time}}.

Detalles:
- Estilista: {{stylist_name}}
- Servicio: {{service_name}}

¡Te esperamos!

Saludos,
Equipo de la Barbería''',
                'available_variables': {
                    'client_name': 'Nombre del cliente',
                    'appointment_date': 'Fecha de la cita',
                    'appointment_time': 'Hora de la cita',
                    'stylist_name': 'Nombre del estilista',
                    'service_name': 'Nombre del servicio'
                }
            },
            {
                'name': 'Recordatorio de Cita',
                'type': 'email',
                'notification_type': 'appointment_reminder',
                'subject': 'Recordatorio: Cita Mañana - {{appointment_time}}',
                'body': '''Hola {{client_name}},

Te recordamos que tienes una cita mañana {{appointment_date}} a las {{appointment_time}}.

Detalles:
- Estilista: {{stylist_name}}
- Servicio: {{service_name}}

Si necesitas cancelar o reprogramar, contáctanos.

Saludos,
Equipo de la Barbería''',
                'available_variables': {
                    'client_name': 'Nombre del cliente',
                    'appointment_date': 'Fecha de la cita',
                    'appointment_time': 'Hora de la cita',
                    'stylist_name': 'Nombre del estilista',
                    'service_name': 'Nombre del servicio'
                }
            },
            {
                'name': 'Ganancias Disponibles',
                'type': 'email',
                'notification_type': 'earnings_available',
                'subject': 'Nueva Venta Registrada - {{sale_amount}}',
                'body': '''Hola {{employee_name}},

Se ha registrado una nueva venta por {{sale_amount}} el {{sale_date}}.

Tu comisión ({{commission_rate}}%) será calculada en tu próximo pago quincenal.

¡Excelente trabajo!

Saludos,
Administración''',
                'available_variables': {
                    'employee_name': 'Nombre del empleado',
                    'sale_amount': 'Monto de la venta',
                    'sale_date': 'Fecha de la venta',
                    'commission_rate': 'Porcentaje de comisión'
                }
            },
            {
                'name': 'Alerta de Stock Bajo',
                'type': 'email',
                'notification_type': 'stock_alert',
                'subject': 'Alerta: Stock Bajo - {{product_name}}',
                'body': '''Atención,

El producto "{{product_name}}" tiene stock bajo:

- Stock actual: {{current_stock}}
- Stock mínimo: {{min_stock}}
- Proveedor: {{supplier}}

Es recomendable realizar un pedido pronto.

Sistema de Inventario''',
                'available_variables': {
                    'product_name': 'Nombre del producto',
                    'current_stock': 'Stock actual',
                    'min_stock': 'Stock mínimo',
                    'supplier': 'Proveedor'
                }
            },
            {
                'name': 'Suscripción por Vencer',
                'type': 'email',
                'notification_type': 'subscription_expiring',
                'subject': 'Suscripción Venciendo - {{days_remaining}} días restantes',
                'body': '''Hola {{tenant_name}},

Tu suscripción al plan {{plan_name}} vencerá el {{expiry_date}}.

Días restantes: {{days_remaining}}

Para evitar interrupciones en el servicio, renueva tu suscripción antes de la fecha de vencimiento.

Equipo de Soporte''',
                'available_variables': {
                    'tenant_name': 'Nombre del negocio',
                    'plan_name': 'Nombre del plan',
                    'expiry_date': 'Fecha de vencimiento',
                    'days_remaining': 'Días restantes'
                }
            }
        ]

        created_count = 0
        all_templates = templates + wa_templates
        for template_data in all_templates:
            template, created = NotificationTemplate.objects.get_or_create(
                name=template_data['name'],
                tenant=tenant,
                defaults=template_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Template creado: {template.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Template ya existe: {template.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Proceso completado. {created_count} templates creados.')
        )