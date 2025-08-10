from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, SupplierViewSet, StockMovementViewSet, low_stock_alerts
from django.urls import path


router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'stock-movements', StockMovementViewSet)

urlpatterns = router.urls

urlpatterns = [
    path('alerts/low-stock/', low_stock_alerts, name='low-stock-alerts'),

]