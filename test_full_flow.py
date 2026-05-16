import django, os; os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
import json
django.setup()
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.tenants_api.middleware import TenantMiddleware
from apps.tenants_api.views import TenantViewSet
from rest_framework.test import APIRequestFactory, force_authenticate

User = get_user_model()
user = User.objects.get(email='andresdelacrus058@gmail.com')

factory = APIRequestFactory()
request = factory.get('/api/tenants/subscription-status/')
force_authenticate(request, user=user)

# Run middleware
mw = TenantMiddleware(lambda r: None)
result = mw.process_request(request)
print('Middleware result:', result)
if result:
    print('Middleware blocked:', result.status_code, result.content)
else:
    print('Middleware passed, request.tenant:', getattr(request, 'tenant', None))
    print('request.user.tenant:', request.user.tenant)
