from django.urls import path
from .views import ReportsView, SalesReportView

urlpatterns = [
    path('', ReportsView.as_view(), name='reports'),
    path('sales/', SalesReportView.as_view(), name='sales-report'),
]
