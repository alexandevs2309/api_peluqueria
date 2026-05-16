from apps.auth_api.models import User
user = User.objects.filter(email='andresdelacrus058@gmail.com').first()
if user:
    print(f'Email: {user.email}')
    print(f'is_superuser: {user.is_superuser}')
    print(f'is_staff: {user.is_staff}')
    print(f'role: {user.role}')
    print(f'business_role: {user.business_role}')
    print(f'is_active: {user.is_active}')
    print(f'Groups: {[g.name for g in user.groups.all()]}')
else:
    print('Usuario no encontrado')
