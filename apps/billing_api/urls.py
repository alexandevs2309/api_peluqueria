from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet, PaymentAttemptViewSet, BillingStatsView
# ❌ DEPRECADO: webhooks.py sin idempotencia
# from .webhooks import stripe_webhook
from .webhooks_idempotent import stripe_webhook  # ✅ Versión con idempotencia
from .paypal_webhook import paypal_webhook  # ✅ PayPal webhook handler

router = DefaultRouter()
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'payment-attempts', PaymentAttemptViewSet, basename='payment-attempt')

urlpatterns = [
    path('', include(router.urls)),
    # ✅ Solo webhooks idempotentes
    path('webhooks/stripe/', stripe_webhook, name='stripe_webhook'),
    path('webhooks/paypal/', paypal_webhook, name='paypal_webhook'),

    # SuperAdmin billing stats
    path('admin/stats/', BillingStatsView.as_view(), name='billing-admin-stats'),
]