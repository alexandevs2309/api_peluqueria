from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmployeeViewSet, WorkScheduleViewSet
from .notifications_views import recent_earnings_notifications, mark_notification_read
from .pending_payments_endpoint import employee_pending_payments
from .phase2_views import AdvanceLoanViewSet, PayrollReportViewSet, AccountingViewSet
from .sse_views import earnings_events_stream
from .scheduled_payments_views import pay_scheduled_payroll

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'schedules', WorkScheduleViewSet, basename='work_schedule')

router.register(r'loans', AdvanceLoanViewSet, basename='loan')
router.register(r'reports', PayrollReportViewSet, basename='report')
router.register(r'accounting', AccountingViewSet, basename='accounting')

urlpatterns = [
    path('', include(router.urls)),
    path('employees/<int:employee_id>/pending-payments/', employee_pending_payments, name='employee-pending-payments'),
    path('notifications/recent/', recent_earnings_notifications, name='recent-notifications'),
    path('notifications/<int:notification_id>/read/', mark_notification_read, name='mark-notification-read'),
    path('events/earnings/', earnings_events_stream, name='earnings-events-stream'),
    path('payments/pay_scheduled_payroll/', pay_scheduled_payroll, name='pay-scheduled-payroll'),
]