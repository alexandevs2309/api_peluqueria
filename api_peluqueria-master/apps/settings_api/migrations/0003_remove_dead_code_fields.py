# Generated manually - Remove dead code fields from BarbershopSettings

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('settings_api', '0002_settingsauditlog'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='barbershopsettings',
            name='default_commission_rate',
        ),
        migrations.RemoveField(
            model_name='barbershopsettings',
            name='default_fixed_salary',
        ),
        migrations.RemoveField(
            model_name='barbershopsettings',
            name='tax_rate',
        ),
        migrations.RemoveField(
            model_name='barbershopsettings',
            name='service_discount_limit',
        ),
        migrations.RemoveField(
            model_name='barbershopsettings',
            name='cancellation_policy_hours',
        ),
        migrations.RemoveField(
            model_name='barbershopsettings',
            name='late_arrival_grace_minutes',
        ),
        migrations.RemoveField(
            model_name='barbershopsettings',
            name='booking_advance_days',
        ),
    ]
