"""
Management command para garantizar que exista un superadmin en producción.
Se ejecuta en el startup command de Render:
    python manage.py migrate && python manage.py ensure_superadmin && gunicorn ...

Variables de entorno requeridas:
    SUPERADMIN_EMAIL    — email del superadmin
    SUPERADMIN_PASSWORD — contraseña del superadmin
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Crea o actualiza el superadmin desde variables de entorno'

    def handle(self, *args, **options):
        email = os.environ.get('SUPERADMIN_EMAIL', '').strip()
        password = os.environ.get('SUPERADMIN_PASSWORD', '').strip()

        if not email or not password:
            self.stdout.write(self.style.WARNING(
                '[ensure_superadmin] SUPERADMIN_EMAIL o SUPERADMIN_PASSWORD no definidos — omitiendo.'
            ))
            return

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'full_name': 'Platform Admin',
                'is_superuser': True,
                'is_staff': True,
                'is_active': True,
                'tenant': None,
            }
        )

        if created:
            user.set_password(password)
            user.save(update_fields=['password'])
            self.stdout.write(self.style.SUCCESS(
                f'[ensure_superadmin] Superadmin creado: {email}'
            ))
        else:
            # Garantizar flags correctos aunque el usuario ya existiera
            changed = False
            if not user.is_superuser:
                user.is_superuser = True
                changed = True
            if not user.is_staff:
                user.is_staff = True
                changed = True
            if not user.is_active:
                user.is_active = True
                changed = True
            if user.tenant is not None:
                user.tenant = None
                changed = True
            if changed:
                user.save(update_fields=['is_superuser', 'is_staff', 'is_active', 'tenant'])
            self.stdout.write(self.style.SUCCESS(
                f'[ensure_superadmin] Superadmin ya existe: {email} (flags verificados)'
            ))
