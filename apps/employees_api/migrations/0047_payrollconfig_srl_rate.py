from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0046_liquidacion_asistencia'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollconfiguration',
            name='srl_rate',
            field=models.DecimalField(decimal_places=2, default=Decimal('1.20'), help_text='Tasa SRL (riesgo laboral, 1.00-1.30%)', max_digits=5),
        ),
    ]
