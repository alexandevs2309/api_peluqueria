from django.core.management.base import BaseCommand
from django.core import signing
from apps.settings_api.models import SystemSettings, SECRET_FIELDS


class Command(BaseCommand):
    help = "Cifra los campos secretos de SystemSettings que estén en texto plano"

    def handle(self, *args, **options):
        settings = SystemSettings.get_settings()
        changed = False

        for field in SECRET_FIELDS:
            value = getattr(settings, field, '')
            if not value:
                continue
            if value and SystemSettings._is_encrypted(value):
                continue
            encrypted = signing.dumps(value, salt="system_settings", compress=True)
            setattr(settings, field, encrypted)
            changed = True
            self.stdout.write(f"  Cifrado: {field}")

        if changed:
            settings.save(update_fields=SECRET_FIELDS)
            self.stdout.write(self.style.SUCCESS("Secretos cifrados correctamente"))
        else:
            self.stdout.write("Todos los secretos ya estaban cifrados")
