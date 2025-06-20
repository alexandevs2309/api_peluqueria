# apps/pos_api/urls.py

from rest_framework.routers import DefaultRouter
from .views import SaleViewSet, CashRegisterViewSet, daily_summary
from django.urls import path


router = DefaultRouter()
router.register(r'sales', SaleViewSet, basename='sale')
router.register(r'cash-registers', CashRegisterViewSet, basename='cash-register')

urlpatterns = router.urls

urlpatterns += [
    path('summary/daily/', daily_summary, name='daily-summary')

]