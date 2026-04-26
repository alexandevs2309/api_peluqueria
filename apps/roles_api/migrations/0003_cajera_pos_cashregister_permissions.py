from django.db import migrations


def add_cajera_cashregister_permissions(apps, schema_editor):
    Role = apps.get_model('roles_api', 'Role')
    Permission = apps.get_model('auth', 'Permission')

    try:
        cajera = Role.objects.get(name='Cajera')
    except Role.DoesNotExist:
        return

    permissions = Permission.objects.filter(
        content_type__app_label='pos_api',
        codename__in=[
            'view_sale',
            'add_sale',
            'view_cashregister',
            'add_cashregister',
            'change_cashregister',
        ],
    )
    cajera.permissions.add(*permissions)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('roles_api', '0002_initial'),
        ('pos_api', '0018_add_rnc_field_with_nullable'),
    ]

    operations = [
        migrations.RunPython(add_cajera_cashregister_permissions, noop_reverse),
    ]
