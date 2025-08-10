from rest_framework.routers import DefaultRouter
from django.urls import path, include
from apps.users_api.views import UserViewSet

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
]
