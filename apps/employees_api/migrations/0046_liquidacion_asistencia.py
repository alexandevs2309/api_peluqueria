from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0045_liquidacion'),
    ]

    operations = [
        migrations.AddField(
            model_name='liquidacion',
            name='asistencia_economica',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, help_text='Asistencia económica Art. 82 (litigio)'),
        ),
    ]
