from django.db import migrations, models
from decimal import Decimal


def migrate_salary_data(apps, schema_editor):
    """
    Migra salary_amount (quincenal) a contractual_monthly_salary (mensual).
    Asume que salary_amount era quincenal, por lo tanto: mensual = quincenal * 2
    """
    Employee = apps.get_model('employees_api', 'Employee')
    
    updated_count = 0
    for employee in Employee.objects.all():
        if employee.salary_amount and employee.salary_amount > 0:
            # Convertir quincenal a mensual
            employee.contractual_monthly_salary = employee.salary_amount * Decimal('2')
            employee.save(update_fields=['contractual_monthly_salary'])
            updated_count += 1
    
    print(f"✅ Migrados {updated_count} empleados: salary_amount * 2 → contractual_monthly_salary")


def reverse_migration(apps, schema_editor):
    """Reversión: copiar contractual_monthly_salary / 2 → salary_amount"""
    Employee = apps.get_model('employees_api', 'Employee')
    
    for employee in Employee.objects.all():
        if employee.contractual_monthly_salary and employee.contractual_monthly_salary > 0:
            employee.salary_amount = employee.contractual_monthly_salary / Decimal('2')
            employee.save(update_fields=['salary_amount'])


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0006_fortnightsummary_afp_deduction_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='contractual_monthly_salary',
            field=models.DecimalField(
                decimal_places=2,
                default=0.0,
                help_text='Salario mensual contractual (fuente de verdad para cálculos de nómina)',
                max_digits=10
            ),
        ),
        migrations.AlterField(
            model_name='employee',
            name='salary_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=0.0,
                help_text='[DEPRECATED] Usar contractual_monthly_salary. Anteriormente: sueldo quincenal',
                max_digits=10
            ),
        ),
        migrations.RunPython(migrate_salary_data, reverse_migration),
    ]
