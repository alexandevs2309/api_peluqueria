from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, StripeWebhookView

router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),
    # Stripe webhook endpoint (public, signature-verified in view)
    path('stripe/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
]
