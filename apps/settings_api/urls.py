from django.urls import path
from .views import (
    SettingRetrieveUpdateView,
    SettingExportView,
    SettingImportView,
    SettingAuditLogListView,
    BranchListCreateView
)

urlpatterns = [
    path('', SettingRetrieveUpdateView.as_view(), name='setting-detail'),
    path('export/', SettingExportView.as_view(), name='setting-export'),
    path('import/', SettingImportView.as_view(), name='setting-import'),
    path('audit-logs/', SettingAuditLogListView.as_view(), name='setting-audit'),
    path('branches/', BranchListCreateView.as_view(), name='branch-list-create'),
]
