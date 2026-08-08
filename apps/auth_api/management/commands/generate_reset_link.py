from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from apps.tenants_api.models import Tenant

User = get_user_model()


class Command(BaseCommand):
    help = 'Genera un enlace de recuperacion de contrasena para testing'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email del usuario')
        parser.add_argument('--tenant', type=str, help='Subdominio del tenant', required=False)

    def handle(self, *args, **options):
        email = options['email']
        tenant_subdomain = (options.get('tenant') or '').strip().lower() or None

        user = None
        if tenant_subdomain:
            tenant = Tenant.objects.filter(subdomain=tenant_subdomain).first()
            if tenant:
                user = User.objects.filter(email=email, tenant=tenant).first()
        else:
            users = list(User.objects.filter(email=email).select_related('tenant'))
            if len(users) > 1:
                tenants = ", ".join(sorted({u.tenant.subdomain for u in users if u.tenant}))
                self.stdout.write(self.style.ERROR(
                    f'Email con multiples tenants. Usa --tenant. Opciones: {tenants}'
                ))
                return
            if users:
                user = users[0]

        if not user:
            self.stdout.write(self.style.ERROR(f'Usuario con email {email} no encontrado'))
            return

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f"http://localhost:4200/auth/reset-password/{uid}/{token}"

        self.stdout.write(self.style.SUCCESS(f'\nEnlace de recuperacion generado para {email}:\n'))
        self.stdout.write(self.style.WARNING(f'{reset_url}\n'))
        self.stdout.write(self.style.SUCCESS('Copia este enlace en tu navegador para probar el reset.\n'))
