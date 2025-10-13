from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .views import EmployeeViewSet, WorkScheduleViewSet
from .earnings_views import EarningViewSet, FortnightSummaryViewSet
from .notifications_views import recent_earnings_notifications, mark_notification_read

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_fortnight(request):
    return Response({'total': 0, 'commission': 0})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_earnings(request):
    return Response({'monthly': 0, 'total': 0})

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet , basename='employee')
router.register(r'schedules', WorkScheduleViewSet , basename='work_schedule')
router.register(r'earnings', EarningViewSet, basename='earning')
router.register(r'fortnight-summaries', FortnightSummaryViewSet, basename='fortnight-summary')

urlpatterns = [
    path('', include(router.urls)),
    path('earnings/current_fortnight/', current_fortnight, name='current-fortnight'),
    path('earnings/my_earnings/', my_earnings, name='my-earnings'),
    path('notifications/recent/', recent_earnings_notifications, name='recent-notifications'),
    path('notifications/<int:notification_id>/read/', mark_notification_read, name='mark-notification-read'),
]