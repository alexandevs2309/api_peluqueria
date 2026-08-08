from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TutorialViewSet, AdminTutorialViewSet

router = DefaultRouter()
router.register(r'tutorials', TutorialViewSet, basename='tutorial')

admin_router = DefaultRouter()
admin_router.register(r'tutorials', AdminTutorialViewSet, basename='admin-tutorial')

urlpatterns = [
    path('', include(router.urls)),
    path('admin/', include(admin_router.urls)),
]
