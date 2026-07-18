from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants_api', '0005_tenant_access_until'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenant',
            name='grace_period_until',
            field=models.DateTimeField(blank=True, help_text='Fecha/hora límite del periodo de gracia por pago fallido', null=True),
        ),
        migrations.AddField(
            model_name='tenant',
            name='last_payment_failed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tenant',
            name='payment_failure_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='tenant',
            name='subscription_status',
            field=models.CharField(choices=[('trial', 'Trial'), ('active', 'Active'), ('past_due', 'Past Due'), ('suspended', 'Suspended'), ('cancelled', 'Cancelled')], default='trial', max_length=20),
        ),
    ]
