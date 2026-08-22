from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settings_api', '0013_alter_barbershopsettings_currency'),
    ]

    operations = [
        migrations.AddField(
            model_name='barbershopsettings',
            name='whatsapp_webhook_secret',
            field=models.CharField(blank=True, help_text='Secret for Evolution API webhook signature verification', max_length=255),
        ),
    ]
