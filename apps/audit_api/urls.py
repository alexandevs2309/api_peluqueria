from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuditLogViewSet, AuditLogCreateView

router = DefaultRouter()
router.register(r'logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('', include(router.urls)),
    path('create/', AuditLogCreateView.as_view({'post': 'create'}), name='audit-log-create'),
]
