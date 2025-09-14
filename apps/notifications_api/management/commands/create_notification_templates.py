from django.core.management.base import BaseCommand
from apps.notifications_api.models import NotificationTemplate

class Command(BaseCommand):
    help = 'Crear templates de notificación iniciales'

    def handle(self, *args, **options):
        templates_data = [
            # Email Templates
            {
                'name': 'Recordatorio de Cita',
                'type': 'email',
                'notification_type': 'appointment_reminder',
                'subject': 'Recordatorio: Tu cita en {{business_name}}',
                'body': '''
                <html>
                <body>
                    <h2>¡Hola {{client_name}}!</h2>
                    <p>Te recordamos tu cita programada:</p>
                    <div style="background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p><strong>Servicio:</strong> {{service_name}}</p>
                        <p><strong>Fecha y Hora:</strong> {{appointment_date}}</p>
                        <p><strong>Empleado:</strong> {{employee_name}}</p>
                        <p><strong>Dirección:</strong> {{business_address}}</p>
                    </div>
                    <p>Si necesitas reprogramar o cancelar tu cita, por favor contáctanos.</p>
                    <p>¡Te esperamos!</p>
                    <p><strong>{{business_name}}</strong></p>
                    <p>Tel: {{business_phone}} | Email: {{business_email}}</p>
                </body>
                </html>
                ''',
                'is_html': True,
                'available_variables': {
                    'client_name': 'Nombre del cliente',
                    'service_name': 'Nombre del servicio',
                    'appointment_date': 'Fecha y hora de la cita',
                    'employee_name': 'Nombre del empleado',
                    'business_name': 'Nombre del negocio',
                    'business_address': 'Dirección del negocio',
                    'business_phone': 'Teléfono del negocio',
                    'business_email': 'Email del negocio'
                }
            },
            {
                'name': 'Confirmación de Cita',
                'type': 'email',
                'notification_type': 'appointment_confirmation',
                'subject': 'Confirmación de cita en {{business_name}}',
                'body': '''
                <html>
                <body>
                    <h2>¡Hola {{client_name}}!</h2>
                    <p>Tu cita ha sido confirmada exitosamente:</p>
                    <div style="background-color: #e8f5e8; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p><strong>Servicio:</strong> {{service_name}}</p>
                        <p><strong>Fecha y Hora:</strong> {{appointment_date}}</p>
                        <p><strong>Empleado:</strong> {{employee_name}}</p>
                        <p><strong>Dirección:</strong> {{business_address}}</p>
                    </div>
                    <p>Si tienes alguna pregunta, no dudes en contactarnos.</p>
                    <p>¡Nos vemos pronto!</p>
                    <p><strong>{{business_name}}</strong></p>
                </body>
                </html>
                ''',
                'is_html': True,
                'available_variables': {
                    'client_name': 'Nombre del cliente',
                    'service_name': 'Nombre del servicio',
                    'appointment_date': 'Fecha y hora de la cita',
                    'employee_name': 'Nombre del empleado',
                    'business_name': 'Nombre del negocio',
                    'business_address': 'Dirección del negocio'
                }
            },
            {
                'name': 'Ganancias Disponibles',
                'type': 'email',
                'notification_type': 'earnings_available',
                'subject': 'Tus ganancias de {{fortnight_display}} están disponibles',
                'body': '''
                <html>
                <body>
                    <h2>¡Hola {{employee_name}}!</h2>
                    <p>Tus ganancias correspondientes a {{fortnight_display}} ya están disponibles:</p>
                    <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p><strong>Total de ganancias:</strong> ${{total_earnings}}</p>
                        <p><strong>Servicios realizados:</strong> {{total_services}}</p>
                        <p><strong>Comisiones:</strong> ${{total_commissions}}</p>
                        <p><strong>Propinas:</strong> ${{total_tips}}</p>
                    </div>
                    <p>El pago será procesado según el calendario establecido.</p>
                    <p>¡Gracias por tu excelente trabajo!</p>
                    <p><strong>{{business_name}}</strong></p>
                </body>
                </html>
                ''',
                'is_html': True,
                'available_variables': {
                    'employee_name': 'Nombre del empleado',
                    'fortnight_display': 'Período quincenal (ej: 1ra quincena enero 2025)',
                    'total_earnings': 'Ganancias totales',
                    'total_services': 'Número de servicios',
                    'total_commissions': 'Total de comisiones',
                    'total_tips': 'Total de propinas',
                    'business_name': 'Nombre del negocio'
                }
            },
            {
                'name': 'Pago Recibido',
                'type': 'email',
                'notification_type': 'payment_received',
                'subject': 'Confirmación de pago - {{business_name}}',
                'body': '''
                <html>
                <body>
                    <h2>¡Hola {{client_name}}!</h2>
                    <p>Hemos recibido tu pago exitosamente:</p>
                    <div style="background-color: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p><strong>Monto pagado:</strong> ${{amount}}</p>
                        <p><strong>Método de pago:</strong> {{payment_method}}</p>
                        <p><strong>Fecha:</strong> {{payment_date}}</p>
                        <p><strong>ID de transacción:</strong> {{transaction_id}}</p>
                    </div>
                    <p>¡Gracias por tu preferencia!</p>
                    <p><strong>{{business_name}}</strong></p>
                </body>
                </html>
                ''',
                'is_html': True,
                'available_variables': {
                    'client_name': 'Nombre del cliente',
                    'amount': 'Monto del pago',
                    'payment_method': 'Método de pago',
                    'payment_date': 'Fecha del pago',
                    'transaction_id': 'ID de transacción',
                    'business_name': 'Nombre del negocio'
                }
            },
            {
                'name': 'Alerta de Stock Bajo',
                'type': 'email',
                'notification_type': 'stock_alert',
                'subject': 'Alerta: Stock bajo de {{product_name}}',
                'body': '''
                <html>
                <body>
                    <h2>Alerta de Inventario</h2>
                    <p>El siguiente producto tiene stock bajo:</p>
                    <div style="background-color: #f8d7da; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p><strong>Producto:</strong> {{product_name}}</p>
                        <p><strong>Stock actual:</strong> {{current_stock}}</p>
                        <p><strong>Stock mínimo:</strong> {{minimum_stock}}</p>
                    </div>
                    <p>Por favor, considera reabastecer este producto.</p>
                    <p><strong>{{business_name}}</strong></p>
                </body>
                </html>
                ''',
                'is_html': True,
                'available_variables': {
                    'product_name': 'Nombre del producto',
                    'current_stock': 'Stock actual',
                    'minimum_stock': 'Stock mínimo requerido',
                    'business_name': 'Nombre del negocio'
                }
            },
            {
                'name': 'Suscripción Venciendo',
                'type': 'email',
                'notification_type': 'subscription_expiring',
                'subject': 'Tu suscripción vence pronto - {{business_name}}',
                'body': '''
                <html>
                <body>
                    <h2>¡Hola {{user_name}}!</h2>
                    <p>Tu suscripción está por vencer:</p>
                    <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p><strong>Plan actual:</strong> {{plan_name}}</p>
                        <p><strong>Fecha de vencimiento:</strong> {{expiration_date}}</p>
                        <p><strong>Días restantes:</strong> {{days_remaining}}</p>
                    </div>
                    <p>Para evitar interrupciones en el servicio, por favor renueva tu suscripción.</p>
                    <p><strong>{{business_name}}</strong></p>
                </body>
                </html>
                ''',
                'is_html': True,
                'available_variables': {
                    'user_name': 'Nombre del usuario',
                    'plan_name': 'Nombre del plan',
                    'expiration_date': 'Fecha de vencimiento',
                    'days_remaining': 'Días restantes',
                    'business_name': 'Nombre del negocio'
                }
            },
            {
                'name': 'Bienvenida',
                'type': 'email',
                'notification_type': 'welcome',
                'subject': '¡Bienvenido a {{business_name}}!',
                'body': '''
                <html>
                <body>
                    <h2>¡Hola {{user_name}}!</h2>
                    <p>¡Bienvenido a {{business_name}}!</p>
                    <p>Tu cuenta ha sido creada exitosamente. Ya puedes comenzar a disfrutar de nuestros servicios.</p>
                    <div style="background-color: #e8f5e8; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p><strong>Usuario:</strong> {{user_email}}</p>
                        <p><strong>Plan:</strong> {{plan_name}}</p>
                    </div>
                    <p>Si tienes alguna pregunta, no dudes en contactarnos.</p>
                    <p>¡Estamos aquí para ayudarte!</p>
                    <p><strong>{{business_name}}</strong></p>
                    <p>Tel: {{business_phone}} | Email: {{business_email}}</p>
                </body>
                </html>
                ''',
                'is_html': True,
                'available_variables': {
                    'user_name': 'Nombre del usuario',
                    'user_email': 'Email del usuario',
                    'plan_name': 'Nombre del plan',
                    'business_name': 'Nombre del negocio',
                    'business_phone': 'Teléfono del negocio',
                    'business_email': 'Email del negocio'
                }
            },

            # SMS Templates
            {
                'name': 'Recordatorio SMS',
                'type': 'sms',
                'notification_type': 'appointment_reminder',
                'subject': '',
                'body': 'Hola {{client_name}}! Recordatorio: Tu cita para {{service_name}} es mañana {{appointment_time}} con {{employee_name}}. {{business_name}} - {{business_phone}}',
                'is_html': False,
                'available_variables': {
                    'client_name': 'Nombre del cliente',
                    'service_name': 'Nombre del servicio',
                    'appointment_time': 'Hora de la cita',
                    'employee_name': 'Nombre del empleado',
                    'business_name': 'Nombre del negocio',
                    'business_phone': 'Teléfono del negocio'
                }
            },
            {
                'name': 'Confirmación SMS',
                'type': 'sms',
                'notification_type': 'appointment_confirmation',
                'subject': '',
                'body': 'Hola {{client_name}}! Tu cita para {{service_name}} el {{appointment_date}} ha sido confirmada. {{business_name}}',
                'is_html': False,
                'available_variables': {
                    'client_name': 'Nombre del cliente',
                    'service_name': 'Nombre del servicio',
                    'appointment_date': 'Fecha de la cita',
                    'business_name': 'Nombre del negocio'
                }
            },

            # Push Notification Templates
            {
                'name': 'Recordatorio Push',
                'type': 'push',
                'notification_type': 'appointment_reminder',
                'subject': 'Recordatorio de Cita',
                'body': 'Tu cita para {{service_name}} es mañana a las {{appointment_time}}',
                'is_html': False,
                'available_variables': {
                    'service_name': 'Nombre del servicio',
                    'appointment_time': 'Hora de la cita'
                }
            },
            {
                'name': 'Ganancias Push',
                'type': 'push',
                'notification_type': 'earnings_available',
                'subject': 'Ganancias Disponibles',
                'body': 'Tus ganancias de ${{total_earnings}} para {{fortnight_display}} están listas',
                'is_html': False,
                'available_variables': {
                    'total_earnings': 'Ganancias totales',
                    'fortnight_display': 'Período quincenal'
                }
            }
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates_data:
            template, created = NotificationTemplate.objects.get_or_create(
                name=template_data['name'],
                defaults=template_data
            )

            if created:
                created_count += 1
                self.stdout.write(f'Creado: {template.name}')
            else:
                # Update existing template
                for key, value in template_data.items():
                    setattr(template, key, value)
                template.save()
                updated_count += 1
                self.stdout.write(f'Actualizado: {template.name}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Proceso completado. Creados: {created_count}, Actualizados: {updated_count}'
            )
        )
