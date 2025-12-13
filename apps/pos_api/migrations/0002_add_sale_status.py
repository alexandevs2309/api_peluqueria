from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('pos_api', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pendiente'),
                    ('completed', 'Completada'),
                    ('cancelled', 'Cancelada'),
                    ('refunded', 'Reembolsada')
                ],
                default='completed',
                max_length=20
            ),
        ),
    ]