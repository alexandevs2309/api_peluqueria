from django.urls import path
from . import views
from rest_framework.urlpatterns import format_suffix_patterns
urlpatterns = [
    path('sales/', views.SalesReportView.as_view(), name='sales-report'),
    path('appointments/', views.AppointmentsReportView.as_view(), name='appointments-report'),
    path('employee-performance/', views.EmployeePerformanceReportView.as_view(), name='employee-performance-report'),

    path('export/', views.ReportExportView.as_view(), name='export-reports'),

]
