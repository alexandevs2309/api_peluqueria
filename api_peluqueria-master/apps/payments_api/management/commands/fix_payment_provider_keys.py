from django.core.management.base import BaseCommand
from django.core import signing
from apps.payments_api.models import PaymentProvider


class Command(BaseCommand):
    help = "Repara claves de PaymentProvider que quedaron doble-cifradas por un bug en save()"

    def handle(self, *args, **options):
        fixed_api = 0
        fixed_webhook = 0

        for provider in PaymentProvider.objects.all():
            changed = False

            if provider.api_key:
                raw_api = self._unwrap_all(provider.api_key)
                if raw_api != provider.api_key:
                    provider.api_key = provider.encrypt(raw_api)
                    fixed_api += 1
                    changed = True

            if provider.webhook_secret:
                raw_secret = self._unwrap_all(provider.webhook_secret)
                if raw_secret != provider.webhook_secret:
                    provider.webhook_secret = provider.encrypt(raw_secret)
                    fixed_webhook += 1
                    changed = True

            if changed:
                provider.save(update_fields=['api_key', 'webhook_secret'])

        self.stdout.write(self.style.SUCCESS(
            f"Reparadas {fixed_api} api_key(s) y {fixed_webhook} webhook_secret(s)"
        ))

    def _unwrap_all(self, value):
        raw = value
        for _ in range(3):
            try:
                decrypted = signing.loads(raw, salt="payment_provider")
                raw = decrypted
            except (signing.BadSignature, signing.SignatureExpired):
                break
        return raw
