from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .integration_views import IntegrationStatusView, IntegrationTestView
from .admin_views import SaasMetricsView, SystemMonitorView, test_integration_service
from .contact_views import demo_request, newsletter_signup
from .barbershop_views import BarbershopSettingsViewSet

router = DefaultRouter()
router.register(r'barbershop', BarbershopSettingsViewSet, basename='barbershop-settings')

urlpatterns = [
    path('', include(router.urls)),
    path('integrations/status/', IntegrationStatusView.as_view(), name='integration-status'),
    path('integrations/test/', IntegrationTestView.as_view(), name='integration-test'),
    
    # SuperAdmin endpoints
    path('admin/metrics/', SaasMetricsView.as_view(), name='admin-saas-metrics'),
    path('admin/system-monitor/', SystemMonitorView.as_view(), name='admin-system-monitor'),
    path('admin/test-service/', test_integration_service, name='admin-test-service'),
    
    # Contact endpoints
    path('contact/demo/', demo_request, name='demo-request'),
    path('contact/newsletter/', newsletter_signup, name='newsletter-signup'),
]
