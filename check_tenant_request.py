import django; django.setup()
from apps.auth_api.models import User
from apps.tenants_api.models import Tenant

user = User.objects.filter(email='andresdelacrus058@gmail.com').first()
print(f'User ID: {user.id}')
print(f'User.tenant_id field: {user.tenant_id}')
print(f'User.tenant (related object): {user.tenant}')
if user.tenant:
    print(f'  name: {user.tenant.name}')
    print(f'  is_active: {user.tenant.is_active}')
    print(f'  deleted_at: {user.tenant.deleted_at}')
