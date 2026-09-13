from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PaymentViewSet,
    StripeWebhookView,
    azul_checkout,
    azul_verify,
    azul_webhook,
    manual_upload,
    manual_proof_download,
)

router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),
    # Stripe webhook endpoint (public, signature-verified in view)
    path('stripe/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    # Azul — payment processor primario para RD
    path('azul/checkout/', azul_checkout, name='azul-checkout'),
    path('azul/verify/', azul_verify, name='azul-verify'),
    path('azul/webhook/', azul_webhook, name='azul-webhook'),
    # Pagos manuales
    path('manual/', manual_upload, name='manual-upload'),
    path('manual/proof/<uuid:proof_id>/', manual_proof_download, name='manual-proof-download'),
]
