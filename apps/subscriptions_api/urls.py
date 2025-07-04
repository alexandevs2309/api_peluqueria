from rest_framework.routers import DefaultRouter
from .views import SubscriptionPlanViewSet, UserSubscriptionViewSet

router = DefaultRouter()
router.register(r'plans', SubscriptionPlanViewSet, basename='subscription-plan')
router.register(r'user-subscriptions', UserSubscriptionViewSet, basename='user-subscription')

urlpatterns = router.urls