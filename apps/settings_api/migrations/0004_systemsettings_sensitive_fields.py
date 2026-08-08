from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settings_api', '0003_remove_dead_code_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsettings',
            name='smtp_host',
            field=models.CharField(blank=True, max_length=255, verbose_name='Servidor SMTP'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='smtp_port',
            field=models.PositiveIntegerField(default=587, verbose_name='Puerto SMTP'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='smtp_username',
            field=models.CharField(blank=True, max_length=255, verbose_name='Usuario SMTP'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='smtp_password',
            field=models.CharField(blank=True, max_length=255, verbose_name='Password SMTP'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='from_email',
            field=models.EmailField(blank=True, max_length=254, verbose_name='Email remitente'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='from_name',
            field=models.CharField(blank=True, max_length=255, verbose_name='Nombre remitente'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='stripe_public_key',
            field=models.CharField(blank=True, max_length=255, verbose_name='Stripe public key'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='stripe_secret_key',
            field=models.CharField(blank=True, max_length=255, verbose_name='Stripe secret key'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='webhook_secret',
            field=models.CharField(blank=True, max_length=255, verbose_name='Stripe webhook secret'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='paypal_client_id',
            field=models.CharField(blank=True, max_length=255, verbose_name='PayPal client id'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='paypal_client_secret',
            field=models.CharField(blank=True, max_length=255, verbose_name='PayPal client secret'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='paypal_sandbox',
            field=models.BooleanField(default=True, verbose_name='PayPal sandbox'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='twilio_account_sid',
            field=models.CharField(blank=True, max_length=64, verbose_name='Twilio account SID'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='twilio_auth_token',
            field=models.CharField(blank=True, max_length=255, verbose_name='Twilio auth token'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='twilio_phone_number',
            field=models.CharField(blank=True, max_length=32, verbose_name='Twilio phone number'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='auto_upgrade_limits',
            field=models.BooleanField(default=False, verbose_name='Auto upgrade de limites'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='jwt_expiry_minutes',
            field=models.PositiveIntegerField(default=60, verbose_name='JWT expiry minutes'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='max_login_attempts',
            field=models.PositiveIntegerField(default=5, verbose_name='Max login attempts'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='password_min_length',
            field=models.PositiveIntegerField(default=8, verbose_name='Password min length'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='require_email_verification',
            field=models.BooleanField(default=True, verbose_name='Require email verification'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='enable_mfa',
            field=models.BooleanField(default=False, verbose_name='Enable MFA'),
        ),
    ]
