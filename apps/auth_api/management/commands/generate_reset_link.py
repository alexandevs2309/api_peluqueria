from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

User = get_user_model()

class Command(BaseCommand):
    help = 'Genera un enlace de recuperación de contraseña para testing'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email del usuario')

    def handle(self, *args, **options):
        email = options['email']
        
        try:
            user = User.objects.get(email=email)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"http://localhost:4200/auth/reset-password/{uid}/{token}"
            
            self.stdout.write(self.style.SUCCESS(f'\n✅ Enlace de recuperación generado para {email}:\n'))
            self.stdout.write(self.style.WARNING(f'{reset_url}\n'))
            self.stdout.write(self.style.SUCCESS('Copia este enlace en tu navegador para probar el reset de contraseña.\n'))
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Usuario con email {email} no encontrado'))
