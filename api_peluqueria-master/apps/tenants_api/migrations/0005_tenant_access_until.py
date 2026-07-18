from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants_api', '0004_tenant_locale_config'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenant',
            name='access_until',
            field=models.DateTimeField(blank=True, help_text='Fecha/hora límite de acceso para planes pagos', null=True),
        ),
    ]

