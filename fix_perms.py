import django; django.setup()
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.roles_api.models import Role

role = Role.objects.filter(name='Client-Admin').first()
if not role:
    print('Role Client-Admin not found')
    exit()

# Get all content types for employees_api and notifications_api
content_types = ContentType.objects.filter(app_label__in=['employees_api', 'notifications_api'])
print(f'Content types found: {content_types.count()}')

# Get all permissions for these apps
perms = Permission.objects.filter(content_type__in=content_types)
print(f'Permissions found: {perms.count()}')
for p in perms:
    print(f'  {p.content_type.app_label}.{p.codename}')

# Assign all to the role
role.permissions.add(*perms)
role.save()

# Verify
role.refresh_from_db()
print(f'\nRole {role.name} now has {role.permissions.count()} permissions')
