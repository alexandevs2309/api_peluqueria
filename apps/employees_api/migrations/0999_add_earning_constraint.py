# Generated migration for earning constraint

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0005_payrollbatch_payrollbatchitem_earning_external_id_and_more'),
    ]

    operations = [
        # Asegurar que external_id sea único a nivel de base de datos
        migrations.RunSQL(
            "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS earning_external_id_unique ON employees_api_earning (external_id) WHERE external_id IS NOT NULL;",
            reverse_sql="DROP INDEX IF EXISTS earning_external_id_unique;"
        ),
    ]