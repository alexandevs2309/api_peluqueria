from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settings_api', '0004_systemsettings_sensitive_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsettings',
            name='login_lockout_minutes',
            field=models.PositiveIntegerField(default=5, verbose_name='Login lockout minutes'),
        ),
    ]
