# Generated manually for payment system optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0008_add_legal_deductions_config'),
        ('pos_api', '0009_merge_0002_add_sale_status_0008_alter_sale_user'),
    ]

    operations = [
        # Índices para optimizar consultas de pagos (SQLite compatible)
        migrations.RunSQL(
            "CREATE INDEX pos_sale_period_null_idx ON pos_api_sale (employee_id, status) WHERE period_id IS NULL;",
            reverse_sql="DROP INDEX pos_sale_period_null_idx;"
        ),
        migrations.RunSQL(
            "CREATE INDEX pos_sale_employee_status_idx ON pos_api_sale (employee_id, status);",
            reverse_sql="DROP INDEX pos_sale_employee_status_idx;"
        ),
        migrations.RunSQL(
            "CREATE INDEX fortnight_summary_employee_period_idx ON employees_api_fortnightsummary (employee_id, fortnight_year, fortnight_number);",
            reverse_sql="DROP INDEX fortnight_summary_employee_period_idx;"
        ),
        migrations.RunSQL(
            "CREATE INDEX fortnight_summary_paid_idx ON employees_api_fortnightsummary (is_paid, paid_at);",
            reverse_sql="DROP INDEX fortnight_summary_paid_idx;"
        ),
    ]