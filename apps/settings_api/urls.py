from django.urls import path
from .integration_views import IntegrationStatusView, IntegrationTestView
from .admin_views import SaasMetricsView, SystemMonitorView, test_integration_service

urlpatterns = [
    path('integrations/status/', IntegrationStatusView.as_view(), name='integration-status'),
    path('integrations/test/', IntegrationTestView.as_view(), name='integration-test'),
    
    # SuperAdmin endpoints
    path('admin/metrics/', SaasMetricsView.as_view(), name='admin-saas-metrics'),
    path('admin/system-monitor/', SystemMonitorView.as_view(), name='admin-system-monitor'),
    path('admin/test-service/', test_integration_service, name='admin-test-service'),
]
