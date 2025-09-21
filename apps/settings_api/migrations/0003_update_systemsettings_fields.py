from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('settings_api', '0002_systemsettings'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='systemsettings',
            name='backup_frequency',
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='platform_domain',
            field=models.CharField(blank=True, max_length=255, verbose_name='Dominio principal'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='supported_languages',
            field=models.JSONField(default=list, verbose_name='Idiomas habilitados'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='platform_commission_rate',
            field=models.DecimalField(decimal_places=2, default=5.0, max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(50)], verbose_name='Comisión de plataforma (%)'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='basic_plan_max_employees',
            field=models.PositiveIntegerField(default=5, verbose_name='Plan básico - máx. empleados'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='premium_plan_max_employees',
            field=models.PositiveIntegerField(default=25, verbose_name='Plan premium - máx. empleados'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='enterprise_plan_max_employees',
            field=models.PositiveIntegerField(default=999, verbose_name='Plan enterprise - máx. empleados'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='stripe_enabled',
            field=models.BooleanField(default=True, verbose_name='Stripe habilitado'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='paypal_enabled',
            field=models.BooleanField(default=False, verbose_name='PayPal habilitado'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='twilio_enabled',
            field=models.BooleanField(default=False, verbose_name='SMS (Twilio) habilitado'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='sendgrid_enabled',
            field=models.BooleanField(default=True, verbose_name='Email (SendGrid) habilitado'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='aws_s3_enabled',
            field=models.BooleanField(default=True, verbose_name='Almacenamiento (AWS S3) habilitado'),
        ),
    ]