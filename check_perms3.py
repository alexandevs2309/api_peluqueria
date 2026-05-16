import django; django.setup()
from apps.auth_api.models import User
from apps.tenants_api.models import Tenant
from apps.roles_api.models import UserRole, Role

user = User.objects.filter(email='andresdelacrus058@gmail.com').first()
tenant = Tenant.objects.filter(id=1).first()

if user:
    print(f'User ID: {user.id}, tenant_id: {user.tenant_id}')
    
    # Check UserRole records
    user_roles = UserRole.objects.filter(user=user)
    print(f'UserRole count: {user_roles.count()}')
    for ur in user_roles:
        print(f'  UserRole: id={ur.id}, role={ur.role.name if ur.role else "None"}, tenant={ur.tenant_id}')
        if ur.role:
            perms = ur.role.permissions.all()
            print(f'  Permissions ({perms.count()}):')
            for p in perms:
                print(f'    {p.content_type.app_label}.{p.codename}')
    
    # Check all roles in tenant
    tenant_roles = Role.objects.filter(tenant=tenant)
    print(f'Roles in tenant {tenant.id}: {tenant_roles.count()}')
    for r in tenant_roles:
        print(f'  Role: id={r.id}, name={r.name}, scope={r.scope}')
    
    # Check if user has any permission directly
    perms = user.user_permissions.all()
    print(f'User direct permissions: {perms.count()}')
    for p in perms:
        print(f'  {p.content_type.app_label}.{p.codename}')
