from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoleViewSet

router = DefaultRouter()
router.register(r'roles', RoleViewSet ,basename='role')

urlpatterns = [
    path('', include(router.urls)),
    path('roles/permissions/', RoleViewSet.as_view({'get': 'list_permissions'}), name='list_permissions')
]
