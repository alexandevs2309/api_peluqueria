from apps.auth_api.models import User
from apps.tenants_api.models import Tenant
from apps.core.models import UserRole, Role, Permission

user = User.objects.filter(email='andresdelacrus058@gmail.com').first()
tenant = Tenant.objects.filter(id=1).first()

if user:
    print(f'User tenant field: {user.tenant_id}')
    print(f'Tenant exists: {tenant is not None}')
    
    # Check UserRole
    try:
        ur = UserRole.objects.filter(user=user, tenant=tenant).select_related('role')
        for r in ur:
            print(f'UserRole: role={r.role.name if r.role else "None"}, tenant={r.tenant_id}')
            perms = r.role.permissions.all() if r.role else []
            for p in perms:
                print(f'  Permission: {p.content_type.app_label}.{p.codename}')
    except Exception as e:
        print(f'Error checking UserRole: {e}')
    
    # Check all roles
    try:
        all_roles = Role.objects.filter(tenant=tenant)
        for r in all_roles:
            print(f'Role: {r.name} (id={r.id})')
    except Exception as e:
        print(f'Error listing roles: {e}')
