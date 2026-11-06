from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0034_christmas_bonus_and_loan_fk'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrolldeduction',
            name='source',
            field=models.CharField(
                choices=[
                    ('auto_attendance', 'Automática - Asistencia'),
                    ('auto_loan', 'Automática - Préstamo'),
                    ('auto_config', 'Automática - Configuración'),
                    ('manual', 'Manual'),
                    ('adjustment', 'Ajuste correctivo'),
                ],
                default='manual',
                max_length=20,
            ),
        ),
    ]
