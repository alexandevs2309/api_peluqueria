# Generated migration for adding tenant field to Sale model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants_api', '0001_initial'),
        ('pos_api', '0011_sale_pos_api_sal_date_ti_a16fd8_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='tenant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='sales',
                to='tenants_api.tenant'
            ),
        ),
        # Poblar tenant desde user.tenant para registros existentes
        migrations.RunSQL(
            sql="""
                UPDATE pos_api_sale 
                SET tenant_id = (
                    SELECT tenant_id 
                    FROM auth_api_user 
                    WHERE auth_api_user.id = pos_api_sale.user_id
                )
                WHERE tenant_id IS NULL AND user_id IS NOT NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Poblar tenant desde employee.tenant para registros sin user
        migrations.RunSQL(
            sql="""
                UPDATE pos_api_sale 
                SET tenant_id = (
                    SELECT tenant_id 
                    FROM employees_api_employee 
                    WHERE employees_api_employee.id = pos_api_sale.employee_id
                )
                WHERE tenant_id IS NULL AND employee_id IS NOT NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AddIndex(
            model_name='sale',
            index=models.Index(fields=['tenant', 'date_time'], name='pos_api_sal_tenant_date_idx'),
        ),
    ]
