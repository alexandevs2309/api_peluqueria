from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.audit_api.utils import create_audit_log

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample audit logs for testing'

    def handle(self, *args, **options):
        # Get or create a test user
        user, created = User.objects.get_or_create(
            email='admin@test.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'Test',
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        if created:
            user.set_password('admin123')
            user.save()
            self.stdout.write(f'Created test user: {user.email}')

        # Create sample logs
        sample_logs = [
            {
                'action': 'LOGIN',
                'description': 'Usuario inició sesión exitosamente',
                'source': 'AUTH',
                'ip_address': '192.168.1.100'
            },
            {
                'action': 'CREATE',
                'description': 'Nuevo plan de suscripción creado: Plan Premium',
                'source': 'SUBSCRIPTIONS',
                'ip_address': '192.168.1.100'
            },
            {
                'action': 'UPDATE',
                'description': 'Configuración del sistema actualizada',
                'source': 'SETTINGS',
                'ip_address': '192.168.1.100'
            },
            {
                'action': 'DELETE',
                'description': 'Usuario eliminado del sistema',
                'source': 'USERS',
                'ip_address': '192.168.1.100'
            },
            {
                'action': 'ADMIN_ACTION',
                'description': 'Acceso al panel de administración',
                'source': 'SYSTEM',
                'ip_address': '192.168.1.100'
            }
        ]

        for log_data in sample_logs:
            create_audit_log(
                user=user,
                action=log_data['action'],
                description=log_data['description'],
                source=log_data['source'],
                ip_address=log_data['ip_address'],
                user_agent='Mozilla/5.0 (Test Browser)'
            )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {len(sample_logs)} sample audit logs')
        )