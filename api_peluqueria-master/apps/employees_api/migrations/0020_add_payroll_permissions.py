from django.db import migrations


def add_payroll_permissions(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')

    ct, _ = ContentType.objects.get_or_create(
        app_label='employees_api',
        model='employee',
    )

    perms_to_create = [
        ('approve_payroll', 'Can approve payroll periods'),
        ('change_employee_payroll', 'Can recalculate and submit payroll periods'),
        ('view_employee_payroll', 'Can view payroll periods and receipts'),
    ]

    for codename, name in perms_to_create:
        Permission.objects.get_or_create(
            codename=codename,
            content_type=ct,
            defaults={'name': name},
        )


def remove_payroll_permissions(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    Permission.objects.filter(
        codename__in=[
            'approve_payroll',
            'change_employee_payroll',
            'view_employee_payroll',
        ],
        content_type__app_label='employees_api',
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0019_verify_existing_employee_users'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(
            add_payroll_permissions,
            reverse_code=remove_payroll_permissions,
        ),
    ]
