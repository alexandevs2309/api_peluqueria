from django.db import migrations


def add_payroll_config_permission(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')

    ct, _ = ContentType.objects.get_or_create(
        app_label='employees_api',
        model='employee',
    )

    Permission.objects.get_or_create(
        codename='manage_payroll_config',
        content_type=ct,
        defaults={'name': 'Can manage payroll configuration'},
    )


def remove_payroll_config_permission(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    Permission.objects.filter(
        codename='manage_payroll_config',
        content_type__app_label='employees_api',
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0032_rename_employees_a_sale_detai_6f0b2a_idx_employees_a_sale_de_554069_idx'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(
            add_payroll_config_permission,
            reverse_code=remove_payroll_config_permission,
        ),
    ]
