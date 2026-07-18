from django.db import migrations


def remove_soporte_role(apps, schema_editor):
    Role = apps.get_model("roles_api", "Role")
    UserRole = apps.get_model("roles_api", "UserRole")

    try:
        role = Role.objects.get(name="Soporte")
        UserRole.objects.filter(role=role).delete()
        role.delete()
    except Role.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ("roles_api", "0004_remove_userrole_roles_api_u_user_id_31ebd3_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(remove_soporte_role, migrations.RunPython.noop),
    ]
