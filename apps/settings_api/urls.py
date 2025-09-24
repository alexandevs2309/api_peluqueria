from django.urls import path
from .views import (
    SettingRetrieveUpdateView,
    SettingExportView,
    SettingImportView,
    SettingAuditLogListView,
    BranchListCreateView,
    SettingListCreateView,
    SystemSettingsRetrieveUpdateView,
    SystemSettingsResetView
)
from .integration_views import IntegrationStatusView, IntegrationTestView
from rest_framework.routers import DefaultRouter



urlpatterns = [
    path('', SettingRetrieveUpdateView.as_view(), name='setting-detail'),
    path('export/', SettingExportView.as_view(), name='setting-export'),
    path('import/', SettingImportView.as_view(), name='setting-import'),
    path('audit-logs/', SettingAuditLogListView.as_view(), name='setting-audit'),
    path('branches/', BranchListCreateView.as_view(), name='branch-list-create'),
    path('settings/', SettingListCreateView.as_view(), name='setting-list-create'),
    path('integrations/status/', IntegrationStatusView.as_view(), name='integration-status'),
    path('integrations/test/', IntegrationTestView.as_view(), name='integration-test'),
]
