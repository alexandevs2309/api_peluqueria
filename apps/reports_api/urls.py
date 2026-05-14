from django.urls import path
from . import views
from . import analytics_views
from . import realtime_views

urlpatterns = [
    path('', views.reports_by_type, name='reports-by-type'),
    path('employees/', views.employee_report, name='employee-report'),
    path('sales/', views.sales_report, name='sales-report'),
    path('dashboard/', views.dashboard_stats, name='dashboard-stats'),
    
    # Nuevos endpoints para frontend avanzado
    path('calendar-data/', views.appointments_calendar_data, name='calendar-data'),
    path('kpi/', views.kpi_dashboard, name='kpi-dashboard'),
    path('services-performance/', views.services_performance, name='services-performance'),
    path('client-analytics/', views.client_analytics, name='client-analytics'),
    
    # Advanced Analytics
    path('analytics/', analytics_views.AdvancedAnalyticsView.as_view(), name='advanced-analytics'),
    path('business-intelligence/', analytics_views.BusinessIntelligenceView.as_view(), name='business-intelligence'),
    path('predictive/', analytics_views.PredictiveAnalyticsView.as_view(), name='predictive-analytics'),
    
    # Real-time Metrics
    path('realtime/', realtime_views.RealtimeMetricsView.as_view(), name='realtime-metrics'),
    path('live-dashboard/', realtime_views.LiveDashboardView.as_view(), name='live-dashboard'),
    path('alerts/', realtime_views.PerformanceAlertsView.as_view(), name='performance-alerts'),
    
    # SuperAdmin reports
    path('admin/', views.AdminReportsView.as_view(), name='admin-reports'),
]
