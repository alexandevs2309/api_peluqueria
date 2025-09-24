from django.urls import path
from .webhooks import stripe_webhook

urlpatterns = [
    path('webhooks/stripe/', stripe_webhook, name='stripe_webhook'),
]