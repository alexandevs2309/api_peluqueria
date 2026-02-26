from apps.auth_api.serializers import LoginSerializer
from django.test import RequestFactory

factory = RequestFactory()
request = factory.post('/api/auth/cookie-login/')

print('TEST 1: Super-admin')
data1 = {'email': 'admin@admin.com', 'password': 'baspeka1394'}
s1 = LoginSerializer(data=data1, context={'request': request})
print(f'Valid: {s1.is_valid()}')
if s1.is_valid():
    print(f'User: {s1.validated_data["user"].email}, Tenant: {s1.validated_data["tenant"]}')
else:
    print(f'Errors: {s1.errors}')

print('\nTEST 2: Usuario normal')
data2 = {'email': 'alejav.zuniga@gmail.com', 'password': 'test123'}
s2 = LoginSerializer(data=data2, context={'request': request})
print(f'Valid: {s2.is_valid()}')
if s2.is_valid():
    print(f'User: {s2.validated_data["user"].email}, Tenant: {s2.validated_data["tenant"].subdomain}')
else:
    print(f'Errors: {s2.errors}')
