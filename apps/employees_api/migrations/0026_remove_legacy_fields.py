"""
ADR-001 — Eliminar campos legacy del modelo Employee.

- specialties: JSONField que el ADR prohíbe (no usar JSONField para especialidades).
- legacy_specialty_text: campo transitorio de migración que ya cumplió su propósito.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0025_refactor_employee_model_20250704_4'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='employee',
            name='specialties',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='legacy_specialty_text',
        ),
    ]
