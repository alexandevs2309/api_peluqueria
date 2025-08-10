from rest_framework.routers import DefaultRouter
from django.urls import path, include
from apps.users_api.views import UserViewSet

router = DefaultRouter()
<<<<<<< HEAD
router.register(r'', UserViewSet, basename='user')  # SIN 'users'
=======
router.register(r'users', UserViewSet, basename='user')
>>>>>>> origin/master

urlpatterns = [
    path('', include(router.urls)),
]
