from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing_api', '0009_populate_invoice_tenant'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='paypal_order_id',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='PayPal order ID para idempotencia a nivel DB',
                max_length=255,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('paid', 'Paid'),
                    ('failed', 'Failed'),
                    ('canceled', 'Canceled'),
                    ('refunded', 'Refunded'),
                ],
                default='pending',
                max_length=50,
            ),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(fields=['paypal_order_id'], name='billing_api_invoice_paypal_order_id_idx'),
        ),
    ]
