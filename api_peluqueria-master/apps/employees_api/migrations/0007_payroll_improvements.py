# Migration to add snapshot field and unique constraint

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0006_clean_duplicate_periods'),
    ]

    operations = [
        # Add calculation_snapshot field
        migrations.AddField(
            model_name='payrollperiod',
            name='calculation_snapshot',
            field=models.JSONField(blank=True, help_text='Snapshot del cálculo al momento de aprobación', null=True),
        ),
        
        # Add unique constraint to prevent duplicate periods
        migrations.AddConstraint(
            model_name='payrollperiod',
            constraint=models.UniqueConstraint(
                fields=['employee', 'period_start', 'period_end'],
                name='unique_employee_period'
            ),
        ),
    ]
