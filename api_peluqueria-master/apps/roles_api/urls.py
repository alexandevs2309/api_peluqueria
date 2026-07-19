from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoleViewSet
from .viewsets.user_role_viewset import UserRoleViewSet

router = DefaultRouter()
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'user-roles', UserRoleViewSet, basename='userrole')

urlpatterns = [
    path('', include(router.urls)),
    path('roles/permissions/', RoleViewSet.as_view({'get': 'list_permissions'}), name='list_permissions')
]
