import django.db.models.deletion
from django.db import migrations, models


def backfill_tenant(apps, schema_editor):
    CashRegister = apps.get_model('pos_api', 'CashRegister')
    for cr in CashRegister.objects.select_related('user__tenant').filter(tenant__isnull=True):
        tenant = cr.user.tenant if hasattr(cr.user, 'tenant') else None
        if tenant:
            cr.tenant = tenant
            cr.save(update_fields=['tenant'])


class Migration(migrations.Migration):

    dependencies = [
        ('pos_api', '0019_promotion_tenant'),
        ('tenants_api', '0009_plan_public_names'),
    ]

    operations = [
        migrations.AddField(
            model_name='cashregister',
            name='tenant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='cash_registers',
                to='tenants_api.tenant',
            ),
        ),
        migrations.RunPython(backfill_tenant, reverse_code=migrations.RunPython.noop),
        migrations.AddIndex(
            model_name='cashregister',
            index=models.Index(
                fields=['tenant', 'is_open'],
                name='pos_api_cash_tenant_i_abc123',
            ),
        ),
    ]
