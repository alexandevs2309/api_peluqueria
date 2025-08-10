from rest_framework.routers import DefaultRouter
from django.urls import path, include
from apps.users_api.views import UserViewSet

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')  # SIN 'users'

urlpatterns = [
    path('', include(router.urls)),
]
