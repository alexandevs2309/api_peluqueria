from django.db import migrations


def reclassify_sources(apps, schema_editor):
    PayrollDeduction = apps.get_model('employees_api', 'PayrollDeduction')
    # Deducciones automáticas creadas antes de la migración 0035 recibieron
    # source='manual' por defecto. Reclassificar por prefijo de descripción.
    for d in PayrollDeduction.objects.filter(is_automatic=True):
        desc = (d.description or '')
        if desc.startswith('[Asistencia]'):
            d.source = 'auto_attendance'
        elif desc.startswith('[Préstamo]') or desc.startswith('[Prestamo]'):
            d.source = 'auto_loan'
        elif desc.startswith('[Config]'):
            d.source = 'auto_config'
        else:
            d.source = 'auto_config' if d.is_automatic else 'manual'
        d.save(update_fields=['source'])


def reverse_reclassify(apps, schema_editor):
    PayrollDeduction = apps.get_model('employees_api', 'PayrollDeduction')
    PayrollDeduction.objects.filter(is_automatic=True).update(source='manual')


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0035_payroll_deduction_source'),
    ]

    operations = [
        migrations.RunPython(reclassify_sources, reverse_code=reverse_reclassify),
    ]
