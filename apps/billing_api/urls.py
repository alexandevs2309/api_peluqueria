from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet, PaymentAttemptViewSet

router = DefaultRouter()
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'payment-attempts', PaymentAttemptViewSet, basename='payment-attempt')

urlpatterns = [
    path("", include(router.urls)),
]
