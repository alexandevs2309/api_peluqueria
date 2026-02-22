"""
Script para crear template de notificación de citas
Ejecutar: python manage.py shell < create_notification_template.py
"""
from apps.notifications_api.models import NotificationTemplate

template, created = NotificationTemplate.objects.get_or_create(
    notification_type='appointment_confirmation',
    type='email',
    defaults={
        'name': 'Confirmación de Cita',
        'subject': 'Cita Confirmada - {{appointment_date}}',
        'body': '''
Hola {{client_name}},

Tu cita ha sido confirmada:
- Fecha: {{appointment_date}}
- Hora: {{appointment_time}}
- Estilista: {{stylist_name}}
- Servicio: {{service_name}}

¡Te esperamos!
        ''',
        'is_html': False,
        'is_active': True,
        'available_variables': {
            'client_name': 'Nombre del cliente',
            'appointment_date': 'Fecha de la cita',
            'appointment_time': 'Hora de la cita',
            'stylist_name': 'Nombre del estilista',
            'service_name': 'Nombre del servicio'
        }
    }
)

if created:
    print(f"✅ Template creado: {template.name}")
else:
    print(f"ℹ️ Template ya existe: {template.name}")
