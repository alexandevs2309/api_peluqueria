from django.db import migrations, models


def backfill_business_roles(apps, schema_editor):
    User = apps.get_model('auth_api', 'User')

    role_map = {
        'SuperAdmin': 'internal_support',
        'Client-Admin': 'owner',
        'Manager': 'manager',
        'Cajera': 'frontdesk_cashier',
        'Estilista': 'professional',
        'Client-Staff': 'professional',
        'Utility': 'professional',
        'Soporte': 'internal_support',
    }

    for user in User.objects.all().iterator():
        business_role = 'internal_support' if user.is_superuser else role_map.get((user.role or '').strip())
        if business_role and user.business_role != business_role:
            User.objects.filter(pk=user.pk).update(business_role=business_role)


class Migration(migrations.Migration):

    dependencies = [
        ('auth_api', '0008_user_stripe_customer_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='business_role',
            field=models.CharField(
                blank=True,
                choices=[
                    ('owner', 'Propietario'),
                    ('manager', 'Gerente'),
                    ('frontdesk_cashier', 'Recepcion / Caja'),
                    ('professional', 'Profesional'),
                    ('internal_support', 'Soporte interno'),
                    ('marketing', 'Marketing'),
                    ('accounting', 'Contabilidad'),
                ],
                db_index=True,
                max_length=32,
                null=True,
            ),
        ),
        migrations.RunPython(backfill_business_roles, migrations.RunPython.noop),
    ]
