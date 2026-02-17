# Generated migration for adding status field and immutability to Sale model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos_api', '0004_change_sale_period_to_payroll'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('confirmed', 'Confirmed'),
                    ('void', 'Void'),
                    ('refunded', 'Refunded')
                ],
                default='confirmed',
                max_length=20
            ),
        ),
        migrations.AddIndex(
            model_name='sale',
            index=models.Index(fields=['status'], name='pos_api_sal_status_idx'),
        ),
    ]
