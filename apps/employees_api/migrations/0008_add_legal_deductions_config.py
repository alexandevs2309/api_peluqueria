# Generated migration for legal deductions configuration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0007_add_contractual_salary'),
        ('tenants_api', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='apply_afp',
            field=models.BooleanField(default=False, help_text='Aplicar descuento AFP (2.87%)'),
        ),
        migrations.AddField(
            model_name='employee',
            name='apply_sfs',
            field=models.BooleanField(default=False, help_text='Aplicar descuento SFS (3.04%)'),
        ),
        migrations.AddField(
            model_name='employee',
            name='apply_isr',
            field=models.BooleanField(default=False, help_text='Aplicar descuento ISR'),
        ),
    ]
