from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services_api', '0005_service_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='service',
            name='image',
            field=models.ImageField(blank=True, max_length=500, null=True, upload_to='services/'),
        ),
    ]
