from django.db import migrations


def verify_employee_users(apps, schema_editor):
    Employee = apps.get_model('employees_api', 'Employee')
    User = apps.get_model('auth_api', 'User')

    employee_user_ids = Employee.objects.values_list('user_id', flat=True)
    User.objects.filter(
        id__in=employee_user_ids,
        is_email_verified=False,
    ).update(is_email_verified=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('auth_api', '0008_user_stripe_customer_id'),
        ('employees_api', '0018_rename_employees_a_employe_e9f98d_idx_employees_a_employe_227330_idx_and_more'),
    ]

    operations = [
        migrations.RunPython(verify_employee_users, noop_reverse),
    ]
