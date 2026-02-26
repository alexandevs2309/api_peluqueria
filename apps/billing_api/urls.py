from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet, PaymentAttemptViewSet, BillingStatsView
# ❌ DEPRECADO: webhooks.py sin idempotencia
# from .webhooks import stripe_webhook
from .webhooks_idempotent import stripe_webhook  # ✅ Versión con idempotencia

router = DefaultRouter()
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'payment-attempts', PaymentAttemptViewSet, basename='payment-attempt')

urlpatterns = [
    path('', include(router.urls)),
    # ✅ SOLO webhook idempotente activo
    path('webhooks/stripe/', stripe_webhook, name='stripe_webhook'),
    
    # SuperAdmin billing stats
    path('admin/stats/', BillingStatsView.as_view(), name='billing-admin-stats'),
]