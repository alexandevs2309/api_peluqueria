from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0036_reclassify_deduction_sources'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrolldeduction',
            name='original_amount',
            field=models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='payrolldeduction',
            name='modified_by',
            field=models.ForeignKey('auth.User', null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payroll_deductions_modified'),
        ),
        migrations.AddField(
            model_name='payrolldeduction',
            name='modified_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
