from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MyEntitlementsView,
    MyActiveSubscriptionView,
    SubscriptionPlanViewSet,
    UserSubscriptionViewSet,
    SubscriptionAuditLogViewSet,
    OnboardingView,
)
from .registration_views import register_with_plan

router = DefaultRouter()
router.register(r'plans', SubscriptionPlanViewSet, basename='subscription-plan')
router.register(r'user-subscriptions', UserSubscriptionViewSet, basename='user-subscription')
router.register(r'audit-logs', SubscriptionAuditLogViewSet, basename='subscription-audit-log')

urlpatterns = [
    path("", include(router.urls)),
    path("me/active/", MyActiveSubscriptionView.as_view(), name="my-active-subscription"),
    path("me/entitlements/", MyEntitlementsView.as_view(), name="my-entitlements"),
    path("register/", register_with_plan, name="register-with-plan"),
    path("onboard/", OnboardingView.as_view(), name="onboarding"),
]
