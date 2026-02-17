from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmployeeViewSet, WorkScheduleViewSet
from .earnings_views import PayrollViewSet
from .notifications_views import recent_earnings_notifications, mark_notification_read

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet , basename='employee')
router.register(r'schedules', WorkScheduleViewSet , basename='work_schedule')
router.register(r'payroll', PayrollViewSet, basename='payroll')

urlpatterns = [
    path('', include(router.urls)),
    path('notifications/recent/', recent_earnings_notifications, name='recent-notifications'),
    path('notifications/<int:notification_id>/read/', mark_notification_read, name='mark-notification-read'),
]