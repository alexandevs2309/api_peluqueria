from django.db import migrations


def add_manager_service_crud(apps, schema_editor):
    Role = apps.get_model('roles_api', 'Role')
    Permission = apps.get_model('auth', 'Permission')

    try:
        manager = Role.objects.get(name='Manager')
    except Role.DoesNotExist:
        return

    permissions = Permission.objects.filter(
        content_type__app_label='services_api',
        codename__in=[
            'add_service',
            'change_service',
            'delete_service',
        ],
    )
    if permissions:
        manager.permissions.add(*permissions)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('roles_api', '0005_remove_soporte_role'),
        ('services_api', '0002_remove_service_category_servicecategory_and_more'),
    ]

    operations = [
        migrations.RunPython(add_manager_service_crud, noop_reverse),
    ]