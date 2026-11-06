from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0033_add_payroll_config_permission'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollperiod',
            name='christmas_bonus',
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=10,
                help_text='Bono navideño (importe manual o calculado)',
            ),
        ),
        migrations.AddField(
            model_name='payrolldeduction',
            name='loan',
            field=models.ForeignKey(
                'employees_api.Loan', null=True, blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='payroll_deductions',
            ),
        ),
    ]
