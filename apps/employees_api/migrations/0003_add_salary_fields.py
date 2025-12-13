from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0002_earning_employeeservice_paymentreceipt_workschedule_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='salary_type',
            field=models.CharField(
                choices=[('fixed', 'Sueldo Fijo'), ('commission', 'Comisión'), ('mixed', 'Mixto (Sueldo + Comisión)')],
                default='commission',
                help_text='Tipo de pago: fixed, commission, mixed',
                max_length=10
            ),
        ),
        migrations.AddField(
            model_name='employee',
            name='salary_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=0.0,
                help_text='Sueldo fijo quincenal',
                max_digits=10
            ),
        ),
        migrations.AddField(
            model_name='employee',
            name='commission_percentage',
            field=models.DecimalField(
                decimal_places=2,
                default=40.0,
                help_text='Porcentaje de comisión (ej: 40.00 para 40%)',
                max_digits=5
            ),
        ),
    ]