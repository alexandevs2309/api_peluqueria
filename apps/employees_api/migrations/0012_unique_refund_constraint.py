from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0011_commissionadjustment'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='commissionadjustment',
            constraint=models.UniqueConstraint(
                condition=models.Q(reason='refund'),
                fields=['sale', 'reason'],
                name='unique_refund_per_sale'
            ),
        ),
    ]
