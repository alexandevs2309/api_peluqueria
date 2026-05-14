from django.contrib.auth.models import Permission

from apps.roles_api.models import Role


ROLE_PERMISSIONS = {
    'Client-Admin': '__all__',
    'Manager': [
        ('appointments_api', 'view_appointment'),
        ('appointments_api', 'add_appointment'),
        ('appointments_api', 'change_appointment'),
        ('appointments_api', 'cancel_appointment'),
        ('appointments_api', 'complete_appointment'),
        ('clients_api', 'view_client'),
        ('clients_api', 'add_client'),
        ('clients_api', 'change_client'),
        ('employees_api', 'view_employee'),
        ('services_api', 'view_service'),
        ('reports_api', 'view_employee_reports'),
        ('reports_api', 'view_sales_reports'),
        ('reports_api', 'view_kpi_dashboard'),
    ],
    'Client-Staff': [
        ('employees_api', 'view_employee'),
        ('appointments_api', 'view_appointment'),
        ('clients_api', 'view_client'),
        ('services_api', 'view_service'),
        ('pos_api', 'view_sale'),
        ('employees_api', 'view_attendancerecord'),
        ('employees_api', 'add_attendancerecord'),
        ('employees_api', 'change_attendancerecord'),
    ],
    'Cajera': [
        ('employees_api', 'view_employee'),
        ('appointments_api', 'view_appointment'),
        ('appointments_api', 'add_appointment'),
        ('appointments_api', 'change_appointment'),
        ('clients_api', 'view_client'),
        ('clients_api', 'add_client'),
        ('clients_api', 'change_client'),
        ('services_api', 'view_service'),
        ('pos_api', 'view_sale'),
        ('pos_api', 'add_sale'),
        ('pos_api', 'view_cashregister'),
        ('pos_api', 'add_cashregister'),
        ('pos_api', 'change_cashregister'),
        ('inventory_api', 'view_product'),
    ],
    'Estilista': [
        ('employees_api', 'view_employee'),
        ('appointments_api', 'view_appointment'),
        ('clients_api', 'view_client'),
        ('services_api', 'view_service'),
        ('pos_api', 'view_sale'),
        ('employees_api', 'view_attendancerecord'),
        ('employees_api', 'add_attendancerecord'),
        ('employees_api', 'change_attendancerecord'),
    ],
    'Utility': [
        ('employees_api', 'view_employee'),
        ('appointments_api', 'view_appointment'),
        ('services_api', 'view_service'),
    ],
}


assigned_total = 0
skipped = []

for role_name, perms in ROLE_PERMISSIONS.items():
    roles = Role.objects.filter(name=role_name)
    if not roles.exists():
        print(f"Role '{role_name}' not found, skipping")
        continue

    for role in roles:
        if perms == '__all__':
            target_apps = [
                'auth_api',
                'appointments_api',
                'clients_api',
                'employees_api',
                'services_api',
                'inventory_api',
                'pos_api',
                'billing_api',
                'reports_api',
                'settings_api',
                'notifications_api',
                'audit_api',
            ]
            all_perms = Permission.objects.filter(
                content_type__app_label__in=target_apps
            )
            role.permissions.set(all_perms)
            print(f"{role_name} (id={role.id}): {all_perms.count()} permissions assigned")
            assigned_total += all_perms.count()
        else:
            for app_label, codename in perms:
                perm = Permission.objects.filter(
                    content_type__app_label=app_label,
                    codename=codename,
                ).first()
                if perm:
                    role.permissions.add(perm)
                    assigned_total += 1
                else:
                    skipped.append(f"{app_label}.{codename}")

            print(
                f"{role_name} (id={role.id}, tenant={getattr(role, 'tenant_id', 'global')}): "
                "permissions assigned"
            )

print(f"\nTotal assigned: {assigned_total}")
if skipped:
    print(f"Permissions not found (create with migration): {set(skipped)}")
