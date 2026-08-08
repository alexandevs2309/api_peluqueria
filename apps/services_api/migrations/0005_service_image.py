# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services_api', '0004_alter_service_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='services/'),
        ),
    ]
