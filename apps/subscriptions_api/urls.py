from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MyEntitlementsView,
    MyActiveSubscriptionView,
    SubscriptionPlanViewSet, 
    UserSubscriptionViewSet,
    SubscriptionAuditLogViewSet,
)

router = DefaultRouter()
router.register(r'plans', SubscriptionPlanViewSet, basename='subscription-plan')
router.register(r'user-subscriptions', UserSubscriptionViewSet, basename='user-subscription')
router.register(r'audit-logs', SubscriptionAuditLogViewSet, basename='subscription-audit-log')

urlpatterns = [
    path("", include(router.urls)),
    path("me/active/", MyActiveSubscriptionView.as_view(), name="my-active-subscription"),
    path("me/entitlements/", MyEntitlementsView.as_view(), name="my-entitlements"),
]
