from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet, PaymentAttemptViewSet, BillingStatsView
from .webhooks import stripe_webhook

router = DefaultRouter()
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'payment-attempts', PaymentAttemptViewSet, basename='payment-attempt')

urlpatterns = [
    path('', include(router.urls)),
    path('webhooks/stripe/', stripe_webhook, name='stripe_webhook'),
    
    # SuperAdmin billing stats
    path('admin/stats/', BillingStatsView.as_view(), name='billing-admin-stats'),
]