import django, os; os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'; django.setup()
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from apps.tenants_api.views import TenantViewSet

User = get_user_model()
user = User.objects.get(email='andresdelacrus058@gmail.com')
print('User:', user.email, 'tenant:', user.tenant_id)

factory = APIRequestFactory()
request = factory.get('/api/tenants/subscription-status/')
force_authenticate(request, user=user)

# Manually check permissions like DRF does
from rest_framework.permissions import IsAuthenticated
from apps.core.permissions import IsSuperAdmin

view = TenantViewSet.as_view({'get': 'subscription_status'})
response = view(request)
print('Status:', response.status_code)
print('Content:', response.content)
