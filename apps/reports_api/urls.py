from django.urls import path
from . import views

urlpatterns = [
    path('', views.reports_by_type, name='reports-by-type'),
    path('employees/', views.employee_report, name='employee-report'),
    path('sales/', views.sales_report, name='sales-report'),
    path('dashboard/', views.dashboard_stats, name='dashboard-stats'),
]