# Generated migration for EmployeeCompensationHistory

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0007_payroll_improvements'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EmployeeCompensationHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_type', models.CharField(
                    choices=[
                        ('fixed', 'Sueldo Fijo'),
                        ('commission', 'Comisión'),
                        ('mixed', 'Mixto (Sueldo + Comisión)')
                    ],
                    max_length=10
                )),
                ('fixed_salary', models.DecimalField(
                    decimal_places=2,
                    max_digits=10,
                    validators=[django.core.validators.MinValueValidator(Decimal('0.00'))]
                )),
                ('commission_rate', models.DecimalField(
                    decimal_places=2,
                    max_digits=5,
                    validators=[
                        django.core.validators.MinValueValidator(Decimal('0.00')),
                        django.core.validators.MaxValueValidator(Decimal('100.00'))
                    ]
                )),
                ('effective_date', models.DateField(help_text='Fecha desde la cual aplican estas condiciones')),
                ('end_date', models.DateField(
                    blank=True,
                    help_text='Fecha hasta la cual aplicaron estas condiciones (null = vigente)',
                    null=True
                )),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('change_reason', models.TextField(blank=True)),
                ('employee_snapshot', models.JSONField(default=dict, help_text='Snapshot completo del empleado al momento del cambio')),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='compensation_changes_created',
                    to=settings.AUTH_USER_MODEL
                )),
                ('employee', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='compensation_history',
                    to='employees_api.employee'
                )),
            ],
            options={
                'ordering': ['-effective_date', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='employeecompensationhistory',
            index=models.Index(fields=['employee', 'effective_date'], name='employees_a_employe_idx'),
        ),
        migrations.AddIndex(
            model_name='employeecompensationhistory',
            index=models.Index(fields=['employee', 'end_date'], name='employees_a_employe_end_idx'),
        ),
        migrations.AddIndex(
            model_name='employeecompensationhistory',
            index=models.Index(fields=['effective_date'], name='employees_a_effecti_idx'),
        ),
        migrations.AddConstraint(
            model_name='employeecompensationhistory',
            constraint=models.CheckConstraint(
                condition=models.Q(('end_date__isnull', True), ('end_date__gte', models.F('effective_date')), _connector='OR'),
                name='valid_date_range'
            ),
        ),
    ]
