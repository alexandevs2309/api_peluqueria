# Generated migration for tenant locale configuration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants_api', '0003_tenant_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenant',
            name='locale',
            field=models.CharField(default='es-DO', help_text='Locale code (e.g., es-DO, en-US)', max_length=10),
        ),
        migrations.AddField(
            model_name='tenant',
            name='currency',
            field=models.CharField(default='DOP', help_text='Currency code (ISO 4217)', max_length=3),
        ),
        migrations.AddField(
            model_name='tenant',
            name='date_format',
            field=models.CharField(default='dd/MM/yyyy', help_text='Date format for display', max_length=20),
        ),
        migrations.AddField(
            model_name='tenant',
            name='time_zone',
            field=models.CharField(default='America/Santo_Domingo', help_text='IANA timezone', max_length=50),
        ),
    ]
