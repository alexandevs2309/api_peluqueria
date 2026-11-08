from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0043_vacation'),
    ]

    operations = [
        migrations.AddField(model_name='vacation', name='termination_type', field=models.CharField(blank=True, choices=[('desahucio', 'Desahucio'), ('despido_causa', 'Despido con causa'), ('despido_sin_causa', 'Despido sin causa'), ('dimision_causa', 'Dimisión con causa'), ('dimision_sin_causa', 'Dimisión sin causa'), ('mutuo_acuerdo', 'Mutuo acuerdo')], max_length=20, null=True)),
        migrations.AddField(model_name='vacation', name='payroll_period', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='vacations_paid', to='employees_api.payrollperiod')),
        migrations.AddField(model_name='vacation', name='daily_salary', field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
    ]
