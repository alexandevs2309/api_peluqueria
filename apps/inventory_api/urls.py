from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, SupplierViewSet, StockMovementViewSet, low_stock_alerts
from .category_views import categories_list, low_stock_products
from django.urls import path, include

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'stock-movements', StockMovementViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('alerts/low-stock/', low_stock_alerts, name='low-stock-alerts'),
    path('categories/', categories_list, name='categories'),
    path('products/low-stock/', low_stock_products, name='low-stock'),
]