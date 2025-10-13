from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TenantViewSet
from .admin_views import AdminUserManagementViewSet

router = DefaultRouter()
router.register(r"", TenantViewSet, basename="tenant")
router.register(r"admin/users", AdminUserManagementViewSet, basename="admin-users")

urlpatterns = [
    path('', include(router.urls)),
]
