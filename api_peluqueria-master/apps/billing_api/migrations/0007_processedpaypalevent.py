# Generated migration for PayPal event idempotency

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing_api', '0006_invoice_tenant'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProcessedPayPalEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('paypal_event_id', models.CharField(db_index=True, max_length=255, unique=True)),
                ('event_type', models.CharField(db_index=True, max_length=100)),
                ('processed_at', models.DateTimeField(auto_now_add=True)),
                ('payload', models.JSONField()),
            ],
            options={
                'ordering': ['-processed_at'],
            },
        ),
        migrations.AddIndex(
            model_name='processedpaypalevent',
            index=models.Index(fields=['paypal_event_id'], name='billing_api_paypal_event_id_idx'),
        ),
        migrations.AddIndex(
            model_name='processedpaypalevent',
            index=models.Index(fields=['event_type', 'processed_at'], name='billing_api_paypal_event_type_idx'),
        ),
    ]
