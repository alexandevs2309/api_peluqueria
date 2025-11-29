from rest_framework.routers import DefaultRouter
from .views import SaleViewSet, CashRegisterViewSet, PromotionViewSet, PosConfigurationViewSet, daily_summary, dashboard_stats, active_promotions, pos_categories, pos_config, debug_sale_data
from django.urls import path, include

router = DefaultRouter()
router.register(r'sales', SaleViewSet, basename='sale')
router.register(r'cashregisters', CashRegisterViewSet, basename='cash-register')
router.register(r'promotions', PromotionViewSet, basename='promotion')
router.register(r'configuration', PosConfigurationViewSet, basename='pos-configuration')

urlpatterns = [
    path('', include(router.urls)),
    path('summary/daily/', daily_summary, name='daily-summary'),
    path('dashboard/stats/', dashboard_stats, name='dashboard-stats'),
    path('promotions/active/', active_promotions, name='active-promotions'),
    path('categories/', pos_categories, name='pos-categories'),
    path('config/', pos_config, name='pos-config'),

    path('debug-sale/', debug_sale_data, name='debug-sale-data'),
]