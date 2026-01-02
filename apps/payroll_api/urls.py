from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PayrollSettlementViewSet, PayrollPaymentViewSet
from .client_views import ClientPayrollViewSet

router = DefaultRouter()
router.register(r'settlements', PayrollSettlementViewSet, basename='settlement')
router.register(r'payments', PayrollPaymentViewSet, basename='payment')

# Rutas simplificadas para /client
client_router = DefaultRouter()
client_router.register(r'payroll', ClientPayrollViewSet, basename='client-payroll')

urlpatterns = [
    path('', include(router.urls)),
    path('client/', include(client_router.urls)),
]