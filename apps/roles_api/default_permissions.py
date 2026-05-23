from django.contrib.auth.models import Permission


TENANT_ADMIN_APPS = [
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
    'subscriptions_api',
]


ROLE_PERMISSIONS = {
    'Super-Admin': '__all__',
    'SuperAdmin': '__all__',
    'Client-Admin': '__tenant_admin__',
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
        ('employees_api', 'view_employee_payroll'),
        ('services_api', 'view_service'),
        ('inventory_api', 'view_product'),
        ('inventory_api', 'adjust_stock'),
        ('pos_api', 'view_sale'),
        ('pos_api', 'refund_sale'),
        ('pos_api', 'add_cashregister'),
        ('pos_api', 'change_cashregister'),
        ('pos_api', 'add_promotion'),
        ('pos_api', 'change_promotion'),
        ('pos_api', 'view_promotion'),
        ('pos_api', 'view_posconfiguration'),
        ('reports_api', 'view_employee_reports'),
        ('reports_api', 'view_sales_reports'),
        ('reports_api', 'view_kpi_dashboard'),
        ('settings_api', 'view_barbershopsettings'),
        ('notifications_api', 'view_inappnotification'),
    ],
    'Client-Staff': [
        ('employees_api', 'view_employee'),
        ('appointments_api', 'view_appointment'),
        ('appointments_api', 'add_appointment'),
        ('clients_api', 'view_client'),
        ('clients_api', 'add_client'),
        ('services_api', 'view_service'),
        ('pos_api', 'view_sale'),
        ('pos_api', 'view_promotion'),
        ('pos_api', 'view_posconfiguration'),
        ('employees_api', 'view_attendancerecord'),
        ('employees_api', 'add_attendancerecord'),
        ('employees_api', 'change_attendancerecord'),
        ('settings_api', 'view_barbershopsettings'),
        ('notifications_api', 'view_inappnotification'),
    ],
    'Cajera': [
        ('employees_api', 'view_employee'),
        ('appointments_api', 'view_appointment'),
        ('appointments_api', 'add_appointment'),
        ('appointments_api', 'change_appointment'),
        ('appointments_api', 'cancel_appointment'),
        ('appointments_api', 'complete_appointment'),
        ('clients_api', 'view_client'),
        ('clients_api', 'add_client'),
        ('clients_api', 'change_client'),
        ('services_api', 'view_service'),
        ('pos_api', 'view_sale'),
        ('pos_api', 'add_sale'),
        ('pos_api', 'view_cashregister'),
        ('pos_api', 'add_cashregister'),
        ('pos_api', 'change_cashregister'),
        ('pos_api', 'view_promotion'),
        ('pos_api', 'view_posconfiguration'),
        ('inventory_api', 'view_product'),
        ('settings_api', 'view_barbershopsettings'),
        ('notifications_api', 'view_inappnotification'),
    ],
    'Estilista': [
        ('employees_api', 'view_employee'),
        ('appointments_api', 'view_appointment'),
        ('appointments_api', 'change_appointment'),
        ('appointments_api', 'complete_appointment'),
        ('clients_api', 'view_client'),
        ('clients_api', 'add_client'),
        ('clients_api', 'change_client'),
        ('services_api', 'view_service'),
        ('pos_api', 'view_sale'),
        ('pos_api', 'view_promotion'),
        ('pos_api', 'view_posconfiguration'),
        ('employees_api', 'view_attendancerecord'),
        ('employees_api', 'add_attendancerecord'),
        ('employees_api', 'change_attendancerecord'),
        ('employees_api', 'view_employee_payroll'),
        ('settings_api', 'view_barbershopsettings'),
        ('notifications_api', 'view_inappnotification'),
    ],
    'Utility': [
        ('employees_api', 'view_employee'),
        ('appointments_api', 'view_appointment'),
        ('services_api', 'view_service'),
        ('pos_api', 'view_promotion'),
        ('pos_api', 'view_posconfiguration'),
        ('settings_api', 'view_barbershopsettings'),
        ('notifications_api', 'view_inappnotification'),
    ],
    # Business roles (nuevo sistema RBAC)
    'owner': '__tenant_admin__',
    'frontdesk_cashier': [
        ('employees_api', 'view_employee'),
        ('appointments_api', 'view_appointment'),
        ('appointments_api', 'add_appointment'),
        ('appointments_api', 'change_appointment'),
        ('appointments_api', 'cancel_appointment'),
        ('appointments_api', 'complete_appointment'),
        ('clients_api', 'view_client'),
        ('clients_api', 'add_client'),
        ('clients_api', 'change_client'),
        ('services_api', 'view_service'),
        ('pos_api', 'view_sale'),
        ('pos_api', 'add_sale'),
        ('pos_api', 'view_cashregister'),
        ('pos_api', 'add_cashregister'),
        ('pos_api', 'change_cashregister'),
        ('pos_api', 'view_promotion'),
        ('pos_api', 'view_posconfiguration'),
        ('inventory_api', 'view_product'),
        ('settings_api', 'view_barbershopsettings'),
        ('notifications_api', 'view_inappnotification'),
    ],
    'professional': [
        ('employees_api', 'view_employee'),
        ('appointments_api', 'view_appointment'),
        ('appointments_api', 'change_appointment'),
        ('appointments_api', 'complete_appointment'),
        ('clients_api', 'view_client'),
        ('clients_api', 'add_client'),
        ('clients_api', 'change_client'),
        ('services_api', 'view_service'),
        ('pos_api', 'view_sale'),
        ('pos_api', 'view_promotion'),
        ('pos_api', 'view_posconfiguration'),
        ('employees_api', 'view_attendancerecord'),
        ('employees_api', 'add_attendancerecord'),
        ('employees_api', 'change_attendancerecord'),
        ('employees_api', 'view_employee_payroll'),
        ('settings_api', 'view_barbershopsettings'),
        ('notifications_api', 'view_inappnotification'),
    ],
    'internal_support': [
        ('employees_api', 'view_employee'),
        ('appointments_api', 'view_appointment'),
        ('services_api', 'view_service'),
        ('pos_api', 'view_promotion'),
        ('pos_api', 'view_posconfiguration'),
        ('settings_api', 'view_barbershopsettings'),
        ('notifications_api', 'view_inappnotification'),
    ],
}


def get_default_permissions_for_role(role_name):
    config = ROLE_PERMISSIONS.get(role_name)

    if config == '__all__':
        return Permission.objects.all()

    if config == '__tenant_admin__':
        return Permission.objects.filter(content_type__app_label__in=TENANT_ADMIN_APPS)

    if not config:
        return Permission.objects.none()

    filters = Permission.objects.none()
    for app_label, codename in config:
        filters |= Permission.objects.filter(
            content_type__app_label=app_label,
            codename=codename,
        )
    return filters.distinct()


def sync_default_role_permissions(role):
    permissions = get_default_permissions_for_role(role.name)
    role.permissions.set(permissions)
    return permissions.count()


def ensure_role_default_permissions(role):
    permissions = get_default_permissions_for_role(role.name)
    if permissions.exists():
        role.permissions.add(*permissions)
    return role.permissions.count()


def sync_all_default_role_permissions():
    from apps.roles_api.models import Role

    synced = {}
    for role in Role.objects.filter(name__in=ROLE_PERMISSIONS.keys()):
        synced[role.name] = sync_default_role_permissions(role)
    return synced
