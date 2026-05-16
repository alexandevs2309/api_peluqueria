import django, os; os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
django.setup()
from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.get(email='andresdelacrus058@gmail.com')

client = Client()
client.force_login(user)
response = client.get('/api/tenants/subscription-status/')
print('Status:', response.status_code)
print('Content:', response.content)
