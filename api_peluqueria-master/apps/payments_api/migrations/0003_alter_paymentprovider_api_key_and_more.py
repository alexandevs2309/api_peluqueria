from django.db import migrations, models
from django.core import signing


def encrypt_existing_keys(apps, schema_editor):
    PaymentProvider = apps.get_model("payments_api", "PaymentProvider")
    for provider in PaymentProvider.objects.all():
        changed = False
        if provider.api_key and not provider.api_key.startswith("gAAAAA"):
            provider.api_key = signing.dumps(provider.api_key, salt="payment_provider", compress=True)
            changed = True
        if provider.webhook_secret and not provider.webhook_secret.startswith("gAAAAA"):
            provider.webhook_secret = signing.dumps(provider.webhook_secret, salt="payment_provider", compress=True)
            changed = True
        if changed:
            provider.save(update_fields=["api_key", "webhook_secret"])


class Migration(migrations.Migration):

    dependencies = [
        ("payments_api", "0002_payment_tenant"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paymentprovider",
            name="api_key",
            field=models.CharField(
                blank=True,
                editable=False,
                help_text="Encriptado automaticamente. No modificar manualmente.",
                max_length=512,
            ),
        ),
        migrations.AlterField(
            model_name="paymentprovider",
            name="webhook_secret",
            field=models.CharField(
                blank=True,
                editable=False,
                help_text="Encriptado automaticamente. No modificar manualmente.",
                max_length=512,
            ),
        ),
        migrations.RunPython(encrypt_existing_keys, migrations.RunPython.noop),
    ]
